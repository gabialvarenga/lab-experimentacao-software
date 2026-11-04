"""Coleta dos PRs reais pela API do GitHub (Issue S01-04).

É o único módulo do Lab04 que acessa a API. Segue o protocolo de `docs/protocolo-coleta.md`:
PRs mesclados de `supabase/supabase` na janela do `config.yaml`, de autor humano, divididos em
`com_bot` (primeira revisão do Copilot até 1 h após a abertura) e `sem_bot` (nenhuma revisão
do Copilot), ambos com mais de 1 h até o merge. De cada grupo saem 10 PRs por mês de merge,
sorteados com a semente do config.

As respostas da API ficam em cache (uma por arquivo), então repetir a coleta não refaz
requisições. Para uma coleta nova, apague a pasta de cache.

Saídas: `prs.csv` (uma linha por PR da amostra) e `registro-coleta.md` (consultas, contagens
por etapa e trocas).
"""

import calendar
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API = "https://api.github.com"
COLUNAS = [
    "numero_pr",
    "grupo",
    "autor",
    "criado_em",
    "mesclado_em",
    "horas_ate_merge",
    "horas_ate_revisao_bot",
]
POR_PAGINA = 100
TETO_DA_BUSCA = 1000
ESPERA_PADRAO = 60.0
TENTATIVAS = 6


class ErroColeta(Exception):
    """A coleta não pode continuar sem comprometer a amostra; a mensagem diz o motivo."""


class Cliente:
    """Requisições à API com cache em disco, pausa entre buscas e espera do limite de uso."""

    def __init__(self, token, pasta_cache, pausa_busca=20.0, sessao=None, dormir=time.sleep, relogio=time.monotonic):
        self._cabecalhos = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._pasta = Path(pasta_cache)
        self._pausa_busca = pausa_busca
        self._sessao = sessao or requests.Session()
        self._dormir = dormir
        self._relogio = relogio
        self._ultima_busca = None
        self.requisicoes = 0
        self.do_cache = 0

    def buscar(self, consulta: str, pagina: int = 1) -> dict:
        params = {"q": consulta, "per_page": POR_PAGINA, "page": pagina, "sort": "created", "order": "asc"}
        return self._obter("/search/issues", params, busca=True)

    def revisoes(self, repositorio: str, numero: int) -> list:
        """Todas as revisões de um PR, em ordem de envio."""
        itens, pagina = [], 1
        while True:
            bloco = self._obter(f"/repos/{repositorio}/pulls/{numero}/reviews", {"per_page": POR_PAGINA, "page": pagina})
            itens += bloco
            if len(bloco) < POR_PAGINA:
                return itens
            pagina += 1

    def _arquivo(self, caminho, params):
        chave = hashlib.sha1(json.dumps([caminho, sorted(params.items())]).encode("utf-8")).hexdigest()
        return self._pasta / f"{chave}.json"

    def _obter(self, caminho, params, busca=False):
        arquivo = self._arquivo(caminho, params)
        if arquivo.exists():
            self.do_cache += 1
            return json.loads(arquivo.read_text(encoding="utf-8"))
        for tentativa in range(TENTATIVAS):
            if busca:
                self._respeitar_pausa()
            resposta = self._sessao.get(API + caminho, params=params, headers=self._cabecalhos, timeout=30)
            self.requisicoes += 1
            if busca:
                self._ultima_busca = self._relogio()
            if resposta.status_code == 200:
                corpo = resposta.json()
                self._pasta.mkdir(parents=True, exist_ok=True)
                arquivo.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
                return corpo
            if resposta.status_code in (403, 429):
                self._dormir(self._espera(resposta.headers) + 5)
            elif resposta.status_code >= 500:
                self._dormir(2**tentativa)
            else:
                raise ErroColeta(f"GET {caminho} devolveu HTTP {resposta.status_code}")
        raise ErroColeta(f"GET {caminho} falhou depois de {TENTATIVAS} tentativas")

    def _respeitar_pausa(self):
        if self._ultima_busca is None:
            return
        falta = self._pausa_busca - (self._relogio() - self._ultima_busca)
        if falta > 0:
            self._dormir(falta)

    @staticmethod
    def _espera(cabecalhos) -> float:
        if "Retry-After" in cabecalhos:
            return float(cabecalhos["Retry-After"])
        if cabecalhos.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in cabecalhos:
            return max(float(cabecalhos["x-ratelimit-reset"]) - time.time(), 0.0)
        return ESPERA_PADRAO


