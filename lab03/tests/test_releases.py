from datetime import date, datetime, timezone

import pytest

from pipeline import cliente_http, releases

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)


def utc(ano, mes, dia, hora=12):
    return datetime(ano, mes, dia, hora, tzinfo=timezone.utc)


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, cabecalhos=None):
        self.status_code = status
        self._corpo = corpo
        self.headers = cabecalhos or {}

    def json(self):
        return self._corpo


class Rede:
    """Respostas da API em fila; registra as URLs pedidas."""

    def __init__(self):
        self.fila = []
        self.urls = []

    def requisitar(self, url, cabecalhos):
        self.urls.append(url)
        assert self.fila, f"chamada inesperada à rede: {url}"
        return self.fila.pop(0)


@pytest.fixture
def rede(monkeypatch, tmp_path):
    falsa = Rede()
    monkeypatch.setattr(cliente_http, "_requisitar", falsa.requisitar)
    cliente_http.configurar("token-de-teste", str(tmp_path / "cache"))
    return falsa


def release_bruta(tag, publicada, draft=False, prerelease=False):
    return {
        "tag_name": tag,
        "published_at": publicada,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
        "name": tag,
    }


def commit_bruto(i, data="2025-11-01T10:00:00Z"):
    return {"sha": f"sha{i:04d}", "commit": {"author": {"date": data}, "message": f"mudanca {i}"}}


def release(tag, publicada, draft=False, prerelease=False):
    return {
        "tag_name": tag,
        "published_at": publicada,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
    }


# coletar_releases e coletar_tags


def test_coletar_releases_grava_campos_e_converte_a_data(rede):
    rede.fila.append(
        RespostaFalsa(
            200,
            [
                release_bruta("v1.1.0", "2026-03-15T12:00:00Z"),
                release_bruta("v1.2.0-rc1", "2026-04-01T08:30:00Z", prerelease=True),
                release_bruta("v1.2.0", None, draft=True),
            ],
        )
    )

    resultado = releases.coletar_releases("o", "r")

    assert resultado[0] == {
        "tag_name": "v1.1.0",
        "published_at": utc(2026, 3, 15),
        "draft": False,
        "prerelease": False,
        "html_url": "https://github.com/o/r/releases/tag/v1.1.0",
    }
    assert resultado[1]["prerelease"] is True
    assert resultado[2]["draft"] is True and resultado[2]["published_at"] is None
    assert set(resultado[0]) == {"tag_name", "published_at", "draft", "prerelease", "html_url"}


def test_coletar_releases_junta_todas_as_paginas_sem_filtro_de_data(rede):
    rede.fila.append(
        RespostaFalsa(
            200,
            [release_bruta("v2", "2026-01-01T00:00:00Z")],
            {"Link": '<https://api.github.com/repos/o/r/releases?page=2&per_page=100>; rel="next"'},
        )
    )
    rede.fila.append(RespostaFalsa(200, [release_bruta("v1", "2019-01-01T00:00:00Z")]))

    resultado = releases.coletar_releases("o", "r")

    assert [r["tag_name"] for r in resultado] == ["v2", "v1"]
    assert all("created" not in url and "since" not in url for url in rede.urls)


def test_coletar_tags_devolve_nome_e_sha(rede):
    rede.fila.append(
        RespostaFalsa(200, [{"name": "v1.0.0", "commit": {"sha": "abc123", "url": "x"}, "zipball_url": "y"}])
    )

    assert releases.coletar_tags("o", "r") == [{"name": "v1.0.0", "sha": "abc123"}]


def test_data_da_tag_usa_a_data_do_commit_apontado(rede):
    rede.fila.append(RespostaFalsa(200, commit_bruto(1, "2026-02-03T04:05:06Z")))

    assert releases.data_da_tag("o", "r", "abc123") == utc(2026, 2, 3, 4).replace(minute=5, second=6)
    assert rede.urls == ["https://api.github.com/repos/o/r/commits/abc123"]


def test_data_da_tag_com_commit_inexistente_levanta_erro(rede):
    rede.fila.append(RespostaFalsa(404))

    with pytest.raises(LookupError):
        releases.data_da_tag("o", "r", "abc123")


# commits_entre


def test_commits_entre_devolve_sha_data_e_mensagem(rede):
    rede.fila.append(
        RespostaFalsa(200, {"commits": [commit_bruto(1, "2026-03-02T09:00:00Z"), commit_bruto(2, "2026-03-14T18:00:00Z")]})
    )

    commits = releases.commits_entre("o", "r", "v1.0.0", "v1.1.0")

    assert commits == [
        {"sha": "sha0001", "data": utc(2026, 3, 2, 9), "mensagem": "mudanca 1"},
        {"sha": "sha0002", "data": utc(2026, 3, 14, 18), "mensagem": "mudanca 2"},
    ]
    assert len(rede.urls) == 1  # a primeira página é reaproveitada do cache


