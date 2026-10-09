"""Ponto de entrada do pipeline: `python -m pipeline --config config.yaml`.

Encadeia seleção, coleta e métricas. Os candidatos são examinados por estrelas
decrescentes e a execução para no N-ésimo aprovado no funil. As respostas da API ficam no
cache, então repetir o comando depois de uma interrupção continua de onde parou.

Saídas em `caminhos.saida`: `funil.csv` e `repositorios.csv`. Com `--repos`, os arquivos
são `funil_subamostra.csv` e `repositorios_subamostra.csv`, para não sobrescrever os da
amostra.
"""

import argparse
import csv
import logging
import os
import re
import sys
from collections import Counter

from metricas.cfr import cfr_ci
from metricas.classificacao import classificar
from metricas.conclusao import runs_validos
from metricas.frequencia import deploys_na_janela, frequencia_deploy
from metricas.janela import semanas
from metricas.lead_time import lead_time_por_commit, lead_time_por_release
from metricas.recuperacao import tempo_recuperacao
from pipeline import cliente_http, config, funil, releases, runs, selecao

COLUNAS = (
    "full_name",
    "estrelas",
    "linguagem",
    "contribuidores",
    "idade_dias",
    "n_deploys",
    "n_runs_validos",
    "frequencia_semana",
    "lead_time_a_h",
    "lead_time_b_h",
    "releases_ignoradas_404",
    "cfr_a",
    "recuperacao_mediana_h",
    "n_episodios",
    "n_censurados_direita",
    "n_censurados_esquerda",
    "categoria_c1",
    "n_metricas_classificadas",
)
SUFIXO_SUBAMOSTRA = "_subamostra"

log = logging.getLogger("pipeline")


