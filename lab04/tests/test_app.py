"""Teste de fumaça do dashboard interativo (Streamlit AppTest, sem navegador nem servidor).

Confere o que a seção 4 do enunciado pede: links no topo, as 7 seções nesta ordem numa página só e
um texto do grupo junto de cada gráfico. E que os controles principais rodam sem exceção.
"""

from pathlib import Path

import pytest

testing = pytest.importorskip("streamlit.testing.v1")

from lab04 import dashboard  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TEMPO = 180   # a primeira execução gera o G2, com 10.000 conjuntos sob H₀


@pytest.fixture(scope="module")
def app():
    at = testing.AppTest.from_file(APP, default_timeout=TEMPO)
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_links_no_topo(app):
    topo = next(m.value for m in app.markdown if 'class="topo"' in m.value)
    for link in (dashboard.LINK_KANBAN, dashboard.LINK_REPOSITORIO, dashboard.LINK_DASHBOARD):
        assert link in topo
    # o topo vem antes da primeira seção
    assert _markdown(app).index('class="topo"') < _markdown(app).index(dashboard.LINK_CENARIO)


def test_as_7_secoes_na_ordem_do_enunciado_e_o_apendice_no_fim(app):
    titulos = [h.value for h in app.header]
    assert titulos[:7] == [titulo for _, titulo in dashboard.SECOES]
    assert titulos[7:] == ["Apêndice: laboratório ao vivo"]


def test_cada_grafico_tem_a_leitura_do_grupo_visivel(app):
    textos = _markdown(app)
    assert textos.count('class="leitura"') >= 5   # G1, G2, G3, G4 e dados reais
    assert "Leitura do grupo" in textos


def test_secao_2_sorteia_outro_conjunto(app):
    semente = app.number_input(key="g1_semente").value
    app.button(key="g1_sortear").click().run()
    assert not app.exception, app.exception
    assert app.number_input(key="g1_semente").value != semente


def test_secao_3_mostra_a_decisao(app):
    app.slider(key="g2_delta").set_value(1.5).run()
    assert not app.exception, app.exception
    assert any(df.value.shape == (2, 6) for df in app.dataframe)


def test_secao_4_filtra_cenarios(app):
    app.multiselect(key="g3_cenarios").set_value(["C0", "C1"]).run()
    assert not app.exception, app.exception


def test_laboratorio_roda_e_reproduz_o_csv(app):
    app.selectbox(key="lab_base").set_value("C4").run()
    rodar = next(b for b in app.button if "Rodar simulação" in b.label)
    rodar.click().run()   # com os parâmetros de C4, semente 42 e 10.000 repetições
    assert not app.exception, app.exception
    assert any("Reproduziu exatamente" in s.value for s in app.success)
