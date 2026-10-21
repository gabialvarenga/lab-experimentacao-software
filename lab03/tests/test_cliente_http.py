import json
import os
import threading
import time

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


def test_erro_de_conexao_e_repetido(rede):
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


# uso concorrente


def test_mapear_preserva_a_ordem_em_sequencia_e_em_paralelo(rede, tmp_path):
    assert cliente_http.mapear(lambda n: n * 2, [3, 1, 2]) == [6, 2, 4]

    cliente_http.configurar(TOKEN, str(tmp_path / "cache"), simultaneas=4)

    assert cliente_http.mapear(lambda n: n * 2, range(20)) == [n * 2 for n in range(20)]
    assert cliente_http.mapear(lambda n: n, []) == []


def test_mapear_com_simultaneas_1_roda_na_propria_thread(rede):
    assert cliente_http.mapear(lambda _: threading.current_thread(), [1, 2]) == [threading.current_thread()] * 2


def test_mapear_propaga_a_excecao_da_funcao(rede, tmp_path):
    cliente_http.configurar(TOKEN, str(tmp_path / "cache"), simultaneas=3)

    with pytest.raises(ZeroDivisionError):
        cliente_http.mapear(lambda n: 1 // n, [1, 0, 2])


def test_requisicoes_em_andamento_respeitam_o_teto(monkeypatch, tmp_path):
    em_andamento = []
    pico = []
    trava = threading.Lock()

    def requisitar(url, cabecalhos):
        with trava:
            em_andamento.append(url)
            pico.append(len(em_andamento))
        time.sleep(0.02)
        with trava:
            em_andamento.remove(url)
        return RespostaFalsa(200, {"url": url})

    monkeypatch.setattr(cliente_http, "_requisitar", requisitar)
    cliente_http.configurar(TOKEN, str(tmp_path / "cache"), simultaneas=3)

    # 12 threads disputando 3 vagas
    threads = [threading.Thread(target=cliente_http.get_json, args=(f"/repos/o/r{n}",)) for n in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max(pico) == 3
    assert len(os.listdir(tmp_path / "cache")) == 12


def test_configurar_rejeita_teto_menor_que_1(tmp_path):
    with pytest.raises(ValueError):
        cliente_http.configurar(TOKEN, str(tmp_path / "cache"), simultaneas=0)


def test_interromper_impede_novas_requisicoes_mas_nao_o_cache(rede):
    rede.enfileirar(RespostaFalsa(200, {"a": 1}))
    cliente_http.get_json("/repos/o/em-cache")

    cliente_http.interromper()

    assert cliente_http.get_json("/repos/o/em-cache") == {"a": 1}
    with pytest.raises(cliente_http.Interrompido):
        cliente_http.get_json("/repos/o/novo")
    assert len(rede.chamadas) == 1


def test_configurar_desfaz_a_interrupcao(rede, tmp_path):
    cliente_http.interromper()
    cliente_http.configurar(TOKEN, str(tmp_path / "cache"))
    rede.enfileirar(RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}


def test_espera_do_limite_usa_os_cabecalhos_da_propria_resposta(rede):
    # com várias threads, outra resposta pode ter registrado cota disponível nesse meio-tempo
    cliente_http._registrar_cota({"x-ratelimit-remaining": "40", "x-ratelimit-reset": str(int(AGORA) + 99)})

    da_resposta = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(AGORA) + 10)}

    assert cliente_http._espera_do_limite(da_resposta) == 11
    assert cliente_http._espera_do_limite({"x-ratelimit-remaining": "40"}) is None


def test_get_json_com_campos_enxuga_o_cache_e_descarta_o_resto_do_corpo(rede):
    corpo = {
        "total_commits": 1,
        "files": [{"filename": "a.py", "patch": "muito texto"}],
        "base_commit": {"sha": "x"},
        "commits": [{"sha": "abc", "commit": {"message": "m"}, "author": {"login": "pessoa"}}],
    }
    rede.enfileirar(RespostaFalsa(200, corpo))

    resultado = cliente_http.get_json("/repos/o/r/compare/a...b", chave="commits", campos=("sha", "commit"))

    enxuto = {"total_commits": 1, "commits": [{"sha": "abc", "commit": {"message": "m"}}]}
    assert resultado == enxuto
    (arquivo,) = rede.pasta_cache.glob("*.json")
    assert json.loads(arquivo.read_text(encoding="utf-8"))["corpo"] == enxuto


# queda de rede


def test_sem_conexao_espera_a_rede_voltar_em_vez_de_desistir(rede):
    quedas = [requests.ConnectionError("sem rede") for _ in range(10)]
    rede.enfileirar(*quedas, RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}
    assert rede.esperas == [1, 2, 4, 8, 15, 30, 60, 60, 60, 60]


def test_sem_conexao_alem_do_maximo_levanta_sem_conexao(rede, monkeypatch):
    monkeypatch.setattr(cliente_http, "ESPERA_MAXIMA_SEM_CONEXAO", 20)
    rede.enfileirar(*[requests.ConnectionError("sem rede") for _ in range(10)])

    with pytest.raises(cliente_http.SemConexao):
        cliente_http.get_json("/repos/o/r")

    assert rede.esperas == [1, 2, 4, 8]  # 15 s a mais passaria de 20 s


def test_sem_conexao_nao_e_erro_http():
    assert not issubclass(cliente_http.SemConexao, ErroHTTP)


