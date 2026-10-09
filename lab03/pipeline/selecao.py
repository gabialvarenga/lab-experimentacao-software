"""Seleção dos candidatos: busca fatiada por estrelas, uso de Actions e metadados.

A busca do GitHub devolve no máximo 1.000 resultados por consulta. Por isso ela é feita
por faixa de estrelas; uma faixa que passa do teto é dividida ao meio até caber, e uma
faixa de um único valor que ainda passa gera um aviso (a busca daquela faixa fica truncada).
"""

import logging
import re
from datetime import date, datetime, timezone

from pipeline import cliente_http

LIMITE_DA_API = 1000
BUSCA = "/search/repositories"

log = logging.getLogger(__name__)


def buscar_candidatos(faixas: list[str]) -> list[dict]:
    """Repositórios das faixas de estrelas, sem repetição, por estrelas decrescentes.

    Cada faixa pode vir como `1000..2000` ou `stars:1000..2000`. Cada item traz
    `full_name`, `owner`, `name`, `stargazers_count`, `language` (texto ou `None`),
    `created_at` (`datetime` em UTC) e `default_branch`.
    """
    candidatos = {}
    for faixa in faixas:
        for bruto in _buscar_faixa(_qualificador(faixa)):
            candidato = _normalizar(bruto)
            candidatos.setdefault(candidato["full_name"], candidato)
    return sorted(candidatos.values(), key=lambda c: (-c["stargazers_count"], c["full_name"]))


def buscar_repositorio(owner: str, repo: str) -> dict | None:
    """Um repositório pelo nome, no formato de `buscar_candidatos`; `None` se não existe (404)."""
    bruto = cliente_http.get_json(f"/repos/{owner}/{repo}")
    return _normalizar(bruto) if bruto is not None else None


def usa_actions(owner: str, repo: str) -> bool:
    """True se o repositório tem ao menos um workflow do GitHub Actions."""
    corpo = cliente_http.get_json(f"/repos/{owner}/{repo}/actions/workflows", {"per_page": 1})
    return corpo is not None and corpo["total_count"] > 0


def coletar_metadados(candidato: dict, fim_janela: date) -> dict:
    """Estrelas, linguagem, contribuidores e idade de um candidato de `buscar_candidatos`.

    Deve ser chamada só para candidatos em que `usa_actions` devolveu True: quem não usa
    Actions é descartado antes de qualquer outra coleta. `contribuidores` é `None` quando
    a API se recusa a contar.
    """
    criado = candidato["created_at"]
    if isinstance(criado, str):
        criado = _data(criado)
    return {
        "full_name": candidato["full_name"],
        "estrelas": candidato["stargazers_count"],
        "linguagem": candidato["language"],
        "contribuidores": _contar_contribuidores(candidato["owner"], candidato["name"]),
        "idade_dias": (fim_janela - criado.astimezone(timezone.utc).date()).days,
    }


def _qualificador(faixa: str) -> str:
    faixa = faixa.strip()
    return faixa if faixa.startswith("stars:") else f"stars:{faixa}"


def _buscar_faixa(qualificador: str) -> list[dict]:
    params = {"q": qualificador, "sort": "stars", "order": "desc", "per_page": 100}
    # Mesma URL da primeira página de `get_paginado`: a conferência do total não custa
    # outra requisição, porque a segunda leitura vem do cache.
    primeira = cliente_http.get_json(BUSCA, params)
    if primeira is None:
        return []
    total = primeira["total_count"]
    if total <= LIMITE_DA_API:
        return cliente_http.get_paginado(BUSCA, params, chave="items")

    limites = _limites(qualificador, primeira["items"])
    if limites is None:
        raise ValueError(f"faixa {qualificador!r} tem {total} resultados e não pode ser estreitada")
    minimo, maximo = limites
    if minimo >= maximo:
        log.warning("%s tem %d resultados; busca da faixa truncada em %d", qualificador, total, LIMITE_DA_API)
        return cliente_http.get_paginado(BUSCA, params, chave="items")
    meio = (minimo + maximo) // 2
    return _buscar_faixa(f"stars:{meio + 1}..{maximo}") + _buscar_faixa(f"stars:{minimo}..{meio}")


def _limites(qualificador: str, itens: list[dict]) -> tuple[int, int] | None:
    """Menor e maior número de estrelas da faixa; `None` se o formato não é reconhecido.

    Em faixa aberta (`>10000`), o teto são as estrelas do primeiro item, já que a busca
    vem em ordem decrescente.
    """
    faixa = qualificador.removeprefix("stars:")
    fechada = re.fullmatch(r"(\d+)\.\.(\d+)", faixa)
    if fechada:
        return int(fechada.group(1)), int(fechada.group(2))
    aberta = re.fullmatch(r">(=?)(\d+)", faixa)
    if aberta and itens:
        minimo = int(aberta.group(2)) + (0 if aberta.group(1) else 1)
        return minimo, itens[0]["stargazers_count"]
    return None


def _normalizar(bruto: dict) -> dict:
    return {
        "full_name": bruto["full_name"],
        "owner": bruto["owner"]["login"],
        "name": bruto["name"],
        "stargazers_count": bruto["stargazers_count"],
        "language": bruto.get("language") or None,
        "created_at": _data(bruto["created_at"]),
        "default_branch": bruto["default_branch"],
    }


def _contar_contribuidores(owner: str, repo: str) -> int | None:
    """Com uma pessoa por página, o número da última página é o total de contribuidores."""
    try:
        corpo, cabecalhos = cliente_http.get_com_cabecalhos(
            f"/repos/{owner}/{repo}/contributors", {"per_page": 1, "anon": True}
        )
    except cliente_http.ErroHTTP as erro:
        if erro.status == 0 or erro.status >= 500:
            raise
        log.warning("%s/%s: contribuidores indisponíveis (HTTP %d)", owner, repo, erro.status)
        return None
    ultima = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>\s*;\s*rel="last"', cabecalhos.get("link") or "")
    if ultima:
        return int(ultima.group(1))
    return len(corpo or [])  # sem `Link`: uma única página, com 0 ou 1 pessoa


def _data(texto: str) -> datetime:
    return datetime.fromisoformat(texto)