def _data(valor) -> date:
    return valor if isinstance(valor, date) else date.fromisoformat(str(valor))


def _instante(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _horas(inicio: str, fim: str) -> float:
    return (_instante(fim) - _instante(inicio)).total_seconds() / 3600


def meses_da_janela(inicio, fim) -> list:
    """Lista de (primeiro dia, último dia) de cada mês entre `inicio` e `fim`, recortada nas pontas."""
    inicio, fim = _data(inicio), _data(fim)
    meses, ano, mes = [], inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        primeiro = max(date(ano, mes, 1), inicio)
        ultimo = min(date(ano, mes, calendar.monthrange(ano, mes)[1]), fim)
        meses.append((primeiro, ultimo))
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return meses


def consulta(repositorio: str, revisor: str, inicio: date, fim: date, com_revisor: bool) -> str:
    """Consulta de busca de PRs mesclados no intervalo, com ou sem comentário do revisor."""
    base = (
        f"repo:{repositorio} is:pr is:merged merged:{inicio.isoformat()}..{fim.isoformat()} "
        "-author:app/dependabot -author:app/renovate"
    )
    return f"{base} commenter:app/{revisor}" if com_revisor else f"{base} -commenter:app/{revisor}"


def buscar_todos(cliente: Cliente, consulta_: str) -> tuple:
    """Todos os resultados de uma consulta (todas as páginas) e o total informado pela API."""
    itens, pagina = [], 1
    while True:
        bloco = cliente.buscar(consulta_, pagina)
        total = bloco["total_count"]
        itens += bloco["items"]
        if total > TETO_DA_BUSCA:
            raise ErroColeta(f"a consulta tem {total} resultados, acima do teto de {TETO_DA_BUSCA}: {consulta_}")
        if len(itens) >= total or not bloco["items"]:
            break
        pagina += 1
    if len(itens) < total:
        raise ErroColeta(f"a consulta devolveu {len(itens)} de {total} resultados: {consulta_}")
    return itens, total


def candidato(item: dict):
    """`(dados, None)` do PR da busca, ou `(None, motivo)` com `autor_bot` ou `sem_merge`."""
    if item["user"]["type"] == "Bot":
        return None, "autor_bot"
    mesclado = (item.get("pull_request") or {}).get("merged_at")
    if not mesclado:
        return None, "sem_merge"
    return {
        "numero_pr": item["number"],
        "autor": item["user"]["login"],
        "criado_em": item["created_at"],
        "mesclado_em": mesclado,
        "horas_ate_merge": _horas(item["created_at"], mesclado),
    }, None


def primeira_revisao(revisoes: list, login: str):
    """Instante (texto ISO) do primeiro envio de revisão do `login`, ou `None`."""
    envios = [r["submitted_at"] for r in revisoes if r.get("submitted_at") and (r.get("user") or {}).get("login", "").lower() == login.lower()]
    return min(envios, key=_instante) if envios else None


def sortear(pools: dict, por_mes: int, rng, aceitar):
    """Sorteia `por_mes` itens por mês (ordem do `rng`) e completa as faltas com as sobras.

    `aceitar(item)` devolve a linha final ou `None` (item descartado). Devolve as linhas, as
    trocas por descarte e as linhas vindas de outro mês, para o registro.
    """
    linhas, sobras, descartados, reservas = [], [], 0, []
    falta = {}
    for mes in sorted(pools):
        pool = sorted(pools[mes], key=lambda c: c["numero_pr"])
        pegos = 0
        for i in rng.permutation(len(pool)):
            if pegos == por_mes:
                sobras.append((mes, pool[i]))
                continue
            linha = aceitar(pool[i])
            if linha is None:
                descartados += 1
            else:
                linhas.append(linha)
                pegos += 1
        if pegos < por_mes:
            falta[mes] = por_mes - pegos
    total_falta = sum(falta.values())
    if total_falta:
        for i in rng.permutation(len(sobras)):
            if len(reservas) == total_falta:
                break
            mes, item = sobras[i]
            linha = aceitar(item)
            if linha is None:
                descartados += 1
            else:
                linhas.append(linha)
                reservas.append({"mes": mes, "numero_pr": linha["numero_pr"]})
    return linhas, descartados, reservas, falta


def coletar(cfg: dict, cliente: Cliente, agora=None) -> pd.DataFrame:
    """Executa o protocolo e devolve a amostra; o registro da coleta fica em `df.attrs["registro"]`."""
    c = cfg["coleta"]
    repositorio, revisor = c["repositorio"], c["revisor"]
    login, limite, minimo = f"{revisor}[bot]", c["limite_revisao_horas"], c["min_horas_ate_merge"]
    rng = np.random.default_rng(cfg["semente"])
    meses = meses_da_janela(c["janela"]["inicio"], c["janela"]["fim"])

    registro = {"coletado_em": (agora or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC"),
                "repositorio": repositorio, "meses": {}, "consultas": []}
    pool_com, pool_sem = {}, {}

    for inicio, fim in meses:
        mes = inicio.strftime("%Y-%m")
        info = registro["meses"][mes] = {}
        for grupo, com_revisor in (("com_bot", True), ("sem_bot", False)):
            texto = consulta(repositorio, revisor, inicio, fim, com_revisor)
            registro["consultas"].append(texto)
            itens, total = buscar_todos(cliente, texto)
            etapas = {"busca": total, "autor_bot": 0, "sem_merge": 0, "fora_da_janela": 0, "ate_o_minimo": 0, "elegiveis": 0}
            elegiveis = []
            for item in itens:
                dados, motivo = candidato(item)
                if motivo:
                    etapas[motivo] += 1
                elif not inicio <= _instante(dados["mesclado_em"]).date() <= fim:
                    etapas["fora_da_janela"] += 1
                elif dados["horas_ate_merge"] <= minimo:
                    etapas["ate_o_minimo"] += 1
                else:
                    elegiveis.append(dados)
            etapas["elegiveis"] = len(elegiveis)
            if com_revisor:
                classificados = []
                etapas.update({"revisao_rapida": 0, "revisao_tardia": 0, "sem_revisao_na_lista": 0})
                for dados in elegiveis:
                    envio = primeira_revisao(cliente.revisoes(repositorio, dados["numero_pr"]), login)
                    if envio is None:
                        etapas["sem_revisao_na_lista"] += 1
                        continue
                    horas_revisao = _horas(dados["criado_em"], envio)
                    if 0 <= horas_revisao <= limite:
                        etapas["revisao_rapida"] += 1
                        classificados.append({**dados, "horas_ate_revisao_bot": horas_revisao})
                    else:
                        etapas["revisao_tardia"] += 1
                pool_com[mes] = classificados
            else:
                pool_sem[mes] = elegiveis
            info[grupo] = etapas

    def linha(grupo, dados, horas_revisao):
        return {
            "numero_pr": dados["numero_pr"], "grupo": grupo, "autor": dados["autor"],
            "criado_em": dados["criado_em"], "mesclado_em": dados["mesclado_em"],
            "horas_ate_merge": round(dados["horas_ate_merge"], 4),
            "horas_ate_revisao_bot": None if horas_revisao is None else round(horas_revisao, 4),
        }

    def aceitar_com(dados):
        return linha("com_bot", dados, dados["horas_ate_revisao_bot"])

    def aceitar_sem(dados):
        if primeira_revisao(cliente.revisoes(repositorio, dados["numero_pr"]), login) is not None:
            return None
        return linha("sem_bot", dados, None)

    linhas_com, trocados_com, reservas_com, falta_com = sortear(pool_com, c["por_mes"], rng, aceitar_com)
    linhas_sem, trocados_sem, reservas_sem, falta_sem = sortear(pool_sem, c["por_mes"], rng, aceitar_sem)
    registro["sorteio"] = {
        "por_mes": c["por_mes"],
        "com_bot": {"reservas": reservas_com, "faltas": falta_com, "descartados": trocados_com},
        "sem_bot": {"reservas": reservas_sem, "faltas": falta_sem, "descartados": trocados_sem},
    }
    registro["requisicoes"] = cliente.requisicoes
    registro["do_cache"] = cliente.do_cache

    df = pd.DataFrame(linhas_com + linhas_sem, columns=COLUNAS)
    df = df.sort_values(["grupo", "numero_pr"], ascending=[True, True]).reset_index(drop=True)
    df.attrs["registro"] = registro
    return df


def salvar(df: pd.DataFrame, caminho) -> None:
    """Grava o CSV da amostra (UTF-8, vírgula, sem índice)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8", lineterminator="\n")


def escrever_registro(df: pd.DataFrame, caminho) -> None:
    """Escreve o `registro-coleta.md` a partir de `df.attrs["registro"]`."""
    r = df.attrs["registro"]
    linhas = [
        "# Lab04 — Registro da coleta",
        "",
        f"Coleta de {r['coletado_em']} em `{r['repositorio']}`, gerada por `python -m lab04 coletar`. "
        f"Requisições à API: {r['requisicoes']}; respostas vindas do cache: {r['do_cache']}.",
        "",
        "## Consultas",
        "",
        *[f"- `{texto}`" for texto in r["consultas"]],
        "",
        "## Contagens por etapa",
        "",
        "| Mês de merge | Grupo | Busca | Autor bot | Fora da janela | Até 1 h | Elegíveis | Revisão rápida | Revisão tardia | Sem revisão na lista |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mes, grupos in r["meses"].items():
        for grupo, e in grupos.items():
            com = grupo == "com_bot"
            linhas.append(
                f"| {mes} | {grupo} | {e['busca']} | {e['autor_bot']} | {e['fora_da_janela']} | {e['ate_o_minimo']} | {e['elegiveis']} | "
                f"{e['revisao_rapida'] if com else '—'} | {e['revisao_tardia'] if com else '—'} | "
                f"{e['sem_revisao_na_lista'] if com else '—'} |"
            )
    linhas += ["", "## Amostra", "", "| Mês de merge | com_bot | sem_bot |", "|---|---|---|"]
    meses = pd.to_datetime(df["mesclado_em"]).dt.strftime("%Y-%m")
    for mes in r["meses"]:
        n = lambda g: int(((df["grupo"] == g) & (meses == mes)).sum())
        linhas.append(f"| {mes} | {n('com_bot')} | {n('sem_bot')} |")
    linhas.append(f"| **Total** | **{int((df['grupo'] == 'com_bot').sum())}** | **{int((df['grupo'] == 'sem_bot').sum())}** |")
    linhas += ["", f"Meta: {r['sorteio']['por_mes']} PRs por mês e por grupo.", "", "## Trocas e reservas", ""]
    for grupo in ("com_bot", "sem_bot"):
        s = r["sorteio"][grupo]
        linhas.append(
            f"- `{grupo}`: {s['descartados']} PRs descartados na verificação das revisões; "
            f"{len(s['reservas'])} completados com PRs de outros meses"
            + (f" ({', '.join('#' + str(x['numero_pr']) + ' de ' + x['mes'] for x in s['reservas'])})" if s["reservas"] else "")
            + (f"; faltas por mês antes da reserva: {s['faltas']}" if s["faltas"] else "")
            + "."
        )
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")


def executar(cfg: dict, token: str) -> pd.DataFrame:
    """Coleta, grava `prs.csv` e `registro-coleta.md` nos caminhos do config e resume no terminal."""
    c = cfg["coleta"]
    base = Path(cfg["pasta"])
    cliente = Cliente(token, base / c["cache"], pausa_busca=c["pausa_busca_s"])
    df = coletar(cfg, cliente)
    salvar(df, base / c["saida"])
    escrever_registro(df, base / c["registro"])
    contagem = df["grupo"].value_counts().to_dict()
    print(f"{len(df)} PRs gravados em {base / c['saida']}: {contagem}")
    return df
