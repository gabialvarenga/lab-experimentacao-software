"""Testes do dashboard (`lab05/app.py`, S02-09) e do subcomando `app`.

As funções que não dependem da interface (carregar, tabelas, frases) são testadas direto; a página, com o
`AppTest` do Streamlit, sem navegador nem servidor. Os testes leem a coleta completa versionada em
`dados/brutos/` (é o que o dashboard mostra); o caso de CSV ausente usa um config temporário.
"""

from pathlib import Path

import pytest
import yaml

testing = pytest.importorskip("streamlit.testing.v1")

from lab05 import __main__ as principal  # noqa: E402
from lab05 import app, config, graficos  # noqa: E402

APP = str(Path(app.__file__).resolve())
TEMPO = 120


@pytest.fixture(scope="module")
def dados():
    return app.carregar()


@pytest.fixture
def config_vazio(tmp_path):
    """Config que aponta para uma pasta sem nenhum CSV."""
    cfg = {k: v for k, v in config.carregar().items() if k != "pasta"}
    cfg["saida"] = "vazio"
    caminho = tmp_path / "config.yaml"
    caminho.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return caminho


# --- carregar e avisar ---


def test_carregar_le_a_coleta_completa_e_as_tabelas(dados):
    assert len(dados["df"]) == 480 and dados["cfg"]["semente"] == 42
    assert all(dados[chave] is not None for chave in app.TABELAS)
    assert app.aviso(dados, "df", *app.TABELAS) is None


def test_carregar_sem_csv_nao_levanta_erro_e_o_aviso_diz_o_comando(config_vazio):
    vazio = app.carregar(config_vazio)
    assert vazio["df"] is None and all(vazio[chave] is None for chave in app.TABELAS)
    assert "execucoes.csv" in app.aviso(vazio, "df") and app.COMANDO_COLETA in app.aviso(vazio, "df", "q3")
    texto = app.aviso(vazio, "comparacoes", "q3")
    assert "comparacoes.csv, q3.csv" in texto and app.COMANDO_ANALISE in texto and app.COMANDO_COLETA not in texto


# --- formatação ---


@pytest.mark.parametrize("valor, esperado", [(float("nan"), "—"), (0.00001, "< 0,0001"), (0.00049, "0,0005"), (0.5, "0,5000")])
def test_formata_p_valor(valor, esperado):
    assert app._p(valor) == esperado


def test_formata_valor_por_metrica():
    assert app._valor(88315.23, "ops_s") == "88.315"
    assert app._valor(0.535, "lat_p50_ms") == "0,535 ms"
    assert app._valor(2 * 2**20, "memoria_bytes") == "2,00 MiB"
    assert app._num(float("nan")) == "—" and app._pct(0.0123) == "1,2%" and app._pct(float("nan")) == "—"


# --- tabelas ---


def test_tabela_comparacoes_tem_as_6_combinacoes_em_ordem(dados):
    t = app.tabela_comparacoes(dados["comparacoes"], "ops_s")
    assert t.shape == (6, 8)
    assert list(t["Threads de E/S"]) == [1, 1, 1, 4, 4, 4]
    assert list(t["Carga"][:3]) == [graficos.NOMES_CARGA[c] for c in graficos.CARGAS]
    assert set(t["Situação"]) == {"diferença pequena demais", "diferença relevante"}
    assert all(c.startswith("[") and c.endswith("]") for c in t["IC de 95%"])
    memoria = app.tabela_comparacoes(dados["comparacoes"], "memoria_bytes")
    assert all(v.endswith("MiB") for v in memoria["Mediana Redis"])


def test_tabela_q3_traz_r_o_ganho_de_cada_servidor_e_a_interacao_detectavel(dados):
    t = app.tabela_q3(dados["q3"], dados["q3_detectavel"])
    assert t.shape == (6, 9) and list(t["Métrica"][:3]) == ["Vazão"] * 3 and list(t["Métrica"][3:]) == ["Latência p99"] * 3
    assert set(t["Situação"]) == {"diferença relevante"}
    assert t["Interação detectável (R − 1)"].str.endswith("%").all()
    sem_detectavel = app.tabela_q3(dados["q3"])
    assert "Interação detectável (R − 1)" not in sem_detectavel.columns and len(sem_detectavel) == 6


# --- frases (leem as tabelas) ---


def test_frases_citam_os_numeros_das_tabelas(dados):
    q1 = app.frase_comparacoes(dados["comparacoes"], "ops_s")
    assert q1.startswith("Com 1 thread de E/S") and "com 4 threads de E/S" in q1 and "relevante" in q1 and "pequena demais" in q1
    memoria = app.frase_comparacoes(dados["comparacoes"], "memoria_bytes")
    assert memoria.count("×") == 2 and memoria.endswith(".")   # faixa estreita: um valor só por nível de threads
    assert app.frase_comparacoes(dados["comparacoes"], "inexistente") == ""
    q3 = app.frase_q3(dados["q3"], dados["q3_detectavel"])
    assert q3.startswith("Vazão: R de 1,63 a 1,66") and "latência p99: R de 0,60 a 0,61" in q3 and "6 linhas" in q3
    assert "40 repetições por célula" in q3 and "interação detectável" in q3
    assert "interação detectável" not in app.frase_q3(dados["q3"], None)
    assert "não há deriva" in app.frase_dados(dados["df"])


