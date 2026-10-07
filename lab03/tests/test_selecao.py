import logging
from datetime import date, datetime, timezone

import pytest

from pipeline import selecao
from pipeline.cliente_http import ErroHTTP

FIM = date(2026, 9, 30)
BUSCA = "/search/repositories"
VAZIA = {"total_count": 0, "incomplete_results": False, "items": []}


class ApiFalsa:
    """Substitui o cliente HTTP: busca respondida por `q`, demais recursos por caminho."""

    def __init__(self):
        self.buscas = {}
        self.corpos = {}
        self.cabecalhos = {}
        self.erros = {}
        self.chamadas = []
        self.paginadas = []

    def get_json(self, caminho, params=None):
        return self.get_com_cabecalhos(caminho, params)[0]

    def get_com_cabecalhos(self, caminho, params=None):
        self.chamadas.append((caminho, dict(params or {})))
        if caminho in self.erros:
            raise self.erros[caminho]
        if caminho == BUSCA:
            return self.buscas.get(params["q"], VAZIA), {}
        return self.corpos.get(caminho), self.cabecalhos.get(caminho, {})

    def get_paginado(self, caminho, params=None, chave=None):
        self.paginadas.append((caminho, dict(params), chave))
        return self.buscas.get(params["q"], VAZIA)[chave]


@pytest.fixture
def api(monkeypatch):
    falsa = ApiFalsa()
    monkeypatch.setattr(selecao.cliente_http, "get_json", falsa.get_json)
    monkeypatch.setattr(selecao.cliente_http, "get_com_cabecalhos", falsa.get_com_cabecalhos)
    monkeypatch.setattr(selecao.cliente_http, "get_paginado", falsa.get_paginado)
    return falsa


def bruto(full_name, estrelas, linguagem="Python", criado="2020-01-01T00:00:00Z"):
    owner, name = full_name.split("/")
    return {
        "name": name,
        "full_name": full_name,
        "owner": {"login": owner},
        "stargazers_count": estrelas,
        "language": linguagem,
        "created_at": criado,
        "default_branch": "main",
    }


def resposta(itens, total=None):
    return {"total_count": len(itens) if total is None else total, "incomplete_results": False, "items": itens}


def candidato(criado=datetime(2020, 1, 1, tzinfo=timezone.utc), linguagem="Python"):
    return {
        "full_name": "o/r",
        "owner": "o",
        "name": "r",
        "stargazers_count": 1500,
        "language": linguagem,
        "created_at": criado,
        "default_branch": "main",
    }


def test_uma_busca_por_faixa_com_os_parametros_da_issue(api):
    selecao.buscar_candidatos([">10000", "5000..10000"])

    assert api.paginadas == [
        (BUSCA, {"q": "stars:>10000", "sort": "stars", "order": "desc", "per_page": 100}, "items"),
        (BUSCA, {"q": "stars:5000..10000", "sort": "stars", "order": "desc", "per_page": 100}, "items"),
    ]


def test_total_count_e_conferido_na_mesma_url_da_primeira_pagina(api):
    selecao.buscar_candidatos(["1000..2000"])

    assert api.chamadas == [(BUSCA, api.paginadas[0][1])]


def test_faixa_com_prefixo_stars_e_usada_como_veio(api):
    selecao.buscar_candidatos(["stars:1000..2000"])

    assert api.paginadas[0][1]["q"] == "stars:1000..2000"


def test_campos_do_candidato_a_partir_da_fixture(api, fixture_json):
    api.buscas["stars:1000..2000"] = fixture_json("busca_faixa")

    resultado = selecao.buscar_candidatos(["1000..2000"])

    assert [c["full_name"] for c in resultado] == ["org-a/alfa", "org-b/beta", "pessoa/gama"]
    assert resultado[0] == {
        "full_name": "org-a/alfa",
        "owner": "org-a",
        "name": "alfa",
        "stargazers_count": 1900,
        "language": "Python",
        "created_at": datetime(2015, 3, 10, 14, 30, tzinfo=timezone.utc),
        "default_branch": "main",
    }


def test_repositorio_sem_linguagem(api, fixture_json):
    api.buscas["stars:1000..2000"] = fixture_json("busca_faixa")

    resultado = selecao.buscar_candidatos(["1000..2000"])

    assert resultado[1]["full_name"] == "org-b/beta"
    assert resultado[1]["language"] is None


