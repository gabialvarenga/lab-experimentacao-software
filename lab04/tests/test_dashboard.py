import re

import pandas as pd
import pytest

from lab04 import config, dashboard, graficos


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    saida = tmp_path_factory.mktemp("dashboard") / "sub" / "index.html"
    dashboard.montar(saida)
    return saida.read_text(encoding="utf-8")


def test_montar_grava_html_completo_em_utf8(pagina):
    assert pagina.startswith("<!DOCTYPE html>") and pagina.rstrip().endswith("</html>")
    assert '<meta charset="utf-8">' in pagina


def test_sete_secoes_na_ordem_fixa(pagina):
    posicoes = [pagina.index(f'<section id="{ancora}">') for ancora, _ in dashboard.SECOES]
    assert posicoes == sorted(posicoes) and len(posicoes) == 7
    for _, titulo in dashboard.SECOES:
        assert f"<h2>{titulo}</h2>" in pagina


def test_links_no_topo_antes_das_secoes(pagina):
    inicio = pagina.index("<section")
    for link in (dashboard.LINK_KANBAN, dashboard.LINK_REPOSITORIO, dashboard.LINK_DASHBOARD):
        assert pagina.index(f'href="{link}"') < inicio


def test_secoes_1_a_3_tem_texto_e_graficos(pagina):
    secoes = re.split(r'<section id="', pagina)[1:]
    cenario, dados, testes = secoes[:3]
    assert "Pergunta." in cenario and "H₀" in cenario and "H₁" in cenario
    assert graficos.TEXTO_G1 in dados and dados.count('class="plotly-graph-div"') == 1
    assert graficos.TEXTO_G2 in testes and testes.count('class="plotly-graph-div"') == 2
    for secao in secoes[3:]:
        assert "Em construção" in secao and "plotly-graph-div" not in secao


def test_origem_e_quantidade_dos_dados_vem_do_config_e_do_csv(pagina):
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    contagem = reais["grupo"].value_counts()
    assert cfg["coleta"]["repositorio"] in pagina
    assert "01/08/2026" in pagina and "31/10/2026" in pagina
    assert f"({contagem['com_bot']} PRs)" in pagina and f"({contagem['sem_bot']} PRs)" in pagina


def test_plotly_embutido_uma_vez_e_sem_recurso_externo(pagina):
    assert 'src="http' not in pagina
    assert pagina.count("plotly.js v") == 1  # cabeçalho da biblioteca embutida


def test_grafico_ausente_ou_com_erro_vira_marcador(monkeypatch, tmp_path):
    monkeypatch.delattr(graficos, "g1")

    def quebra(_):
        raise RuntimeError("sem dados")

    monkeypatch.setattr(graficos, "g2", quebra)
    saida = tmp_path / "index.html"
    dashboard.montar(saida, config.carregar())
    pagina = saida.read_text(encoding="utf-8")
    assert "g1 ainda não foi implementado" in pagina
    assert pagina.count("g2 falhou (RuntimeError: sem dados)") == 2
    assert "plotly-graph-div" not in pagina
    assert all(f'<section id="{ancora}">' in pagina for ancora, _ in dashboard.SECOES)


def test_texto_ausente_nao_quebra_a_pagina(monkeypatch, tmp_path):
    monkeypatch.delattr(graficos, "TEXTO_G2")
    saida = tmp_path / "index.html"
    dashboard.montar(saida)
    assert "<h2>3. Como os testes funcionam</h2>" in saida.read_text(encoding="utf-8")