def test_queda_de_rede_nao_consome_as_tentativas_de_erro_temporario(rede):
    rede.enfileirar(
        RespostaFalsa(502),
        *[requests.ConnectionError("sem rede") for _ in range(6)],
        RespostaFalsa(502),
        RespostaFalsa(200, {"ok": 1}),
    )

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}
    assert rede.esperas == [1, 1, 2, 4, 8, 15, 30, 2]


def test_tempo_esgotado_continua_sendo_erro_temporario(rede):
    rede.enfileirar(*[requests.Timeout("demorou") for _ in range(5)])

    with pytest.raises(ErroHTTP) as erro:
        cliente_http.get_json("/repos/o/r")

    assert erro.value.status == 0
    assert rede.esperas == [1, 2, 4, 8]


def test_get_json_com_campos_enxuga_um_objeto_unico(rede):
    rede.enfileirar(RespostaFalsa(200, {"author": {"date": "2026-01-01T00:00:00Z"}, "tree": {"sha": "t"}}))

    assert cliente_http.get_json("/repos/o/r/git/commits/abc", campos=("author",)) == {
        "author": {"date": "2026-01-01T00:00:00Z"}
    }
    (arquivo,) = rede.pasta_cache.glob("*.json")
    assert set(json.loads(arquivo.read_text(encoding="utf-8"))["corpo"]) == {"author"}


# post_graphql


@pytest.fixture
def postagens(rede, monkeypatch):
    """Faz os POST passarem pela mesma rede falsa, registrando o corpo enviado."""
    envios = []

    def postar(url, cabecalhos, envio):
        envios.append(envio)
        return rede.requisitar(url, cabecalhos)

    monkeypatch.setattr(cliente_http, "_postar", postar)
    return envios


def test_post_graphql_devolve_data_e_usa_o_cache(rede, postagens):
    rede.enfileirar(RespostaFalsa(200, {"data": {"x": 1}}))

    primeira = cliente_http.post_graphql("query { x }", {"a": 1})
    segunda = cliente_http.post_graphql("query { x }", {"a": 1})

    assert primeira == segunda == {"x": 1}
    assert len(rede.chamadas) == 1
    assert rede.chamadas[0][0] == "https://api.github.com/graphql"
    assert postagens == [{"query": "query { x }", "variables": {"a": 1}}]


def test_post_graphql_com_variaveis_diferentes_nao_reaproveita_o_cache(rede, postagens):
    rede.enfileirar(RespostaFalsa(200, {"data": {"x": 1}}), RespostaFalsa(200, {"data": {"x": 2}}))

    assert cliente_http.post_graphql("query { x }", {"cursor": None}) == {"x": 1}
    assert cliente_http.post_graphql("query { x }", {"cursor": "c1"}) == {"x": 2}
    assert len(list(rede.pasta_cache.glob("*.json"))) == 2


def test_post_graphql_com_errors_levanta_erro_e_nao_grava_cache(rede, postagens):
    rede.enfileirar(RespostaFalsa(200, {"data": None, "errors": [{"message": "Could not resolve"}]}))

    with pytest.raises(ErroHTTP) as erro:
        cliente_http.post_graphql("query { x }")

    assert isinstance(erro.value, cliente_http.ErroGraphQL)
    assert "Could not resolve" in str(erro.value)
    assert list(rede.pasta_cache.glob("*.json")) == []


def test_post_graphql_repete_erro_temporario_e_nao_grava_o_token(rede, postagens):
    rede.enfileirar(RespostaFalsa(502), RespostaFalsa(200, {"data": {"x": 1}}))

    assert cliente_http.post_graphql("query { x }") == {"x": 1}
    assert rede.esperas == [1]
    assert rede.chamadas[0][1]["Authorization"] == f"Bearer {TOKEN}"
    (arquivo,) = rede.pasta_cache.glob("*.json")
    assert TOKEN not in arquivo.read_text(encoding="utf-8")


def test_post_graphql_antes_de_configurar_levanta_erro(monkeypatch):
    monkeypatch.setitem(cliente_http._estado, "pasta", None)

    with pytest.raises(RuntimeError):
        cliente_http.post_graphql("query { x }")


def test_gravacao_do_cache_tenta_de_novo_quando_o_arquivo_esta_em_uso(rede, monkeypatch):
    original = os.replace
    falhas = []

    def replace_instavel(origem, destino):
        if len(falhas) < 2:
            falhas.append(destino)
            raise PermissionError(13, "Acesso negado")
        return original(origem, destino)

    monkeypatch.setattr(cliente_http.os, "replace", replace_instavel)
    monkeypatch.setattr(cliente_http.time, "sleep", lambda segundos: None)
    rede.enfileirar(RespostaFalsa(200, {"ok": 1}))

    assert cliente_http.get_json("/repos/o/r") == {"ok": 1}

    assert len(falhas) == 2
    assert len(list(rede.pasta_cache.glob("*.json"))) == 1
    assert list(rede.pasta_cache.glob("*.tmp")) == []


def test_gravacao_do_cache_desiste_depois_de_varias_tentativas_e_limpa_o_temporario(rede, monkeypatch):
    tentativas = []

    def sempre_negado(origem, destino):
        tentativas.append(destino)
        raise PermissionError(13, "Acesso negado")

    monkeypatch.setattr(cliente_http.os, "replace", sempre_negado)
    monkeypatch.setattr(cliente_http.time, "sleep", lambda segundos: None)
    rede.enfileirar(RespostaFalsa(200, {"ok": 1}))

    with pytest.raises(PermissionError):
        cliente_http.get_json("/repos/o/r")

    assert len(tentativas) == cliente_http.TENTATIVAS_DE_GRAVACAO
    assert list(rede.pasta_cache.glob("*.tmp")) == []