def test_repositorio_em_duas_faixas_aparece_uma_vez(api):
    api.buscas["stars:2000..5000"] = resposta([bruto("o/alto", 4000), bruto("o/limite", 2000)])
    api.buscas["stars:1000..2000"] = resposta([bruto("o/limite", 2000), bruto("o/baixo", 1100)])

    resultado = selecao.buscar_candidatos(["2000..5000", "1000..2000"])

    assert [c["full_name"] for c in resultado] == ["o/alto", "o/limite", "o/baixo"]


def test_resultado_em_ordem_decrescente_de_estrelas(api):
    api.buscas["stars:1000..2000"] = resposta([bruto("o/b", 1500), bruto("o/a", 1500), bruto("o/c", 1100)])
    api.buscas["stars:2000..5000"] = resposta([bruto("o/d", 3000)])

    resultado = selecao.buscar_candidatos(["1000..2000", "2000..5000"])

    assert [c["full_name"] for c in resultado] == ["o/d", "o/a", "o/b", "o/c"]


def test_faixa_com_exatamente_1000_resultados_nao_e_estreitada(api):
    api.buscas["stars:1000..2000"] = resposta([bruto("o/a", 1500)], total=1000)

    selecao.buscar_candidatos(["1000..2000"])

    assert [p[1]["q"] for p in api.paginadas] == ["stars:1000..2000"]


def test_faixa_com_1001_resultados_e_dividida_ao_meio(api):
    api.buscas["stars:1000..2000"] = resposta([bruto("o/topo", 2000)], total=1001)
    api.buscas["stars:1501..2000"] = resposta([bruto("o/alto", 1800)])
    api.buscas["stars:1000..1500"] = resposta([bruto("o/baixo", 1200)])

    resultado = selecao.buscar_candidatos(["1000..2000"])

    assert [p[1]["q"] for p in api.paginadas] == ["stars:1501..2000", "stars:1000..1500"]
    assert [c["full_name"] for c in resultado] == ["o/alto", "o/baixo"]  # só o que veio das metades


def test_metade_ainda_acima_do_teto_e_dividida_de_novo(api):
    api.buscas["stars:1000..2000"] = resposta([], total=3000)
    api.buscas["stars:1000..1500"] = resposta([], total=2000)

    selecao.buscar_candidatos(["1000..2000"])

    assert [p[1]["q"] for p in api.paginadas] == ["stars:1501..2000", "stars:1251..1500", "stars:1000..1250"]


def test_faixa_aberta_usa_as_estrelas_do_primeiro_item_como_teto(api):
    api.buscas["stars:>10000"] = resposta([bruto("o/maior", 50000)], total=1500)

    selecao.buscar_candidatos([">10000"])

    assert [p[1]["q"] for p in api.paginadas] == ["stars:30001..50000", "stars:10001..30000"]


def test_faixa_de_um_unico_valor_acima_do_teto_gera_aviso(api, caplog):
    api.buscas["stars:1000..1000"] = resposta([bruto("o/a", 1000)], total=1200)

    with caplog.at_level(logging.WARNING, logger="pipeline.selecao"):
        resultado = selecao.buscar_candidatos(["1000..1000"])

    assert any("stars:1000..1000" in mensagem for mensagem in caplog.messages)
    assert [c["full_name"] for c in resultado] == ["o/a"]  # mantém o que veio, truncado


def test_faixa_em_formato_desconhecido_acima_do_teto_e_erro(api):
    api.buscas["stars:<500"] = resposta([bruto("o/a", 400)], total=5000)

    with pytest.raises(ValueError, match="stars:<500"):
        selecao.buscar_candidatos(["<500"])


def test_sem_faixas_devolve_lista_vazia(api):
    assert selecao.buscar_candidatos([]) == []
    assert api.chamadas == []


def test_usa_actions_com_workflows(api, fixture_json):
    api.corpos["/repos/o/r/actions/workflows"] = fixture_json("workflows")

    assert selecao.usa_actions("o", "r") is True


def test_usa_actions_sem_workflows(api):
    api.corpos["/repos/o/r/actions/workflows"] = {"total_count": 0, "workflows": []}

    assert selecao.usa_actions("o", "r") is False


