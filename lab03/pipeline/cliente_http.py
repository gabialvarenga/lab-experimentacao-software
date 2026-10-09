"""Camada HTTP do pipeline: cache em disco, retomada, rate limit, backoff e paginação.

É o único módulo que faz requisições à API do GitHub. Cada resposta 200 ou 404 é
salva em `<pasta_cache>/<sha256 da URL>.json`; rodar de novo o mesmo comando reaproveita
o que já foi baixado. O token vai só no cabeçalho `Authorization`, nunca na chave nem no
arquivo do cache.
"""

import hashlib
import json
import logging
import os
import re
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

BASE_URL = "https://api.github.com"
TIMEOUT = 30
ESPERAS_5XX = (1, 2, 4, 8)
MAX_ESPERAS_DE_LIMITE = 5
MARGEM_RESET = 1
CABECALHOS_GUARDADOS = (
    "link",
    "retry-after",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
)

log = logging.getLogger(__name__)

_estado = {"token": None, "pasta": None, "restantes": None, "reset": None}
_dormir = time.sleep
_agora = time.time


class ErroHTTP(Exception):
    """Resposta de erro da API. `status` é 0 quando não houve resposta (falha de conexão)."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


def configurar(token: str, pasta_cache: str) -> None:
    _estado.update(token=token, pasta=pasta_cache, restantes=None, reset=None)


def get_json(caminho: str, params: dict | None = None) -> dict | list | None:
    """Corpo JSON da resposta; `None` quando o recurso não existe (404)."""
    return get_com_cabecalhos(caminho, params)[0]


def get_com_cabecalhos(caminho: str, params: dict | None = None) -> tuple[dict | list | None, dict]:
    """Corpo JSON e cabeçalhos (em minúsculas: link, x-ratelimit-*, retry-after)."""
    return _obter(_url_canonica(caminho, params))


def get_paginado(
    caminho: str,
    params: dict | None = None,
    chave: str | None = None,
    campos: tuple[str, ...] | None = None,
) -> list:
    """Segue `Link rel="next"` até o fim e junta os itens de todas as páginas.

    Com `chave`, os itens estão em `corpo[chave]` (ex.: `workflow_runs`); sem ela, o
    corpo de cada página já é uma lista. Cada página é cacheada separadamente.

    Com `campos`, cada item fica só com essas chaves, no cache e no resultado. Serve para
    respostas volumosas: uma página de 100 workflow runs passa de 4 MB, porque cada run
    traz o repositório inteiro embutido.
    """
    params = dict(params or {})
    params.setdefault("per_page", 100)
    url = _url_canonica(caminho, params)
    reduzir = (lambda corpo: _so_campos(corpo, chave, campos)) if campos else None
    itens = []
    while url:
        corpo, cabecalhos = _obter(url, reduzir)
        if corpo is None:
            break
        itens.extend(corpo[chave] if chave else corpo)
        url = _proxima_pagina(cabecalhos.get("link"))
    return itens


def _so_campos(corpo, chave: str | None, campos: tuple[str, ...]):
    if chave is None:
        return [{campo: item.get(campo) for campo in campos} for item in corpo]
    return {**corpo, chave: [{campo: item.get(campo) for campo in campos} for item in corpo[chave]]}


def _requisitar(url: str, cabecalhos: dict):
    return requests.get(url, headers=cabecalhos, timeout=TIMEOUT)


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
        os.replace(temporario, _arquivo_cache(url))  # atômico: Ctrl+C não deixa JSON pela metade
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
    _estado["restantes"] = int(restantes) if restantes is not None else None
    _estado["reset"] = int(reset) if reset is not None else None


def _esperar_cota() -> None:
    """Se a última resposta zerou a cota, espera o reset antes de gastar outra chamada."""
    if _estado["restantes"] == 0 and _estado["reset"] is not None:
        _esperar(_segundos_ate_reset(), "cota da API esgotada")
    _estado["restantes"] = None


def _segundos_ate_reset() -> float:
    return max(0, _estado["reset"] - _agora()) + MARGEM_RESET


def _esperar(segundos: float, motivo: str) -> None:
    log.warning("%s; aguardando %.0f s", motivo, segundos)
    _dormir(segundos)


def _espera_do_limite(cabecalhos: dict) -> float | None:
    """Segundos a esperar após um 403/429 de limite; `None` se não for rate limit."""
    if "retry-after" in cabecalhos:
        return float(cabecalhos["retry-after"])
    if _estado["restantes"] == 0 and _estado["reset"] is not None:
        return _segundos_ate_reset()
    return None


def _obter(url: str, reduzir=None):
    """Corpo e cabeçalhos da URL, do cache ou da rede.

    `reduzir` enxuga o corpo antes de gravá-lo no cache. Também é aplicado na leitura,
    porque o cache pode ter páginas gravadas inteiras por uma execução anterior.
    """
    em_cache = _ler_cache(url)
    if em_cache is not None:
        corpo, cabecalhos = em_cache
        return (reduzir(corpo) if reduzir and corpo is not None else corpo), cabecalhos

    falhas_5xx = 0
    esperas_de_limite = 0
    while True:
        _esperar_cota()
        try:
            resposta = _requisitar(url, _cabecalhos_requisicao())
        except requests.RequestException:
            status = 0
        else:
            status = resposta.status_code
            cabecalhos = {nome.lower(): valor for nome, valor in resposta.headers.items()}
            _registrar_cota(cabecalhos)
            if status in (200, 404):
                guardados = {n: v for n, v in cabecalhos.items() if n in CABECALHOS_GUARDADOS}
                corpo = resposta.json() if status == 200 else None
                if reduzir and corpo is not None:
                    corpo = reduzir(corpo)
                _gravar_cache(url, status, corpo, guardados)
                return corpo, guardados
            if status in (403, 429):
                espera = _espera_do_limite(cabecalhos)
                esperas_de_limite += 1
                if espera is None or esperas_de_limite > MAX_ESPERAS_DE_LIMITE:
                    raise ErroHTTP(status)
                _esperar(espera, f"limite de requisições (HTTP {status})")
                _estado["restantes"] = None  # a espera já cobriu o reset
                continue
            if status < 500:
                raise ErroHTTP(status)

        # 5xx ou falha de conexão: backoff exponencial 1 s, 2 s, 4 s, 8 s
        if falhas_5xx >= len(ESPERAS_5XX):
            raise ErroHTTP(status)
        _esperar(ESPERAS_5XX[falhas_5xx], f"erro temporário (HTTP {status})")
        falhas_5xx += 1
