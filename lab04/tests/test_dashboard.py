import re

import numpy as np
import pandas as pd
import pytest

from lab04 import config, dashboard, graficos, testes


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
    assert "Em construção" in secoes[6] and "plotly-graph-div" not in secoes[6]   # seção 7
    assert "Em construção" not in secoes[5] and "<table>" in secoes[5]   # seção 6: a tabela dos dados reais


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
    assert pagina.count('class="plotly-graph-div"') == 2   # só o G3 e o G4: as seções 2 e 3 ficam com marcadores
    assert all(f'<section id="{ancora}">' in pagina for ancora, _ in dashboard.SECOES)


def test_texto_ausente_nao_quebra_a_pagina(monkeypatch, tmp_path):
    monkeypatch.delattr(graficos, "TEXTO_G2")
    saida = tmp_path / "index.html"
    dashboard.montar(saida)
    assert "<h2>3. Como os testes funcionam</h2>" in saida.read_text(encoding="utf-8")


# --- seções 4 e 5: erro tipo I (G3) e poder (G4) (S02-11) ---


def secao(pagina, ancora):
    return pagina.split(f'<section id="{ancora}">')[1].split("</section>")[0]


def test_so_a_secao_7_continua_em_construcao():
    assert set(dashboard.EM_CONSTRUCAO) == {"conclusao"}


@pytest.mark.parametrize("ancora, nome", [("erro-tipo-1", "G3"), ("poder", "G4")])
def test_secoes_4_e_5_tem_o_grafico_a_legenda_e_o_texto(pagina, ancora, nome):
    trecho = secao(pagina, ancora)
    assert trecho.count('class="plotly-graph-div"') == 1 and f"{nome}: " in trecho
    assert "n = 30 por grupo (10 em C4)" in trecho
    assert f'<p class="texto">{getattr(graficos, f"TEXTO_{nome}")}</p>' in trecho
    assert "Em construção" not in trecho


def test_pagina_tem_os_cinco_graficos_com_o_plotly_embutido_uma_vez(pagina):
    assert pagina.count('class="plotly-graph-div"') == 5   # G1, os dois G2, G3 e G4
    assert pagina.count("plotly.js v") == 1


def test_texto_da_secao_4_bate_com_o_classificacao_csv():
    """O texto do G3 contra o CSV versionado da S02-07 (o teste do G3 confere a classificação recalculada)."""
    cfg = config.carregar()
    c = pd.read_csv(f"{cfg['pasta']}/dados/simulacao/classificacao.csv")
    texto = graficos.TEXTO_G3
    por_teste = {t: grupo.set_index(["alfa", "cenario"])["classificacao"] for t, grupo in c.groupby("teste")}
    assert "liberal" not in set(c["classificacao"]) and "Nenhum teste foi liberal" in texto
    mw, welch = por_teste["mann_whitney"][0.05], por_teste["welch"][0.05]
    assert set(mw[mw == "conservador"].index) == {"C0", "C4"} and "em C0 e em C4" in texto
    assert set(welch[welch == "ok"].index) == {"C0"} and "ficou conservador" in texto
    for teste in por_teste.values():   # "Com α = 1% a classificação é a mesma"
        assert (teste[0.05] == teste[0.01]).all()


@pytest.mark.parametrize("nome", ["g3", "g4"])
def test_g3_ou_g4_ausente_vira_marcador_so_na_sua_secao(monkeypatch, tmp_path, nome):
    monkeypatch.delattr(graficos, nome)
    saida = tmp_path / "index.html"
    dashboard.montar(saida, config.carregar())
    pagina = saida.read_text(encoding="utf-8")
    ausente, presente = ("erro-tipo-1", "poder") if nome == "g3" else ("poder", "erro-tipo-1")
    assert f"{nome} ainda não foi implementado" in secao(pagina, ausente)
    assert "plotly-graph-div" not in secao(pagina, ausente)
    assert secao(pagina, presente).count('class="plotly-graph-div"') == 1