def test_usa_actions_com_repositorio_inexistente(api):
    assert selecao.usa_actions("o", "sumiu") is False


def test_usa_actions_faz_uma_unica_chamada_ao_endpoint_de_workflows(api):
    selecao.usa_actions("o", "r")

    assert api.chamadas == [("/repos/o/r/actions/workflows", {"per_page": 1})]


def test_contribuidores_pelo_numero_da_ultima_pagina(api):
    caminho = "/repos/o/r/contributors"
    api.corpos[caminho] = [{"login": "a", "contributions": 10}]
    api.cabecalhos[caminho] = {
        "link": '<https://api.github.com/repositories/1/contributors?per_page=1&anon=true&page=2>; rel="next", '
        '<https://api.github.com/repositories/1/contributors?per_page=1&anon=true&page=347>; rel="last"'
    }

    assert selecao.coletar_metadados(candidato(), FIM)["contribuidores"] == 347
    assert api.chamadas == [(caminho, {"per_page": 1, "anon": True})]


def test_contribuidores_com_page_antes_dos_outros_parametros(api):
    caminho = "/repos/o/r/contributors"
    api.corpos[caminho] = [{"login": "a"}]
    api.cabecalhos[caminho] = {
        "link": '<https://api.github.com/repositories/1/contributors?anon=true&page=2&per_page=1>; rel="next", '
        '<https://api.github.com/repositories/1/contributors?anon=true&page=58&per_page=1>; rel="last"'
    }

    assert selecao.coletar_metadados(candidato(), FIM)["contribuidores"] == 58


def test_contribuidores_sem_cabecalho_link(api):
    api.corpos["/repos/o/r/contributors"] = [{"login": "a", "contributions": 10}]

    assert selecao.coletar_metadados(candidato(), FIM)["contribuidores"] == 1


def test_contribuidores_com_lista_vazia(api):
    api.corpos["/repos/o/r/contributors"] = []

    assert selecao.coletar_metadados(candidato(), FIM)["contribuidores"] == 0


def test_contribuidores_recusados_pela_api_viram_none(api, caplog):
    api.erros["/repos/o/r/contributors"] = ErroHTTP(403)

    with caplog.at_level(logging.WARNING, logger="pipeline.selecao"):
        metadados = selecao.coletar_metadados(candidato(), FIM)

    assert metadados["contribuidores"] is None
    assert metadados["estrelas"] == 1500
    assert any("o/r" in mensagem for mensagem in caplog.messages)


@pytest.mark.parametrize("status", [0, 500, 503])
def test_erro_temporario_em_contribuidores_e_propagado(api, status):
    api.erros["/repos/o/r/contributors"] = ErroHTTP(status)

    with pytest.raises(ErroHTTP):
        selecao.coletar_metadados(candidato(), FIM)


def test_chaves_e_valores_dos_metadados(api):
    api.corpos["/repos/o/r/contributors"] = [{"login": "a"}]

    assert selecao.coletar_metadados(candidato(), FIM) == {
        "full_name": "o/r",
        "estrelas": 1500,
        "linguagem": "Python",
        "contribuidores": 1,
        "idade_dias": 2464,
    }


def test_metadados_de_repositorio_sem_linguagem(api):
    assert selecao.coletar_metadados(candidato(linguagem=None), FIM)["linguagem"] is None


def test_idade_em_dias_ate_o_fim_da_janela(api):
    criado = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)

    assert selecao.coletar_metadados(candidato(criado=criado), FIM)["idade_dias"] == 10


def test_idade_aceita_created_at_como_texto_da_api(api):
    assert selecao.coletar_metadados(candidato(criado="2026-09-29T00:00:00Z"), FIM)["idade_dias"] == 1


def test_metadados_a_partir_de_um_candidato_da_busca(api, fixture_json):
    api.buscas["stars:1000..2000"] = fixture_json("busca_faixa")
    api.corpos["/repos/org-b/beta/contributors"] = [{"login": "a"}]
    beta = selecao.buscar_candidatos(["1000..2000"])[1]

    assert selecao.coletar_metadados(beta, FIM) == {
        "full_name": "org-b/beta",
        "estrelas": 1500,
        "linguagem": None,
        "contribuidores": 1,
        "idade_dias": 2464,
    }
