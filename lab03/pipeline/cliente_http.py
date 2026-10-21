"""Camada HTTP do pipeline: cache em disco, retomada, rate limit, backoff e paginação.

É o único módulo que faz requisições à API do GitHub. Cada resposta 200 ou 404 é
salva em `<pasta_cache>/<sha256 da URL>.json`; rodar de novo o mesmo comando reaproveita
o que já foi baixado. O token vai só no cabeçalho `Authorization`, nunca na chave nem no
arquivo do cache. Consultas GraphQL (POST) usam o mesmo cache, com a consulta e as
variáveis somadas à URL na chave.

O módulo pode ser usado por várias threads: `configurar` define quantas requisições podem
estar em andamento ao mesmo tempo e `mapear` distribui o trabalho respeitando esse teto.
"""

import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

BASE_URL = "https://api.github.com"
GRAPHQL_URL = f"{BASE_URL}/graphql"
TIMEOUT = 30
ESPERAS_5XX = (1, 2, 4, 8)
# Sem conexão (rede ou DNS fora do ar): a espera cresce até 60 s e se repete até a rede
# voltar ou até o total chegar ao máximo.
ESPERAS_SEM_CONEXAO = (1, 2, 4, 8, 15, 30, 60)
ESPERA_MAXIMA_SEM_CONEXAO = 6 * 60 * 60
MAX_ESPERAS_DE_LIMITE = 5
TENTATIVAS_DE_GRAVACAO = 8  # espera 0,05 s, 0,1 s, 0,2 s... entre uma e outra
MARGEM_RESET = 1
CABECALHOS_GUARDADOS = (
    "link",
    "retry-after",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
)

log = logging.getLogger(__name__)

_estado = {"token": None, "pasta": None, "restantes": None, "reset": None, "simultaneas": 1}
_trava_da_cota = threading.Lock()
_vagas = threading.BoundedSemaphore(1)
_interrompido = threading.Event()
_agora = time.time


def _dormir(segundos: float) -> None:
    _interrompido.wait(segundos)  # acorda antes se a execução for interrompida