def test_resultados_ausentes_viram_marcador_nas_secoes_4_e_5_e_o_resto_da_pagina_sai(tmp_path):
    cfg = config.carregar()
    cfg["simulacao"] = {**cfg["simulacao"], "saida": "dados/simulacao/nao-existe.csv"}
    saida = tmp_path / "index.html"
    dashboard.montar(saida, cfg)
    pagina = saida.read_text(encoding="utf-8")
    for ancora in ("erro-tipo-1", "poder"):
        trecho = secao(pagina, ancora)
        assert "não foi possível ler dados/simulacao/nao-existe.csv (FileNotFoundError" in trecho
        assert "plotly-graph-div" not in trecho
    assert graficos.TEXTO_G3 in secao(pagina, "erro-tipo-1")
    assert pagina.count('class="plotly-graph-div"') == 3   # G1 e os dois G2
    assert all(f'<section id="{ancora}">' in pagina for ancora, _ in dashboard.SECOES)


def test_tamanhos_lista_o_n_mais_comum_e_as_excecoes():
    df = pd.DataFrame({"cenario": ["C0", "C0", "C1", "C4"], "n": [30, 30, 30, 10]})
    assert dashboard._tamanhos(df) == "n = 30 por grupo (10 em C4)"
    assert dashboard._tamanhos(df[df["n"] == 30]) == "n = 30 por grupo"
    assert dashboard._tamanhos(pd.DataFrame({"cenario": ["C0"]})) == ""


# --- seção 6: os dois testes nos dados reais (S02-10) ---


def prs(a, b):
    """CSV da coleta fictício: `a` é o grupo com_bot e `b` o sem_bot."""
    return pd.DataFrame({"grupo": ["com_bot"] * len(a) + ["sem_bot"] * len(b), "horas_ate_merge": [*a, *b]})


def paragrafos(a, b):
    reais = prs(a, b)
    return dashboard.texto_dados_reais(testes.tabela_dados_reais(reais), reais)


def secao_6(pagina):
    return re.split(r'<section id="', pagina)[6]


def test_a_secao_6_nao_esta_mais_em_construcao():
    assert "dados-reais" not in dashboard.EM_CONSTRUCAO


def test_secao_6_traz_a_tabela_com_os_numeros_dos_testes_nos_dados_reais(pagina):
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    t = testes.tabela_dados_reais(reais).set_index("teste")
    secao = secao_6(pagina)
    for cabecalho in ("Teste", "Estatística", "p-valor", "Tamanho de efeito", "Razão de medianas", "Conclusão (α = 0,05)"):
        assert cabecalho in secao
    w, m = t.loc["welch"], t.loc["mann_whitney"]
    esperado = [
        f"t = {graficos._num(w['estatistica'])} (gl = {graficos._num(w['graus_de_liberdade'], 2)})",
        graficos._p_rotulo(w["p_valor"]), f"g de Hedges = {graficos._num(w['tamanho_efeito'], 2)} ({w['magnitude']})",
        f"U = {m['estatistica']:.0f}", graficos._p_rotulo(m["p_valor"]),
        f"δ de Cliff = {graficos._num(m['tamanho_efeito'], 2)} ({m['magnitude']})", graficos._num(w["razao_medianas"], 2),
    ]
    for texto in esperado:
        assert texto in secao
    assert secao.count("não rejeita H₀") >= 2 and "plotly-graph-div" not in secao


def test_secao_6_tem_conclusao_efeito_cautela_e_limitacoes_em_uma_frase(pagina):
    secao = secao_6(pagina)
    assert "os dois chegam à mesma conclusão" in secao and "Tamanho de efeito:" in secao
    assert "importância prática" in secao and "Não rejeitar H₀ não prova que não há efeito" in secao
    assert dashboard.LIMITACOES in secao
    assert len([f for f in re.split(r"(?<=[.!?])\s+", dashboard.LIMITACOES.strip()) if f]) == 1
    assert "viés de seleção" in dashboard.LIMITACOES and "tamanho do PR" in dashboard.LIMITACOES


def test_texto_dos_dados_reais_diz_que_os_dois_concordam_e_que_nao_ha_importancia_pratica():
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    decisao, efeito, cautela, _ = dashboard.texto_dados_reais(testes.tabela_dados_reais(reais), reais)
    assert "nenhum dos dois testes rejeita H₀" in decisao and "Welch: p = 0,274" in decisao and "Mann-Whitney: p = 0,600" in decisao
    assert "g de Hedges = −0,28 (pequeno)" in efeito and "δ de Cliff = −0,08 (negligível)" in efeito
    assert "(17,8 h)" in efeito and "(17,2 h)" in efeito and "0,7 h maior" in efeito and "4%" in efeito
    assert "não tem importância prática evidente" in efeito and "20%" in efeito
    assert "Os sinais das medidas não coincidem" in efeito   # g e Cliff negativos, mas a mediana de com_bot é maior
    assert "com 30 PRs por grupo" in cautela