class ErroDeEntrada(Exception):
    """Arquivo de `--repos` ilegível ou com linha fora do formato `owner/repo`."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = config.carregar(args.config)
        pares = ler_repos(args.repos) if args.repos else None
    except (config.ErroDeConfiguracao, ErroDeEntrada) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    cliente_http.configurar(cfg["token"], cfg["caminhos"]["cache"])
    try:
        executar(cfg, args.limite, pares)
    except KeyboardInterrupt:
        print("\ninterrompido; rode o mesmo comando para continuar pelo cache", file=sys.stderr)
        return 130
    except cliente_http.ErroHTTP as erro:
        print(
            f"erro: a busca de candidatos falhou ({erro}); rode o mesmo comando para continuar pelo cache",
            file=sys.stderr,
        )
        return 1
    return 0


def executar(cfg: dict, limite: int | None = None, pares: list[tuple[str, str]] | None = None) -> None:
    """Examina os candidatos até o limite de aprovados e grava os dois CSVs.

    Sem `pares`, os candidatos vêm da busca e o limite padrão é `selecao.alvo_aprovados`.
    Com `pares` (lista de `(owner, repo)`), só eles são processados, na ordem recebida, e
    não há limite se `limite` for `None`.
    """
    contagem = {"buscados": 0}
    if pares is None:
        limite = limite or cfg["selecao"]["alvo_aprovados"]
        candidatos = _candidatos_da_busca(cfg["selecao"]["faixas_estrelas"], contagem)
    else:
        contagem["buscados"] = len(pares)
        candidatos = iter(pares)

    motivos = Counter()
    linhas = []
    for item in candidatos:
        motivo, linha = _avaliar(item, cfg)
        motivos[motivo] += 1
        nome = item["full_name"] if isinstance(item, dict) else "/".join(item)
        if linha is None:
            log.info("%s: descartado (%s)", nome, motivo)
            continue
        linhas.append(linha)
        log.info("%s: aprovado (%d%s)", nome, len(linhas), f" de {limite}" if limite else "")
        if limite is not None and len(linhas) >= limite:
            break
    if limite is not None and len(linhas) < limite:
        log.warning("os candidatos acabaram com %d aprovados, abaixo do limite de %d", len(linhas), limite)

    criterios = cfg["criterios"]
    tabela = montar_funil(
        contagem["buscados"], motivos, limite, criterios["min_releases"], criterios["min_workflow_runs"]
    )
    sufixo = SUFIXO_SUBAMOSTRA if pares is not None else ""
    pasta = cfg["caminhos"]["saida"]
    caminho_funil = os.path.join(pasta, f"funil{sufixo}.csv")
    caminho_repositorios = os.path.join(pasta, f"repositorios{sufixo}.csv")
    tabela.salvar_csv(caminho_funil)
    salvar_repositorios(linhas, caminho_repositorios)
    log.info(
        "%d aprovados em %d examinados; saídas: %s e %s",
        len(linhas), sum(motivos.values()), caminho_funil, caminho_repositorios,
    )


def ler_repos(caminho: str) -> list[tuple[str, str]]:
    """Pares `(owner, repo)` do arquivo, um `owner/repo` por linha, sem repetição.

    Linhas em branco são ignoradas. Linha fora do formato levanta `ErroDeEntrada` com o
    número da linha, antes de qualquer chamada à API.
    """
    try:
        with open(caminho, encoding="utf-8-sig") as arquivo:
            textos = [linha.strip() for linha in arquivo]
    except OSError as erro:
        raise ErroDeEntrada(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    pares = {}
    for numero, texto in enumerate(textos, start=1):
        if not texto:
            continue
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", texto):
            raise ErroDeEntrada(f"{caminho}, linha {numero}: esperado owner/repo, encontrado {texto!r}")
        owner, repo = texto.split("/")
        pares.setdefault(texto.lower(), (owner, repo))
    return list(pares.values())


def montar_funil(buscados: int, motivos: Counter, limite: int | None, min_releases: int, min_runs: int) -> funil.Funil:
    """Tabela do funil a partir do motivo de descarte de cada repositório examinado.

    `motivos` conta os repositórios por motivo; os aprovados ficam na chave `None`. Cada
    repositório é contado uma única vez. Erros da API de qualquer etapa da coleta ficam
    todos na linha "Coleta sem erro".
    """
    examinados = sum(motivos.values())
    nao_examinado = f"não examinado (parada no {limite}º aprovado)" if limite else "não examinado"
    tabela = funil.Funil()
    tabela.registrar("Candidatos examinados", buscados, examinados, nao_examinado)
    restantes = examinados
    for etapa, motivo in (
        ("Com GitHub Actions", funil.SEM_ACTIONS),
        ("Coleta sem erro", funil.ERRO_DA_API),
        ("Releases na janela", funil.motivo_poucas_releases(min_releases)),
        ("Runs válidos na janela", funil.motivo_poucos_runs(min_runs)),
    ):
        saida = restantes - motivos[motivo]
        tabela.registrar(etapa, restantes, saida, motivo)
        restantes = saida
    return tabela


def salvar_repositorios(linhas: list[dict], caminho: str) -> None:
    """Grava uma linha por repositório aprovado (UTF-8, `\\n`); métrica indefinida fica vazia."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Seleciona repositórios, coleta releases e workflow runs e calcula as métricas DORA.",
    )
    analisador.add_argument("--config", required=True, help="caminho do config.yaml")
    analisador.add_argument(
        "--limite",
        type=_inteiro_positivo,
        help="encerra no N-ésimo repositório aprovado (padrão: selecao.alvo_aprovados do config)",
    )
    analisador.add_argument(
        "--repos",
        help="arquivo com um owner/repo por linha; pula a busca e processa só esses repositórios",
    )
    return analisador.parse_args(argv)


