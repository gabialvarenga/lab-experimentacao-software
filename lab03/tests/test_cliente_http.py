import json
import os

import pytest
import requests

from pipeline import cliente_http
from pipeline.cliente_http import ErroHTTP

TOKEN = "ghp_token-secreto-de-teste"
AGORA = 1_000_000.0


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, cabecalhos=None):
        self.status_code = status
        self._corpo = corpo
        self.headers = cabecalhos or {}

    def json(self):
        return self._corpo


class Rede:
    """Substitui a rede, o relógio e o `sleep`, registrando tudo o que acontece."""

    def __init__(self):
        self.fila = []
        self.chamadas = []
        self.esperas = []

    def enfileirar(self, *respostas):
        self.fila.extend(respostas)

    def requisitar(self, url, cabecalhos):
        self.chamadas.append((url, cabecalhos))
        assert self.fila, f"chamada inesperada à rede: {url}"
        resposta = self.fila.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    def dormir(self, segundos):
        self.esperas.append(segundos)


@pytest.fixture
def rede(monkeypatch, tmp_path):
    falsa = Rede()
    monkeypatch.setattr(cliente_http, "_requisitar", falsa.requisitar)
    monkeypatch.setattr(cliente_http, "_dormir", falsa.dormir)
    monkeypatch.setattr(cliente_http, "_agora", lambda: AGORA)
    cliente_http.configurar(TOKEN, str(tmp_path / "cache"))
    falsa.pasta_cache = tmp_path / "cache"
    return falsa


def test_segunda_chamada_identica_usa_o_cache(rede):
    rede.enfileirar(RespostaFalsa(200, {"a": 1}))

    primeira = cliente_http.get_json("/repos/o/r")
    segunda = cliente_http.get_json("/repos/o/r")

    assert primeira == segunda == {"a": 1}
    assert len(rede.chamadas) == 1
    assert len(list(rede.pasta_cache.glob("*.json"))) == 1


def test_ordem_dos_parametros_nao_altera_a_chave(rede):
    rede.enfileirar(RespostaFalsa(200, [1]))

    cliente_http.get_json("/repos/o/r/releases", {"per_page": 100, "page": 2})
    cliente_http.get_json("/repos/o/r/releases", {"page": 2, "per_page": 100})

    assert len(rede.chamadas) == 1


def test_404_devolve_none_e_e_cacheado(rede):
    rede.enfileirar(RespostaFalsa(404, {"message": "Not Found"}))

    assert cliente_http.get_json("/repos/o/inexistente") is None
    assert cliente_http.get_json("/repos/o/inexistente") is None
    assert len(rede.chamadas) == 1


def test_502_seguido_de_200(rede):
    rede.enfileirar(RespostaFalsa(502), RespostaFalsa(200, {"ok": True}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": True}
    assert rede.esperas == [1]
    assert len(rede.chamadas) == 2


def test_5xx_persistente_usa_backoff_exponencial_e_falha(rede):
    rede.enfileirar(*[RespostaFalsa(503) for _ in range(5)])

    with pytest.raises(ErroHTTP) as erro:
        cliente_http.get_json("/repos/o/r")

    assert erro.value.status == 503
    assert rede.esperas == [1, 2, 4, 8]
    assert len(rede.chamadas) == 5
    assert list(rede.pasta_cache.glob("*.json")) == []


def test_erro_de_conexao_e_repetido_como_5xx(rede):
    rede.enfileirar(requests.ConnectionError("caiu"), RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}
    assert rede.esperas == [1]


def test_cota_esgotada_espera_o_reset_antes_da_proxima_chamada(rede):
    cabecalhos = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(AGORA) + 30)}
    rede.enfileirar(RespostaFalsa(200, {"n": 1}, cabecalhos), RespostaFalsa(200, {"n": 2}))

    cliente_http.get_json("/repos/o/a")
    assert rede.esperas == []

    cliente_http.get_json("/repos/o/b")
    assert rede.esperas == [31]  # 30 s até o reset + 1 s de margem


@pytest.mark.parametrize("status", [403, 429])
def test_limite_secundario_espera_retry_after(rede, status):
    rede.enfileirar(RespostaFalsa(status, None, {"Retry-After": "7"}), RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}
    assert rede.esperas == [7]


def test_403_com_cota_zerada_espera_o_reset_e_repete(rede):
    cabecalhos = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(AGORA) + 10)}
    rede.enfileirar(RespostaFalsa(403, None, cabecalhos), RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}
    assert rede.esperas == [11]


def test_limite_que_nunca_libera_levanta_erro(rede):
    rede.enfileirar(*[RespostaFalsa(429, None, {"Retry-After": "1"}) for _ in range(10)])

    with pytest.raises(ErroHTTP) as erro:
        cliente_http.get_json("/repos/o/r")

    assert erro.value.status == 429


@pytest.mark.parametrize("status", [401, 403, 422])
def test_outros_4xx_levantam_erro_http(rede, status):
    rede.enfileirar(RespostaFalsa(status))

    with pytest.raises(ErroHTTP) as erro:
        cliente_http.get_json("/repos/o/r")

    assert erro.value.status == status
    assert rede.esperas == []


def _paginas(rede):
    base = "https://api.github.com/repos/o/r/releases"
    rede.enfileirar(
        RespostaFalsa(200, [1, 2], {"Link": f'<{base}?per_page=100&page=2>; rel="next", <{base}?per_page=100&page=3>; rel="last"'}),
        RespostaFalsa(200, [3, 4], {"Link": f'<{base}?per_page=100&page=3>; rel="next", <{base}?per_page=100&page=1>; rel="prev"'}),
        RespostaFalsa(200, [5], {"Link": f'<{base}?per_page=100&page=2>; rel="prev", <{base}?per_page=100&page=1>; rel="first"'}),
    )


