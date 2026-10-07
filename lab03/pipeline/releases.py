"""Coleta de releases, tags e dos commits incluídos em cada release.

O lead time (RQ 02) precisa dos commits entre uma release e a anterior. A anterior pode
estar fora da janela, por isso o histórico completo de releases é coletado (sem filtro
de data) e só depois as releases da janela são consultadas via `compare`.
"""

import logging
from datetime import datetime

from metricas.janela import dentro_da_janela
from pipeline import cliente_http

log = logging.getLogger(__name__)


def coletar_releases(owner: str, repo: str) -> list[dict]:
    """Todas as releases do repositório, sem filtro de data.

    Cada item traz `tag_name`, `published_at` (`datetime` UTC, ou `None` em rascunhos),
    `draft`, `prerelease` e `html_url`.
    """
    brutas = cliente_http.get_paginado(f"/repos/{owner}/{repo}/releases")
    return [
        {
            "tag_name": bruta["tag_name"],
            "published_at": _data(bruta["published_at"]) if bruta.get("published_at") else None,
            "draft": bool(bruta["draft"]),
            "prerelease": bool(bruta["prerelease"]),
            "html_url": bruta["html_url"],
        }
        for bruta in brutas
    ]


def coletar_tags(owner: str, repo: str) -> list[dict]:
    """Tags do repositório, com `name` e o `sha` do commit apontado."""
    brutas = cliente_http.get_paginado(f"/repos/{owner}/{repo}/tags")
    return [{"name": bruta["name"], "sha": bruta["commit"]["sha"]} for bruta in brutas]


def data_da_tag(owner: str, repo: str, sha: str) -> datetime:
    """Data (`commit.author.date`) do commit apontado pela tag.

    Tags não têm data própria; esta chamada só deve ser feita para repositórios aprovados.
    """
    commit = cliente_http.get_json(f"/repos/{owner}/{repo}/commits/{sha}")
    if commit is None:
        raise LookupError(f"commit {sha} não encontrado em {owner}/{repo}")
    return _data(commit["commit"]["author"]["date"])


def commits_entre(owner: str, repo: str, base: str, head: str) -> list[dict] | None:
    """Commits de `base...head`, paginados, com `sha`, `data` e `mensagem`.

    Devolve `None` quando a comparação não existe (404), caso comum de tag apagada ou
    reescrita. Sem paginação a API devolveria no máximo 250 commits.
    """
    caminho = f"/repos/{owner}/{repo}/compare/{base}...{head}"
    # Primeira página à parte: get_paginado devolve [] tanto para 404 quanto para
    # comparação vazia, e aqui os dois casos precisam ser distinguidos. A página fica no
    # cache e é reaproveitada logo abaixo.
    if cliente_http.get_json(caminho, {"per_page": 100}) is None:
        return None
    brutos = cliente_http.get_paginado(caminho, chave="commits")
    return [
        {
            "sha": bruto["sha"],
            "data": _data(bruto["commit"]["author"]["date"]),
            "mensagem": bruto["commit"]["message"],
        }
        for bruto in brutos
    ]


def releases_com_commits(
    owner: str, repo: str, releases: list[dict], inicio, fim
) -> tuple[list[dict], int]:
    """Deploys da janela com os commits incluídos em cada um.

    Deploy é release com `draft = false` e `prerelease = false`. A release anterior de R é
    o deploy imediatamente anterior por `published_at`, dentro ou fora da janela.

    Cada item devolvido traz `tag_name`, `published_at` e `commits`, a lista das datas
    dos commits incluídos. `commits` é `None` na primeira release da história (sem
    anterior) e quando o `compare` dá 404; só o segundo caso entra no total devolvido.
    """
    deploys = sorted(
        (r for r in releases if not r["draft"] and not r["prerelease"] and r["published_at"] is not None),
        key=lambda r: r["published_at"],
    )
    resultado = []
    total_404 = 0
    for posicao, release in enumerate(deploys):
        if not dentro_da_janela(release["published_at"], inicio, fim):
            continue
        commits = None
        if posicao > 0:
            anterior = deploys[posicao - 1]
            do_intervalo = commits_entre(owner, repo, anterior["tag_name"], release["tag_name"])
            if do_intervalo is None:
                total_404 += 1
                log.warning(
                    "%s/%s: compare %s...%s deu 404; release ignorada no lead time",
                    owner, repo, anterior["tag_name"], release["tag_name"],
                )
            else:
                commits = [commit["data"] for commit in do_intervalo]
        resultado.append(
            {"tag_name": release["tag_name"], "published_at": release["published_at"], "commits": commits}
        )
    return resultado, total_404


def _data(texto: str) -> datetime:
    return datetime.fromisoformat(texto)