class ErroHTTP(Exception):
    """Resposta de erro da API. `status` é 0 quando não houve resposta (falha de conexão)."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


class ErroGraphQL(ErroHTTP):
    """Resposta 200 do GraphQL com o campo `errors` (ex.: repositório inexistente)."""

    def __init__(self, erros: list):
        super().__init__(200)
        self.args = ("GraphQL: " + "; ".join(str(e.get("message", e)) for e in erros),)
        self.erros = erros


class SemConexao(Exception):
    """A rede não voltou dentro de `ESPERA_MAXIMA_SEM_CONEXAO`.

    Não é `ErroHTTP`: a falha não diz nada sobre o recurso pedido, então quem chama não
    deve tratá-la como erro da API para aquele repositório.
    """


class Interrompido(Exception):
    """A execução foi interrompida por `interromper`; nenhuma nova requisição é feita."""


def configurar(token: str, pasta_cache: str, simultaneas: int = 1) -> None:
    """Define o token, a pasta do cache e o teto de requisições em andamento ao mesmo tempo."""
    global _vagas
    if simultaneas < 1:
        raise ValueError("simultaneas deve ser ao menos 1")
    _estado.update(token=token, pasta=pasta_cache, restantes=None, reset=None, simultaneas=simultaneas)
    _vagas = threading.BoundedSemaphore(simultaneas)
    _interrompido.clear()


def interromper() -> None:
    """Faz as threads em andamento pararem na próxima requisição ou espera."""
    _interrompido.set()


def mapear(funcao, itens) -> list:
    """`[funcao(item) for item in itens]`, na mesma ordem, em até `simultaneas` threads.

    Com `simultaneas = 1` roda em sequência, na própria thread. A primeira exceção de
    `funcao` é propagada.
    """
    itens = list(itens)
    threads = min(_estado["simultaneas"], len(itens))
    if threads <= 1:
        return [funcao(item) for item in itens]
    with ThreadPoolExecutor(max_workers=threads) as executor:
        return list(executor.map(funcao, itens))


def get_json(
    caminho: str,
    params: dict | None = None,
    chave: str | None = None,
    campos: tuple[str, ...] | None = None,
) -> dict | list | None:
    """Corpo JSON da resposta; `None` quando o recurso não existe (404).

    `chave` e `campos` enxugam o corpo como em `get_paginado`.
    """
    return get_com_cabecalhos(caminho, params, chave, campos)[0]


def get_com_cabecalhos(
    caminho: str,
    params: dict | None = None,
    chave: str | None = None,
    campos: tuple[str, ...] | None = None,
) -> tuple[dict | list | None, dict]:
    """Corpo JSON e cabeçalhos (em minúsculas: link, x-ratelimit-*, retry-after)."""
    return _obter(_url_canonica(caminho, params), _redutor(chave, campos))


def post_graphql(consulta: str, variaveis: dict | None = None) -> dict:
    """Campo `data` da resposta à consulta GraphQL, do cache ou da rede.

    Resposta com `errors` levanta `ErroGraphQL` e não vai para o cache. A cota do GraphQL
    é separada da REST, mas os cabeçalhos `x-ratelimit-*` têm o mesmo formato e são
    tratados da mesma forma.
    """
    url = _url_canonica(GRAPHQL_URL, None)
    corpo, _ = _obter(url, envio={"query": consulta, "variables": variaveis or {}})
    return corpo["data"]


def get_paginado(
    caminho: str,
    params: dict | None = None,
    chave: str | None = None,
    campos: tuple[str, ...] | None = None,
) -> list:
    """Segue `Link rel="next"` até o fim e junta os itens de todas as páginas.

    Com `chave`, os itens estão em `corpo[chave]` (ex.: `workflow_runs`); sem ela, o
    corpo de cada página já é uma lista. Cada página é cacheada separadamente.

    Com `campos`, cada item fica só com essas chaves, no cache e no resultado; do
    restante do corpo sobram apenas os valores simples (ex.: `total_count`). Serve para
    respostas volumosas: uma página de 100 workflow runs passa de 4 MB, porque cada run
    traz o repositório inteiro embutido.
    """
    params = dict(params or {})
    params.setdefault("per_page", 100)
    url = _url_canonica(caminho, params)
    reduzir = _redutor(chave, campos)
    itens = []
    while url:
        corpo, cabecalhos = _obter(url, reduzir)
        if corpo is None:
            break
        itens.extend(corpo[chave] if chave else corpo)
        url = _proxima_pagina(cabecalhos.get("link"))
    return itens


def _redutor(chave: str | None, campos: tuple[str, ...] | None):
    return (lambda corpo: _so_campos(corpo, chave, campos)) if campos else None


def _so_campos(corpo, chave: str | None, campos: tuple[str, ...]):
    if chave is None and isinstance(corpo, dict):  # objeto único, ex.: um commit
        return {campo: corpo.get(campo) for campo in campos}
    if chave is None:
        return [{campo: item.get(campo) for campo in campos} for item in corpo]
    simples = {nome: valor for nome, valor in corpo.items() if not isinstance(valor, (dict, list))}
    return {**simples, chave: [{campo: item.get(campo) for campo in campos} for item in corpo[chave]]}


def _requisitar(url: str, cabecalhos: dict):
    return requests.get(url, headers=cabecalhos, timeout=TIMEOUT)


def _postar(url: str, cabecalhos: dict, envio: dict):
    return requests.post(url, headers=cabecalhos, json=envio, timeout=TIMEOUT)


def _chave_do_cache(url: str, envio: dict | None) -> str:
    if envio is None:
        return url
    return url + "#" + json.dumps(envio, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _url_canonica(caminho: str, params: dict | None) -> str:
    if _estado["pasta"] is None:
        raise RuntimeError("chame configurar(token, pasta_cache) antes de usar o cliente HTTP")
    url = caminho if caminho.startswith("http") else f"{BASE_URL}/{caminho.lstrip('/')}"
    partes = urlsplit(url)
    consulta = parse_qsl(partes.query, keep_blank_values=True)
    for nome, valor in (params or {}).items():
        texto = str(valor).lower() if isinstance(valor, bool) else str(valor)
        consulta.append((nome, texto))
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(sorted(consulta)), ""))


def _proxima_pagina(link: str | None) -> str | None:
    if not link:
        return None
    achado = re.search(r'<([^>]+)>\s*;\s*rel="next"', link)
    return _url_canonica(achado.group(1), None) if achado else None


def _arquivo_cache(url: str) -> str:
    return os.path.join(_estado["pasta"], hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")


def _ler_cache(url: str):
    try:
        with open(_arquivo_cache(url), encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados["corpo"], dados["cabecalhos"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _gravar_cache(url: str, status: int, corpo, cabecalhos: dict) -> None:
    os.makedirs(_estado["pasta"], exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=_estado["pasta"], suffix=".tmp")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump({"url": url, "status": status, "cabecalhos": cabecalhos, "corpo": corpo}, arquivo)
        destino = _arquivo_cache(url)
        for tentativa in range(TENTATIVAS_DE_GRAVACAO):
            try:
                os.replace(temporario, destino)  # atômico: Ctrl+C não deixa JSON pela metade
                break
            except PermissionError:
                # No Windows, o destino pode estar aberto por outro processo (outra coleta, antivírus).
                if tentativa == TENTATIVAS_DE_GRAVACAO - 1:
                    raise
                time.sleep(0.05 * 2**tentativa)
    except BaseException:
        if os.path.exists(temporario):
            os.remove(temporario)
        raise


def _cabecalhos_requisicao() -> dict:
    cabecalhos = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if _estado["token"]:
        cabecalhos["Authorization"] = f"Bearer {_estado['token']}"
    return cabecalhos


def _registrar_cota(cabecalhos: dict) -> None:
    restantes, reset = cabecalhos.get("x-ratelimit-remaining"), cabecalhos.get("x-ratelimit-reset")
    with _trava_da_cota:
        _estado["restantes"] = int(restantes) if restantes is not None else None
        _estado["reset"] = int(reset) if reset is not None else None


def _esperar_cota() -> None:
    """Se a última resposta zerou a cota, espera o reset antes de gastar outra chamada."""
    with _trava_da_cota:
        esgotada = _estado["restantes"] == 0 and _estado["reset"] is not None
        espera = _segundos_ate(_estado["reset"]) if esgotada else None
        _estado["restantes"] = None
    if espera is not None:
        _esperar(espera, "cota da API esgotada")


def _segundos_ate(reset: int) -> float:
    return max(0, reset - _agora()) + MARGEM_RESET


def _esperar(segundos: float, motivo: str) -> None:
    log.warning("%s; aguardando %.0f s", motivo, segundos)
    _dormir(segundos)


def _espera_do_limite(cabecalhos: dict) -> float | None:
    """Segundos a esperar após um 403/429 de limite; `None` se não for rate limit.

    Usa os cabeçalhos da própria resposta: com várias threads, a cota guardada em
    `_estado` pode já ter sido atualizada por outra requisição.
    """
    if "retry-after" in cabecalhos:
        return float(cabecalhos["retry-after"])
    if cabecalhos.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in cabecalhos:
        return _segundos_ate(int(cabecalhos["x-ratelimit-reset"]))
    return None


def _obter(url: str, reduzir=None, envio: dict | None = None):
    """Corpo e cabeçalhos da URL, do cache ou da rede.

    `reduzir` enxuga o corpo antes de gravá-lo no cache. Também é aplicado na leitura,
    porque o cache pode ter páginas gravadas inteiras por uma execução anterior.
    Com `envio`, a requisição é um POST GraphQL com esse corpo JSON.
    """
    chave_cache = _chave_do_cache(url, envio)
    em_cache = _ler_cache(chave_cache)
    if em_cache is not None:
        corpo, cabecalhos = em_cache
        return (reduzir(corpo) if reduzir and corpo is not None else corpo), cabecalhos

    falhas_5xx = 0
    esperas_de_limite = 0
    tentativas_sem_conexao = 0
    segundos_sem_conexao = 0
    while True:
        _esperar_cota()
        if _interrompido.is_set():
            raise Interrompido()
        try:
            with _vagas:
                if envio is None:
                    resposta = _requisitar(url, _cabecalhos_requisicao())
                else:
                    resposta = _postar(url, _cabecalhos_requisicao(), envio)
        except requests.ConnectionError:
            # Sem rede: espera a conexão voltar em vez de desistir do recurso. Sem isso, uma
            # queda de minutos faria cada repositório da fila ser descartado como erro da API.
            espera = ESPERAS_SEM_CONEXAO[min(tentativas_sem_conexao, len(ESPERAS_SEM_CONEXAO) - 1)]
            if segundos_sem_conexao + espera > ESPERA_MAXIMA_SEM_CONEXAO:
                raise SemConexao(f"sem conexão com a API há {segundos_sem_conexao} s") from None
            _esperar(espera, "sem conexão com a API")
            tentativas_sem_conexao += 1
            segundos_sem_conexao += espera
            continue
        except requests.RequestException:
            status = 0
        else:
            status = resposta.status_code
            cabecalhos = {nome.lower(): valor for nome, valor in resposta.headers.items()}
            _registrar_cota(cabecalhos)
            if status in (200, 404):
                guardados = {n: v for n, v in cabecalhos.items() if n in CABECALHOS_GUARDADOS}
                corpo = resposta.json() if status == 200 else None
                if envio is not None and (corpo is None or corpo.get("errors")):
                    raise ErroGraphQL((corpo or {}).get("errors") or [{"message": f"HTTP {status}"}])
                if reduzir and corpo is not None:
                    corpo = reduzir(corpo)
                _gravar_cache(chave_cache, status, corpo, guardados)
                return corpo, guardados
            if status in (403, 429):
                espera = _espera_do_limite(cabecalhos)
                esperas_de_limite += 1
                if espera is None or esperas_de_limite > MAX_ESPERAS_DE_LIMITE:
                    raise ErroHTTP(status)
                _esperar(espera, f"limite de requisições (HTTP {status})")
                with _trava_da_cota:
                    _estado["restantes"] = None  # a espera já cobriu o reset
                continue
            if status < 500:
                raise ErroHTTP(status)

        # 5xx ou resposta interrompida (ex.: tempo esgotado): backoff exponencial 1 s, 2 s, 4 s, 8 s
        if falhas_5xx >= len(ESPERAS_5XX):
            raise ErroHTTP(status)
        _esperar(ESPERAS_5XX[falhas_5xx], f"erro temporário (HTTP {status})")
        falhas_5xx += 1