def test_paginacao_segue_o_link_ate_a_ultima_pagina(rede):
    _paginas(rede)

    assert cliente_http.get_paginado("/repos/o/r/releases") == [1, 2, 3, 4, 5]
    assert len(rede.chamadas) == 3
    assert "per_page=100" in rede.chamadas[0][0]


def test_paginacao_com_chave(rede):
    rede.enfileirar(
        RespostaFalsa(
            200,
            {"total_count": 3, "workflow_runs": [{"id": 1}, {"id": 2}]},
            {"Link": '<https://api.github.com/repos/o/r/actions/runs?page=2&per_page=100>; rel="next"'},
        ),
        RespostaFalsa(200, {"total_count": 3, "workflow_runs": [{"id": 3}]}),
    )

    runs = cliente_http.get_paginado("/repos/o/r/actions/runs", {"event": "push"}, chave="workflow_runs")

    assert [r["id"] for r in runs] == [1, 2, 3]


def test_campos_reduzem_os_itens_no_resultado_e_no_cache(rede):
    run = {"id": 1, "conclusion": "success", "repository": {"muito": "texto"}}
    rede.enfileirar(RespostaFalsa(200, {"total_count": 1, "workflow_runs": [run]}))

    runs = cliente_http.get_paginado(
        "/repos/o/r/actions/runs", chave="workflow_runs", campos=("id", "conclusion", "updated_at")
    )

    reduzido = {"id": 1, "conclusion": "success", "updated_at": None}
    assert runs == [reduzido]
    (arquivo,) = rede.pasta_cache.glob("*.json")
    assert json.loads(arquivo.read_text(encoding="utf-8"))["corpo"] == {"total_count": 1, "workflow_runs": [reduzido]}


def test_campos_valem_para_pagina_gravada_inteira_no_cache(rede):
    run = {"id": 1, "conclusion": "success", "repository": {"muito": "texto"}}
    rede.enfileirar(RespostaFalsa(200, {"total_count": 1, "workflow_runs": [run]}))
    cliente_http.get_paginado("/repos/o/r/actions/runs", chave="workflow_runs")

    runs = cliente_http.get_paginado("/repos/o/r/actions/runs", chave="workflow_runs", campos=("id",))

    assert runs == [{"id": 1}]
    assert len(rede.chamadas) == 1


def test_campos_em_pagina_que_ja_e_uma_lista(rede):
    rede.enfileirar(RespostaFalsa(200, [{"name": "v1", "zipball_url": "x"}]))

    assert cliente_http.get_paginado("/repos/o/r/tags", campos=("name",)) == [{"name": "v1"}]


def test_campos_nao_afetam_repositorio_inexistente(rede):
    rede.enfileirar(RespostaFalsa(404))

    assert cliente_http.get_paginado("/repos/o/sumiu/actions/runs", chave="workflow_runs", campos=("id",)) == []


def test_paginacao_de_repositorio_inexistente_devolve_lista_vazia(rede):
    rede.enfileirar(RespostaFalsa(404))

    assert cliente_http.get_paginado("/repos/o/inexistente/releases") == []


def test_paginacao_retoma_das_paginas_ja_cacheadas(rede):
    _paginas(rede)
    cliente_http.get_paginado("/repos/o/r/releases")
    rede.chamadas.clear()

    assert cliente_http.get_paginado("/repos/o/r/releases") == [1, 2, 3, 4, 5]
    assert rede.chamadas == []


def test_get_com_cabecalhos_devolve_o_link_tambem_no_cache(rede):
    link = '<https://api.github.com/repos/o/r/contributors?per_page=1&page=42>; rel="last"'
    rede.enfileirar(RespostaFalsa(200, [{"login": "x"}], {"Link": link}))

    _, da_rede = cliente_http.get_com_cabecalhos("/repos/o/r/contributors", {"per_page": 1})
    _, do_cache = cliente_http.get_com_cabecalhos("/repos/o/r/contributors", {"per_page": 1})

    assert da_rede["link"] == do_cache["link"] == link
    assert len(rede.chamadas) == 1


def test_token_vai_so_no_header_e_nunca_no_cache(rede):
    rede.enfileirar(RespostaFalsa(200, {"ok": 1}))

    cliente_http.get_json("/repos/o/r")

    url, cabecalhos = rede.chamadas[0]
    assert cabecalhos["Authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in url
    arquivos = list(rede.pasta_cache.iterdir())
    assert arquivos
    for arquivo in arquivos:
        assert TOKEN not in arquivo.name
        assert TOKEN not in arquivo.read_text(encoding="utf-8")


def test_cache_corrompido_e_refeito(rede):
    rede.enfileirar(RespostaFalsa(200, {"v": 1}), RespostaFalsa(200, {"v": 2}))
    cliente_http.get_json("/repos/o/r")
    (arquivo,) = rede.pasta_cache.glob("*.json")
    arquivo.write_text("{ json interrompido", encoding="utf-8")

    assert cliente_http.get_json("/repos/o/r") == {"v": 2}
    assert json.loads(arquivo.read_text(encoding="utf-8"))["corpo"] == {"v": 2}


def test_gravacao_nao_deixa_arquivos_temporarios(rede):
    rede.enfileirar(RespostaFalsa(200, {"ok": 1}))

    cliente_http.get_json("/repos/o/r")

    assert all(nome.endswith(".json") for nome in os.listdir(rede.pasta_cache))


def test_usar_antes_de_configurar_levanta_erro(monkeypatch):
    monkeypatch.setitem(cliente_http._estado, "pasta", None)

    with pytest.raises(RuntimeError):
        cliente_http.get_json("/repos/o/r")