# --- a página ---


@pytest.fixture(scope="module")
def pagina():
    at = testing.AppTest.from_file(APP, default_timeout=TEMPO)
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_links_no_topo_e_as_cinco_secoes_na_ordem(pagina):
    topo = next(m.value for m in pagina.markdown if 'class="topo"' in m.value)
    assert app.LINK_KANBAN in topo and app.LINK_REPOSITORIO in topo
    assert [h.value for h in pagina.header] == [titulo for _, titulo in app.SECOES]
    assert not pagina.warning and len(pagina.dataframe) == 2


def test_cada_secao_de_resultados_tem_a_leitura_do_grupo(pagina):
    assert _markdown(pagina).count("Leitura do grupo") == 3   # dados, Q1/Q2/Q4 e Q3
    assert [m.label for m in pagina.metric][:1] == ["Execuções"] and pagina.metric[0].value == "480"


def test_trocar_a_pergunta_troca_a_tabela(pagina):
    pagina.get("segmented_control")[0].set_value("Q4: memória").run()
    assert not pagina.exception, pagina.exception
    assert all(v.endswith("MiB") for v in pagina.dataframe[0].value["Mediana Redis"])
    assert "0,871" in pagina.dataframe[0].value["Valkey ÷ Redis"].iloc[0]
    pagina.get("segmented_control")[0].set_value("Q1: vazão").run()
    assert pagina.dataframe[0].value["Mediana Redis"].iloc[0].replace(".", "").isdigit()


def test_sem_metricas_no_g1_mostra_um_aviso_e_nao_um_erro(pagina):
    pagina.multiselect(key="g1_metricas").set_value([]).run()
    assert not pagina.exception, pagina.exception
    assert any("ao menos uma métrica" in i.value for i in pagina.info)
    pagina.multiselect(key="g1_metricas").set_value(list(graficos.METRICAS)).run()
    assert not pagina.info


def test_csv_ausente_mostra_aviso_em_vez_de_erro(monkeypatch, config_vazio):
    monkeypatch.setattr(config, "CONFIG_PADRAO", config_vazio)
    at = testing.AppTest.from_file(APP, default_timeout=TEMPO)
    at.run()
    assert not at.exception, at.exception
    assert [h.value for h in at.header] == [titulo for _, titulo in app.SECOES]   # as 5 seções abrem mesmo assim
    avisos = [w.value for w in at.warning]
    assert len(avisos) == 3 and all("Faltam arquivos desta seção" in a for a in avisos)
    assert not at.dataframe and not at.metric


# --- o subcomando `app` ---


def test_app_sobe_o_streamlit_no_script_certo_e_abre_o_navegador(monkeypatch):
    chamado, timers = {}, []
    monkeypatch.setattr(principal.subprocess, "call", lambda comando, cwd: chamado.update(comando=comando, cwd=cwd) or 0)
    monkeypatch.setattr(principal.threading, "Timer", lambda s, f, args: timers.append((s, f, args)) or type("T", (), {"start": lambda self: None})())
    assert principal.main(["app", "--porta", "8600"]) == 0
    comando = chamado["comando"]
    assert comando[1:4] == ["-m", "streamlit", "run"] and comando[4].endswith("app.py")
    assert comando[comando.index("--server.port") + 1] == "8600" and "--server.headless" in comando
    assert comando[comando.index("--browser.gatherUsageStats") + 1] == "false"
    assert Path(chamado["cwd"]).name == "lab05" and (Path(chamado["cwd"]) / "lab05" / "app.py").exists()
    assert timers == [(principal.ESPERA_NAVEGADOR_S, principal.webbrowser.open, ("http://localhost:8600",))]


def test_app_sem_abrir_nao_abre_o_navegador(monkeypatch):
    monkeypatch.setattr(principal.subprocess, "call", lambda comando, cwd: 0)
    monkeypatch.setattr(principal.threading, "Timer", lambda *a, **k: pytest.fail("não devia abrir o navegador"))
    assert principal.main(["app", "--sem-abrir"]) == 0


def test_app_sem_streamlit_explica_como_instalar(monkeypatch, capsys):
    monkeypatch.setattr(principal.importlib.util, "find_spec", lambda nome: None)
    monkeypatch.setattr(principal.subprocess, "call", lambda *a, **k: pytest.fail("não devia subir o servidor"))
    assert principal.main(["app"]) == 1
    assert "pip install -r requirements.txt" in capsys.readouterr().err


def test_app_nao_le_o_config_nem_o_csv(monkeypatch):
    # o app é só uma interface: o subcomando não carrega o config (quem lê os CSVs é a página)
    monkeypatch.setattr(principal.config, "carregar", lambda *a, **k: pytest.fail("não devia ler o config"))
    monkeypatch.setattr(principal.subprocess, "call", lambda comando, cwd: 0)
    assert principal.main(["app", "--sem-abrir"]) == 0