def test_commits_entre_pagina_alem_de_250_commits(rede):
    def pagina(inicio, fim, proxima=None):
        cabecalhos = {}
        if proxima:
            cabecalhos["Link"] = (
                f'<https://api.github.com/repos/o/r/compare/v1...v2?page={proxima}&per_page=100>; rel="next"'
            )
        return RespostaFalsa(200, {"total_commits": 260, "commits": [commit_bruto(i) for i in range(inicio, fim)]}, cabecalhos)

    rede.fila.extend([pagina(0, 100, 2), pagina(100, 200, 3), pagina(200, 260)])

    commits = releases.commits_entre("o", "r", "v1", "v2")

    assert len(commits) == 260
    assert len({c["sha"] for c in commits}) == 260
    assert len(rede.urls) == 3
    assert all("per_page=100" in url for url in rede.urls)
    assert "page=2" in rede.urls[1] and "page=3" in rede.urls[2]


def test_commits_entre_com_404_devolve_none(rede):
    rede.fila.append(RespostaFalsa(404))

    assert releases.commits_entre("o", "r", "v1", "v2") is None
    assert len(rede.urls) == 1


def test_commits_entre_sem_commits_novos_devolve_lista_vazia(rede):
    rede.fila.append(RespostaFalsa(200, {"total_commits": 0, "commits": []}))

    assert releases.commits_entre("o", "r", "v1", "v2") == []


# releases_com_commits


@pytest.fixture
def comparacoes(monkeypatch):
    """Substitui `commits_entre`: respostas por (base, head); chave ausente = 404."""
    respostas = {}
    chamadas = []

    def falsa(owner, repo, base, head):
        chamadas.append((base, head))
        if (base, head) not in respostas:
            return None
        return [{"sha": "x", "data": data, "mensagem": "m"} for data in respostas[(base, head)]]

    monkeypatch.setattr(releases, "commits_entre", falsa)
    falsa.respostas = respostas
    falsa.chamadas = chamadas
    return falsa


def test_exemplo_do_enunciado_traz_as_datas_dos_commits(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)]
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 15))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert total_404 == 0
    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert resultado[1] == {
        "tag_name": "v1.1",
        "published_at": utc(2026, 3, 15),
        "commits": [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)],
    }


def test_primeira_release_da_historia_tem_commits_none_e_nao_e_404(comparacoes):
    todas = [release("v1.0", utc(2026, 2, 1))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert resultado == [{"tag_name": "v1.0", "published_at": utc(2026, 2, 1), "commits": None}]
    assert total_404 == 0
    assert comparacoes.chamadas == []


def test_release_anterior_fora_da_janela_e_usada_como_base(comparacoes):
    comparacoes.respostas[("v0.9", "v1.0")] = [utc(2025, 9, 20), utc(2025, 10, 2)]
    todas = [release("v0.9", utc(2025, 9, 15)), release("v1.0", utc(2025, 10, 5))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0"]  # v0.9 está fora da janela
    assert resultado[0]["commits"] == [utc(2025, 9, 20), utc(2025, 10, 2)]
    assert comparacoes.chamadas == [("v0.9", "v1.0")]


def test_compare_com_404_vira_none_e_e_contado(comparacoes):
    comparacoes.respostas[("v1.1", "v1.2")] = [utc(2026, 4, 1)]
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 1)), release("v1.2", utc(2026, 4, 2))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    por_tag = {r["tag_name"]: r["commits"] for r in resultado}
    assert por_tag["v1.0"] is None  # primeira da história
    assert por_tag["v1.1"] is None  # 404
    assert por_tag["v1.2"] == [utc(2026, 4, 1)]
    assert total_404 == 1


def test_prerelease_e_draft_nao_sao_deploys_nem_servem_de_base(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 1)]
    todas = [
        release("v1.0", utc(2026, 2, 1)),
        release("v1.1-rc1", utc(2026, 2, 20), prerelease=True),
        release("v1.1-rascunho", None, draft=True),
        release("v1.1", utc(2026, 3, 2)),
    ]

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert comparacoes.chamadas == [("v1.0", "v1.1")]


def test_ordena_por_data_de_publicacao_e_nao_pela_ordem_da_lista(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 1)]
    todas = [release("v1.1", utc(2026, 3, 2)), release("v1.0", utc(2026, 2, 1))]  # ordem da API: mais nova primeiro

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert comparacoes.chamadas == [("v1.0", "v1.1")]


def test_release_sem_commits_novos_mantem_lista_vazia(comparacoes):
    comparacoes.respostas[("v1.0", "v1.0.1")] = []
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.0.1", utc(2026, 2, 2))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert resultado[1]["commits"] == []
    assert total_404 == 0


def test_limites_da_janela_sao_fechados(comparacoes):
    comparacoes.respostas[("v1", "v2")] = []
    comparacoes.respostas[("v2", "v3")] = []
    todas = [
        release("v0", datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
        release("v1", datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)),
        release("v2", datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
        release("v3", datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)),
    ]
    comparacoes.respostas[("v0", "v1")] = []

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1", "v2"]


def test_sem_releases_devolve_vazio(comparacoes):
    assert releases.releases_com_commits("o", "r", [], INICIO, FIM) == ([], 0)