def _inteiro_positivo(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError:
        valor = 0
    if valor <= 0:
        raise argparse.ArgumentTypeError("deve ser um inteiro positivo")
    return valor


def _candidatos_da_busca(faixas: list[str], contagem: dict):
    """Candidatos por estrelas decrescentes, buscando uma faixa de cada vez.

    As faixas do config estão em ordem decrescente, então a faixa seguinte só é buscada
    quando a anterior acaba. `contagem["buscados"]` acumula os candidatos das faixas já
    buscadas; um repositório no limite de duas faixas conta uma vez.
    """
    vistos = set()
    for faixa in faixas:
        novos = [c for c in selecao.buscar_candidatos([faixa]) if c["full_name"] not in vistos]
        vistos.update(c["full_name"] for c in novos)
        contagem["buscados"] += len(novos)
        log.info("faixa de estrelas %s: %d candidatos", faixa, len(novos))
        yield from novos


def _avaliar(item, cfg: dict) -> tuple[str | None, dict | None]:
    """`(None, linha)` para repositório aprovado; `(motivo, None)` para descartado.

    `item` é um candidato da busca ou um par `(owner, repo)` de `--repos`. A coleta segue
    a ordem que gasta menos chamadas: Actions, releases, runs e só então metadados e
    commits. `ErroHTTP` em qualquer etapa descarta o repositório sem interromper a execução.
    """
    inicio, fim = cfg["janela"]["inicio"], cfg["janela"]["fim"]
    min_releases = cfg["criterios"]["min_releases"]
    min_runs = cfg["criterios"]["min_workflow_runs"]
    nome = item["full_name"] if isinstance(item, dict) else "/".join(item)
    etapa = "repositório"
    try:
        candidato = item if isinstance(item, dict) else selecao.buscar_repositorio(*item)
        if candidato is None:
            log.warning("%s: repositório não encontrado (HTTP 404)", nome)
            return funil.ERRO_DA_API, None
        owner, repo = candidato["owner"], candidato["name"]

        etapa = "workflows"
        if not selecao.usa_actions(owner, repo):
            return funil.SEM_ACTIONS, None

        etapa = "releases"
        do_repositorio = releases.coletar_releases(owner, repo)
        ok, motivo = funil.aprovado(do_repositorio, None, inicio, fim, min_releases, min_runs)
        if not ok:
            return motivo, None

        etapa = "runs"
        dos_workflows = runs.coletar_runs(owner, repo, candidato["default_branch"], inicio, fim)
        ok, motivo = funil.aprovado(do_repositorio, dos_workflows, inicio, fim, min_releases, min_runs)
        if not ok:
            return motivo, None

        etapa = "metadados"
        metadados = selecao.coletar_metadados(candidato, fim)

        etapa = "commits entre releases"
        com_commits, ignoradas_404 = releases.releases_com_commits(owner, repo, do_repositorio, inicio, fim)
    except cliente_http.ErroHTTP as erro:
        log.warning("%s: erro da API em %s (%s)", nome, etapa, erro)
        return funil.ERRO_DA_API, None
    return None, _linha(metadados, do_repositorio, dos_workflows, com_commits, ignoradas_404, inicio, fim)


def _linha(metadados, do_repositorio, dos_workflows, com_commits, ignoradas_404, inicio, fim) -> dict:
    frequencia = frequencia_deploy(do_repositorio, inicio, fim)
    lead_time_a = lead_time_por_release(com_commits)
    cfr_a = cfr_ci(dos_workflows)
    recuperacao = tempo_recuperacao(dos_workflows)
    categoria, n_classificadas = classificar(
        frequencia, lead_time_a, cfr_a, recuperacao["mediana_horas"], semanas(inicio, fim)
    )
    return {
        **metadados,
        "n_deploys": len(deploys_na_janela(do_repositorio, inicio, fim)),
        "n_runs_validos": len(runs_validos(dos_workflows)),
        "frequencia_semana": frequencia,
        "lead_time_a_h": lead_time_a,
        "lead_time_b_h": lead_time_por_commit(com_commits),
        "releases_ignoradas_404": ignoradas_404,
        "cfr_a": cfr_a,
        "recuperacao_mediana_h": recuperacao["mediana_horas"],
        "n_episodios": recuperacao["n_episodios"],
        "n_censurados_direita": recuperacao["n_censurados_direita"],
        "n_censurados_esquerda": recuperacao["n_censurados_esquerda"],
        "categoria_c1": categoria,
        "n_metricas_classificadas": n_classificadas,
    }


if __name__ == "__main__":
    sys.exit(main())