def test_dois_testes_que_rejeitam_dizem_de_que_lado_esta_o_efeito():
    decisao, efeito, cautela, _ = paragrafos(np.arange(1.0, 31), np.arange(101.0, 131))
    assert "os dois testes rejeitam H₀" in decisao and "chegam à mesma conclusão" in decisao
    assert "o Welch aponta média menor no grupo com bot" in decisao
    assert "o Mann-Whitney aponta que os PRs com bot tendem a demorar menos" in decisao
    assert "pode ter importância prática" in efeito and "Os sinais" not in efeito
    assert cautela.startswith("Rejeitar H₀ diz") and "Não rejeitar" not in cautela
    inverso = paragrafos(np.arange(101.0, 131), np.arange(1.0, 31))[0]
    assert "média maior" in inverso and "tendem a demorar mais" in inverso


def test_testes_que_discordam_sao_explicados_nos_dois_sentidos():
    r = np.random.default_rng(1)
    so_postos = paragrafos(r.lognormal(0, 2, 30), r.lognormal(1.2, 2, 30))[0]
    assert "Os dois testes discordam" in so_postos and "o Welch não rejeita H₀" in so_postos
    assert "o Mann-Whitney rejeita H₀" in so_postos and "a divergência faz parte do resultado" in so_postos
    assert "compara médias" in so_postos and "compara postos" in so_postos
    assert "Welch aponta" not in so_postos and "Mann-Whitney aponta" in so_postos   # só o que rejeita tem sentido
    r = np.random.default_rng(0)
    so_media = paragrafos(np.concatenate([r.uniform(9, 11, 24), r.uniform(60, 90, 6)]),
                          np.concatenate([r.uniform(9, 11, 24), r.uniform(10, 12, 6)]))[0]
    assert "o Welch rejeita H₀" in so_media and "o Mann-Whitney não rejeita H₀" in so_media
    assert "Welch aponta média maior" in so_media and "Mann-Whitney aponta" not in so_media


def test_dados_sem_variacao_geram_um_texto_de_teste_nao_calculado():
    decisao = paragrafos([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])[0]
    assert "não pôde ser calculado" in decisao and "indefinido" in decisao


def test_diferenca_de_20_por_cento_ou_efeito_medio_conta_como_importancia_pratica():
    r = np.random.default_rng(7)
    base = r.lognormal(2.5, 0.4, 40)
    efeito = paragrafos(base * 1.3, base)[1]   # 30% a mais, mesma forma
    assert "pode ter importância prática" in efeito and "30%" in efeito
    pequena = paragrafos(base * 1.05, base)[1]
    assert "não tem importância prática evidente" in pequena


def test_a_cautela_cita_os_dois_tamanhos_quando_os_grupos_diferem():
    cautela = paragrafos(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.0]))[2]
    assert "com 5 e 6 PRs por grupo" in cautela


def test_p_valor_muito_pequeno_aparece_em_notacao_cientifica():
    tabela = testes.tabela_dados_reais(prs(np.arange(1.0, 31), np.arange(1001.0, 1031)))
    html = dashboard.tabela_dados_reais_html(tabela)
    assert tabela["p_valor"].max() < 1e-3
    assert re.search(r"<td>\d,\de−\d\d</td>", html)


def test_tabela_dados_reais_html_mostra_o_nivel_de_significancia():
    tabela = testes.tabela_dados_reais(prs(A_REAL, B_REAL))
    assert "Conclusão (α = 0,05)" in dashboard.tabela_dados_reais_html(tabela)
    assert "Conclusão (α = 0,01)" in dashboard.tabela_dados_reais_html(tabela, alfa=0.01)


def test_falha_na_tabela_dos_dados_reais_vira_marcador_e_o_resto_da_pagina_sai(monkeypatch, tmp_path):
    def quebra(_):
        raise ValueError("sem dados")

    monkeypatch.setattr(testes, "tabela_dados_reais", quebra)
    saida = tmp_path / "index.html"
    dashboard.montar(saida, config.carregar())
    pagina = saida.read_text(encoding="utf-8")
    assert "Tabela indisponível" in secao_6(pagina) and "ValueError: sem dados" in secao_6(pagina)
    assert all(f'<section id="{ancora}">' in pagina for ancora, _ in dashboard.SECOES)


A_REAL = np.arange(1.0, 11)
B_REAL = np.arange(2.0, 12)
