import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab04 import calibracao, config, dashboard, gerador, graficos, testes


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    saida = tmp_path_factory.mktemp("dashboard") / "sub" / "index.html"
    dashboard.montar(saida)
    return saida.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pagina_com_conclusao(tmp_path_factory):
    """A página com `MOSTRAR_CONCLUSAO = True`, isto é, com a seção 7."""
    chave = pytest.MonkeyPatch()
    chave.setattr(dashboard, "MOSTRAR_CONCLUSAO", True)
    try:
        saida = tmp_path_factory.mktemp("dashboard_completo") / "index.html"
        dashboard.montar(saida)
        return saida.read_text(encoding="utf-8")
    finally:
        chave.undo()


def test_montar_grava_html_completo_em_utf8(pagina):
    assert pagina.startswith("<!DOCTYPE html>") and pagina.rstrip().endswith("</html>")
    assert '<meta charset="utf-8">' in pagina


def test_seis_secoes_na_ordem_fixa_e_a_conclusao_fica_de_fora(pagina):
    posicoes = [pagina.index(f'<section id="{ancora}">') for ancora, _ in dashboard.SECOES]
    assert posicoes == sorted(posicoes) and len(posicoes) == 6
    for _, titulo in dashboard.SECOES:
        assert f"<h2>{titulo}</h2>" in pagina
    assert pagina.count("<section ") == 6 and 'id="conclusao"' not in pagina and "7. Conclusão" not in pagina
    assert dashboard.MOSTRAR_CONCLUSAO is False


def test_com_a_chave_ligada_a_secao_7_volta_no_fim_da_pagina(pagina_com_conclusao):
    ancoras = re.findall(r'<section id="([\w-]+)">', pagina_com_conclusao)
    assert ancoras == [a for a, _ in dashboard.SECOES] + ["conclusao"]
    assert f"<h2>{dashboard.SECAO_CONCLUSAO[1]}</h2>" in pagina_com_conclusao
    assert "<h3>7. Conclusão</h3>" in folha(pagina_com_conclusao)


def test_links_no_topo_antes_das_secoes(pagina):
    inicio = pagina.index("<section")
    for link in (dashboard.LINK_KANBAN, dashboard.LINK_REPOSITORIO, dashboard.LINK_DASHBOARD):
        assert pagina.index(f'href="{link}"') < inicio


ENTREGA = config.CONFIG_PADRAO.parent / "docs" / "dashboard-entrega.html"


def test_dashboard_entregue_tem_os_links_publicados_no_topo():
    """`docs/dashboard-entrega.html` é a versão entregue, versionada à parte: não sai do comando único."""
    pagina = ENTREGA.read_text(encoding="utf-8")
    topo = pagina.split('<header class="topo">')[1].split("</header>")[0]
    for link in (dashboard.LINK_KANBAN, dashboard.LINK_REPOSITORIO, dashboard.LINK_DASHBOARD):
        assert f'href="{link}"' in topo
    assert "github.io" not in pagina and "publicação na S02-13" not in pagina
    assert pagina.count("<script") >= 1 and 'src="https://cdn.plot.ly' not in pagina   # Plotly embutido: abre sem internet


def test_secoes_1_a_3_tem_o_conteudo_e_os_graficos(pagina):
    secoes = re.split(r'<section id="', pagina)[1:]
    cenario, dados, testes = secoes[:3]
    assert "Pergunta." in cenario and "H₀" in cenario and "H₁" in cenario
    assert dados.count('class="plotly-graph-div"') == 1 and testes.count('class="plotly-graph-div"') == 2
    assert graficos.TEXTO_G1 in folha(pagina) and graficos.TEXTO_G2 in folha(pagina)
    assert "Em construção" not in pagina   # desde a S02-12 nenhuma seção está em construção
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
    assert pagina.count('class="plotly-graph-div"') == 4   # só o G3 e o G4, cada um em α = 5% e 1%: as seções 2 e 3 ficam com marcadores
    assert all(f'<section id="{ancora}">' in pagina for ancora, _ in dashboard.SECOES)


def test_texto_ausente_nao_quebra_a_pagina(monkeypatch, tmp_path):
    monkeypatch.delattr(graficos, "TEXTO_G2")
    saida = tmp_path / "index.html"
    dashboard.montar(saida)
    assert "<h2>3. Como os testes funcionam</h2>" in saida.read_text(encoding="utf-8")


# --- seções 4 e 5: erro tipo I (G3) e poder (G4) (S02-11) ---


def secao(pagina, ancora):
    return pagina.split(f'<section id="{ancora}">')[1].split("</section>")[0]


def folha(pagina):
    """A folha de interpretação (fora dos painéis; abre com a tecla i)."""
    return pagina.split('<aside id="interpretacao" hidden>')[1].split("</aside>")[0]


def test_nenhuma_secao_continua_em_construcao():
    assert dashboard.EM_CONSTRUCAO == {}


@pytest.mark.parametrize("ancora, nome", [("erro-tipo-1", "G3"), ("poder", "G4")])
def test_secoes_4_e_5_tem_o_grafico_e_a_legenda_e_o_texto_fica_na_folha(pagina, ancora, nome):
    trecho = secao(pagina, ancora)
    assert trecho.count('class="plotly-graph-div"') == 2 and f"{nome}: " in trecho   # α = 5% e α = 1%
    assert "n = 30 por grupo (10 em C4)" in trecho
    assert f'<p class="texto">{getattr(graficos, f"TEXTO_{nome}")}</p>' in folha(pagina)
    assert getattr(graficos, f"TEXTO_{nome}") not in trecho and "Em construção" not in trecho


def test_pagina_tem_os_sete_graficos_com_o_plotly_embutido_uma_vez(pagina):
    assert pagina.count('class="plotly-graph-div"') == 7   # G1, os dois G2, e G3 e G4 em α = 5% e 1%
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
    assert secao(pagina, presente).count('class="plotly-graph-div"') == 2


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
    assert graficos.TEXTO_G3 in folha(pagina)
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
    return secao(pagina, "dados-reais")


def test_a_secao_6_nao_esta_mais_em_construcao():
    assert "dados-reais" not in dashboard.EM_CONSTRUCAO


def test_secao_6_traz_a_tabela_com_os_numeros_dos_testes_nos_dados_reais(pagina):
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    t = testes.tabela_dados_reais(reais).set_index("teste")
    secao = secao_6(pagina)
    for cabecalho in ("Medida", "t de Welch", "Mann-Whitney", "Estatística", "p-valor", "Tamanho de efeito", "Razão de medianas", "Conclusão (α = 0,05)"):
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


def test_folha_traz_conclusao_efeito_cautela_e_limitacoes_em_uma_frase_dos_dados_reais(pagina):
    texto = folha(pagina).split("<h3>6. Dados reais</h3>")[1]
    assert "os dois chegam à mesma conclusão" in texto and "Tamanho de efeito:" in texto
    assert "importância prática" in texto and "Não rejeitar H₀ não prova que não há efeito" in texto
    assert dashboard.LIMITACOES in texto
    assert len([f for f in re.split(r"(?<=[.!?])\s+", dashboard.LIMITACOES.strip()) if f]) == 1
    assert "viés de seleção" in dashboard.LIMITACOES and "tamanho do PR" in dashboard.LIMITACOES
    assert 'class="texto"' not in secao_6(pagina)   # no painel só a tabela e a legenda


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


# --- seção 7: expectativa × resultado, recomendação e limitação (S02-12) ---

RAIZ_LAB = Path(__file__).resolve().parents[1]
SIMULACAO = RAIZ_LAB / "dados" / "simulacao"
NOMES = {"welch": "Welch", "mann_whitney": "Mann-Whitney"}


def _pct(x, casas=2):
    return f"{x * 100:.{casas}f}%".replace(".", ",")


def _pp(x):
    return f"{x:.1f}".replace(".", ",") + " p.p."


def linha(situacao):
    """O texto 'o que encontrou' da linha `situacao` (o início do rótulo) da tabela da seção 7."""
    return next(r for s, _, r, _ in dashboard.EXPECTATIVA_X_RESULTADO if s.startswith(situacao))


def test_folha_traz_a_tabela_a_recomendacao_as_condicoes_a_limitacao_e_os_commits(pagina_com_conclusao):
    trecho = folha(pagina_com_conclusao).split("<h3>7. Conclusão</h3>")[1]
    assert trecho.count("<tr>") == len(dashboard.EXPECTATIVA_X_RESULTADO) + 1
    assert "<strong>Recomendação.</strong>" in trecho and "<strong>Limitação principal.</strong>" in trecho
    assert trecho.count("<li>") == len(dashboard.CONDICOES_RECOMENDACAO)
    for sha, data, _ in dashboard.COMMITS.values():
        assert f'href="{dashboard.LINK_COMMIT}{sha}"' in trecho and f"<code>{sha[:7]}</code></a> ({data})" in trecho
    assert "Em construção" not in secao(pagina_com_conclusao, "conclusao")


def test_expectativas_citadas_estao_literalmente_na_secao_5_do_cenario():
    """A expectativa não é reescrita: cada citação da tabela está, palavra por palavra, no cenario.md."""
    texto = (RAIZ_LAB / "docs" / "cenario.md").read_text(encoding="utf-8")
    secao_5 = " ".join(texto.split("## 5.")[1].split("## 6.")[0].split())
    for _, citacoes, _, _ in dashboard.EXPECTATIVA_X_RESULTADO:
        for citacao in citacoes:
            assert citacao in secao_5, citacao


def test_erro_tipo_i_da_tabela_bate_com_o_classificacao_csv():
    c = pd.read_csv(SIMULACAO / "classificacao.csv")
    c5 = c[c["alfa"] == 0.05].set_index(["cenario", "teste"])
    for cenario in ("C0", "C1", "C2", "C3", "C4"):
        texto = linha(cenario)
        for teste, nome in NOMES.items():
            taxa, classe = c5.loc[(cenario, teste), ["taxa", "classificacao"]]
            assert f"{nome} com {_pct(taxa)}" in texto
            assert f"{nome} com {_pct(taxa)} ({classe}" in texto or (
                classe == "conservador" and "os dois conservadores" in texto
            )
    for cenario in ("C0", "C1"):   # o desvio citado
        teste = "mann_whitney" if cenario == "C0" else "welch"
        assert f"{c5.loc[(cenario, teste), 'desvio_pp']:.2f}".replace(".", ",").replace("-", "−") + " p.p." in linha(cenario)


def test_poder_da_tabela_e_da_recomendacao_bate_com_o_poder_csv():
    p = pd.read_csv(SIMULACAO / "poder.csv")
    p5 = p[p["alfa"] == 0.05]
    maximo = p5.groupby("cenario")["vantagem_pp"].apply(lambda s: s.abs().max())
    assert f"por no máximo {_pp(maximo['C0'])}" in linha("C0")
    assert f"até {_pp(maximo['C0'])}" in dashboard.CONDICOES_RECOMENDACAO[0]
    for cenario in ("C1", "C2", "C3"):
        assert _pp(maximo[cenario]) in linha(cenario)
        assert f"{_pp(maximo[cenario])} ({cenario})" in linha("Onde")
    assert f"até {round(maximo['C1'])} pontos percentuais" in dashboard.TEXTO_RECOMENDACAO
    lider = p5.groupby("cenario")["vantagem_pp"].apply(lambda s: "welch" if s.mean() < 0 else "mann_whitney")
    assert lider["C0"] == "welch" and (lider.drop("C0") == "mann_whitney").all()
    assert (p5[p5["cenario"] != "C0"]["melhor"] == "mann_whitney").all()   # "em todos os efeitos"
    c3, c4 = p5[p5["cenario"] == "C3"], p5[p5["cenario"] == "C4"].sort_values("delta").iloc[-1]
    assert f"não passa de {_pct(c3['poder_welch'].max(), 1)}" in linha("C3")
    assert f"{_pct(c4['poder_mann_whitney'], 1)} dos conjuntos e o Welch em {_pct(c4['poder_welch'], 1)}" in linha("C4")


def test_linha_de_alfa_1_por_cento_bate_com_os_csvs():
    p = pd.read_csv(SIMULACAO / "poder.csv").pivot_table(
        index=["cenario", "delta"], columns="alfa", values=["poder_welch", "poder_mann_whitney", "vantagem_pp"])
    for coluna in ("poder_welch", "poder_mann_whitney"):   # "o poder cai em todos os pontos"
        assert (p[(coluna, 0.01)] < p[(coluna, 0.05)]).all()
    lider = p["vantagem_pp"].groupby("cenario").mean() < 0   # True: Welch lidera
    assert (lider[0.01] == lider[0.05]).all()
    c = pd.read_csv(SIMULACAO / "classificacao.csv")
    por_alfa = c.pivot_table(index=["cenario", "teste"], columns="alfa", values="classificacao", aggfunc="first")
    assert (por_alfa[0.05] == por_alfa[0.01]).all()
    welch = c[(c["alfa"] == 0.01) & (c["teste"] == "welch") & (c["cenario"] != "C0")]["taxa"]
    assert f"de {_pct(welch.min())} a {_pct(welch.max())}" in linha("α")


def test_linha_e_texto_dos_dados_reais_batem_com_a_tabela_da_secao_6():
    from lab04.descritiva import horas_do_grupo

    cfg = config.carregar()
    reais = pd.read_csv(Path(cfg["pasta"]) / cfg["coleta"]["saida"])
    tabela = testes.tabela_dados_reais(reais).set_index("teste")
    texto = linha("Dados reais")
    assert not tabela["rejeita_h0"].any() and texto.startswith("Nenhum dos dois rejeita H₀")
    for teste, nome in NOMES.items():
        assert f"{nome}: p = {graficos._p_rotulo(tabela.loc[teste, 'p_valor'])}" in texto
    med_com, med_sem = (float(np.median(horas_do_grupo(reais, g))) for g in ("com_bot", "sem_bot"))
    assert f"{graficos._num(med_com, 1)} h com bot" in texto and f"{graficos._num(med_sem, 1)} h sem bot" in texto
    razao = tabela.loc["welch", "razao_medianas"]
    assert f"diferença de {graficos._num(abs(razao - 1) * 100, 0)}%" in texto
    assert f"g de Hedges = {graficos._num(tabela.loc['welch', 'tamanho_efeito'], 2)}" in texto
    assert f"δ de Cliff = {graficos._num(tabela.loc['mann_whitney', 'tamanho_efeito'], 2)}" in texto
    n = reais["grupo"].value_counts()
    assert n["com_bot"] == n["sem_bot"] and f"{n['com_bot']} PRs por grupo" in dashboard.TEXTO_DIFERENCA_DADOS_REAIS


def test_recomendacao_usa_o_erro_tipo_i_do_c1():
    c = pd.read_csv(SIMULACAO / "classificacao.csv").set_index(["cenario", "alfa", "teste"])
    assert f"ficou em {_pct(c.loc[('C1', 0.05, 'mann_whitney'), 'taxa'])}" in dashboard.TEXTO_RECOMENDACAO
    assert f"rejeitou só {_pct(c.loc[('C1', 0.05, 'welch'), 'taxa'])}" in dashboard.TEXTO_RECOMENDACAO


def _git(*args):
    """Saída do git na raiz do repositório, ou `pytest.skip` sem git ou com histórico raso (checkout do CI)."""
    try:
        saida = subprocess.run(["git", *args], cwd=RAIZ_LAB, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        pytest.skip("git indisponível")
    if saida.returncode != 0:
        pytest.skip(f"histórico do git indisponível: {saida.stderr.strip()}")
    return saida.stdout.strip()


def test_commits_citados_existem_com_a_data_e_o_arquivo_certos():
    for chave, arquivo in (("expectativa", "lab04/docs/cenario.md"), ("config_congelado", "lab04/config.yaml")):
        sha, data, _ = dashboard.COMMITS[chave]
        assert arquivo in _git("show", "--name-only", "--format=", sha).splitlines()
    for sha, data, _ in dashboard.COMMITS.values():
        assert _git("log", "-1", "--format=%ad", "--date=format:%d/%m/%Y", sha) == data


def test_expectativa_e_anterior_a_primeira_simulacao_e_config_nao_mudou_depois_de_congelado():
    expectativa = dashboard.COMMITS["expectativa"][0]
    simulacao = dashboard.COMMITS["primeira_simulacao"][0]
    congelado = dashboard.COMMITS["config_congelado"][0]
    for sha in (expectativa, simulacao, congelado):   # pula no checkout raso do CI, antes de qualquer assert
        _git("cat-file", "-e", f"{sha}^{{commit}}")
    ancestral = subprocess.run(["git", "merge-base", "--is-ancestor", expectativa, simulacao], cwd=RAIZ_LAB)
    assert ancestral.returncode == 0   # a expectativa está no histórico da primeira simulação
    instante = lambda sha: int(_git("log", "-1", "--format=%ct", sha))   # noqa: E731
    assert instante(expectativa) < instante(simulacao)
    assert _git("log", "-1", "--format=%H", "--", "config.yaml") == congelado


# --- layout de painel: KPIs, seletores, legendas curtas e interpretação recolhida ---


def kpis(pagina):
    """(rótulo, valor, subtítulo) de cada cartão da faixa de indicadores."""
    faixa = pagina.split('<div class="kpis">')[1].split('<div class="acoes">')[0]
    return re.findall(r"<span>(.*?)</span><strong>(.*?)</strong><small>(.*?)</small>", faixa)


def test_faixa_de_indicadores_vem_antes_das_secoes_e_tem_sete_cartoes(pagina):
    assert pagina.index('class="kpis"') < pagina.index("<section")
    assert [r for r, _, _ in kpis(pagina)] == [
        "PRs coletados", "Mediana até o merge", "p-valor nos dados reais", "Tamanho de efeito",
        "Erro tipo I · Mann-Whitney", "Erro tipo I · Welch", "Maior poder",
    ]


def test_indicadores_batem_com_os_dados_e_os_resultados(pagina):
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    t = testes.tabela_dados_reais(reais).set_index("teste")
    c = pd.read_csv(f"{cfg['pasta']}/dados/simulacao/classificacao.csv")
    c5 = c[c["alfa"] == 0.05]
    por_nome = {r: (v, s) for r, v, s in kpis(pagina)}
    assert por_nome["PRs coletados"] == ("60", "30 com bot · 30 sem bot")
    assert por_nome["Mediana até o merge"][0] == "17,8 h · 17,2 h"
    p_w, p_m = graficos._p_rotulo(t.loc["welch", "p_valor"]), graficos._p_rotulo(t.loc["mann_whitney", "p_valor"])
    assert por_nome["p-valor nos dados reais"][0] == f"{p_w} · {p_m}" and "nenhum rejeita H₀" in por_nome["p-valor nos dados reais"][1]
    for teste, nome in (("mann_whitney", "Erro tipo I · Mann-Whitney"), ("welch", "Erro tipo I · Welch")):
        taxas = c5[c5["teste"] == teste]["taxa"]
        assert por_nome[nome][0] == f"{graficos._num(taxas.min() * 100, 2)}%–{graficos._num(taxas.max() * 100, 2)}%"
    assert por_nome["Maior poder"] == ("Mann-Whitney 4/5", "cenários em que lidera · Welch: C0")


def test_indicadores_sem_resultados_ficam_so_com_os_dados_reais():
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    faixa = dashboard._indicadores(reais, None)
    assert faixa.count('<div class="kpi ') == 4 and "Erro tipo I" not in faixa
    assert dashboard._indicadores(reais.iloc[0:0], None) == ""   # sem dados, sem faixa


def test_topo_tem_os_links_os_indicadores_e_o_botao_da_folha_e_cada_secao_de_simulacao_o_seu_seletor_de_alfa(pagina):
    topo = pagina.split('<header class="topo">')[1].split("</header>")[0]
    assert all(f'href="{link}"' in topo for link in (dashboard.LINK_KANBAN, dashboard.LINK_REPOSITORIO, dashboard.LINK_DASHBOARD))
    assert topo.index('class="marca"') < topo.index('class="kpis"')   # os indicadores ficam numa linha, abaixo do título
    assert 'id="abrir-interpretacao"' in topo and "Interpretação (i)" in topo and "Gerado em" in topo
    assert 'name="alfa' not in topo and 'class="indice"' not in pagina
    for ancora, nome in (("erro-tipo-1", "alfa-g3"), ("poder", "alfa-g4")):
        trecho = secao(pagina, ancora)
        assert f'name="{nome}"' in trecho and 'value="5" checked' in trecho and 'value="1"' in trecho


def test_seletor_de_alfa_troca_g3_e_g4_com_5_por_cento_visivel(pagina):
    for ancora in ("erro-tipo-1", "poder"):
        trecho = secao(pagina, ancora)
        assert re.findall(r'<div data-painel="alfa" data-valor="(\d)"( hidden)?>', trecho) == [("5", ""), ("1", " hidden")]
        cinco, um = trecho.split('data-valor="1"')
        assert "= 5%)" in cinco and "= 1%)" not in cinco   # o JSON do Plotly escapa o α, então só o trecho ASCII
        assert "= 1%)" in um and "= 5%)" not in um


def test_g2_troca_entre_o_exemplo_sem_efeito_e_o_com_efeito(pagina):
    trecho = secao(pagina, "testes")
    assert 'name="g2"' in trecho and trecho.count('data-painel="g2"') == 4   # um gráfico e uma legenda por exemplo
    assert trecho.count('data-valor="sem">') == 2 and trecho.count('data-valor="com" hidden>') == 2
    assert "Sem efeito (H₀ verdadeira)" in trecho and "Com efeito (H₀ falsa)" in trecho


def test_script_troca_os_paineis_sincroniza_os_seletores_redimensiona_e_abre_a_folha(pagina):
    script = pagina.split("<script>")[-1]
    assert "function mostrar" in script and "p.hidden = p.dataset.valor !== valor" in script
    assert "o.checked = o.value === r.value" in script   # os dois seletores de α andam juntos
    assert "Plotly.Plots.resize" in script and "function redimensionar" in script and "addEventListener('load'" in script
    assert "e.key === 'Escape'" in script and "e.key === 'i'" in script
    assert "rotacao" not in script and "scale(" not in script and "IntersectionObserver" not in script


def test_cada_grafico_tem_uma_legenda_curta_de_uma_linha(pagina):
    for ancora, inicio in (("dados", "G1:"), ("testes", "G2, exemplo"), ("erro-tipo-1", "G3:"), ("poder", "G4:")):
        legendas = re.findall(r'<p class="legenda">(.*?)</p>', secao(pagina, ancora))
        assert any(l.split("n = 30 por grupo (10 em C4). ")[-1].startswith(inicio) for l in legendas), ancora
        assert all(len(l) < 330 for l in legendas), ancora   # legendas, não parágrafos


def test_interpretacao_fica_numa_folha_oculta_fora_dos_paineis(pagina):
    assert '<aside id="interpretacao" hidden>' in pagina and "<details" not in pagina
    assert pagina.index("</main>") < pagina.index('<aside id="interpretacao"')   # fora da grade de painéis
    assert 'id="fechar-interpretacao"' in folha(pagina) and "Fechar (Esc)" in folha(pagina)
    texto = folha(pagina)
    for titulo, conteudo in (("2. Os dados", graficos.TEXTO_G1), ("3. Como os testes funcionam", graficos.TEXTO_G2),
                             ("4. Erro tipo I", graficos.TEXTO_G3), ("5. Poder", graficos.TEXTO_G4)):
        assert f"<h3>{titulo}</h3>" in texto and conteudo in texto
        assert conteudo not in secao(pagina, {"2": "dados", "3": "testes", "4": "erro-tipo-1", "5": "poder"}[titulo[0]])


def test_sem_interpretacao_a_pagina_so_tem_graficos_tabelas_e_legendas(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "MOSTRAR_INTERPRETACAO", False)
    saida = tmp_path / "index.html"
    dashboard.montar(saida, config.carregar())
    pagina = saida.read_text(encoding="utf-8")
    assert 'id="interpretacao"' not in pagina and "abrir-interpretacao" not in pagina.split("<script>")[0]
    assert pagina.count('class="plotly-graph-div"') == 7
    for texto in (graficos.TEXTO_G1, graficos.TEXTO_G2, graficos.TEXTO_G3, graficos.TEXTO_G4, dashboard.TEXTO_RECOMENDACAO):
        assert texto not in pagina
    assert "<strong>Recomendação.</strong>" not in pagina and 'class="texto"' not in pagina
    assert "<table>" in secao(pagina, "dados-reais")


def test_secao_1_mostra_pergunta_hipoteses_e_dados_sem_os_paragrafos(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "MOSTRAR_INTERPRETACAO", False)
    saida = tmp_path / "index.html"
    dashboard.montar(saida, config.carregar())
    trecho = secao(saida.read_text(encoding="utf-8"), "cenario")
    assert "<strong>Pergunta.</strong>" in trecho and "H₀" in trecho and "H₁" in trecho
    assert "supabase/supabase" in trecho and "com bot: 30 PRs" in trecho and "sem bot: 30 PRs" in trecho
    assert "01/08/2026 a 31/10/2026" in trecho and "semente 42" in trecho
    assert 'class="texto"' not in trecho


def test_secao_7_tem_um_selo_por_situacao_com_a_classe_certa(pagina_com_conclusao):
    trecho = secao(pagina_com_conclusao, "conclusao")
    assert trecho.count('class="selo ') == len(dashboard.EXPECTATIVA_X_RESULTADO) == 8
    assert trecho.count('class="selo sim"') == 6 and trecho.count('class="selo parte"') == 1 and trecho.count('class="selo nao"') == 1
    assert "Confirmado" in trecho and "Em parte" in trecho and "Não confirmado" in trecho
    assert "Recomendação" in trecho and "Limitação principal" in trecho


@pytest.mark.parametrize("confirmou, classe, rotulo", [
    ("Sim", "sim", "Confirmado"), ("Sim; o Mann-Whitney ficou acima", "sim", "Confirmado"),
    ("Em parte: o Welch ficou abaixo", "parte", "Em parte"), ("Não", "nao", "Não confirmado"),
])
def test_selo_classifica_o_confirmou_pela_primeira_palavra(confirmou, classe, rotulo):
    selo = dashboard._selo("C9", confirmou)
    assert f'class="selo {classe}"' in selo and f"<b>{rotulo}</b>" in selo and "<span>C9</span>" in selo


def test_selo_com_texto_desconhecido_mostra_o_proprio_texto():
    assert "<b>talvez</b>" in dashboard._selo("C9", "talvez")


def test_recomendacao_curta_bate_com_o_classificacao_csv_e_o_poder_csv():
    cfg = config.carregar()
    pasta = f"{cfg['pasta']}/dados/simulacao"
    c = pd.read_csv(f"{pasta}/classificacao.csv").set_index(["cenario", "alfa", "teste"])["taxa"]
    p = pd.read_csv(f"{pasta}/poder.csv")
    c1 = p[(p["cenario"] == "C1") & (p["alfa"] == 0.05)]
    assert graficos._num(c[("C1", 0.05, "mann_whitney")] * 100, 2) + "%" in dashboard.RECOMENDACAO_CURTA
    assert graficos._num(c[("C1", 0.05, "welch")] * 100, 2) + "%" in dashboard.RECOMENDACAO_CURTA
    assert f"{c1['vantagem_pp'].max():.0f} p.p." in dashboard.RECOMENDACAO_CURTA


def test_limitacao_curta_cita_o_c5_e_a_amostra():
    assert "C5 não foi feito" in dashboard.LIMITACAO_CURTA and "30 PRs por grupo" in dashboard.LIMITACAO_CURTA


def test_folha_vazia_com_a_chave_desligada(monkeypatch):
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    assert dashboard._interpretacao(cfg, reais, ["parágrafo"]).startswith('<aside id="interpretacao" hidden>')
    monkeypatch.setattr(dashboard, "MOSTRAR_INTERPRETACAO", False)
    assert dashboard._interpretacao(cfg, reais, ["parágrafo"]) == ""


# --- painel de parede: uma tela fixa, tema escuro e gráficos compactos ---


def test_secoes_ficam_uma_abaixo_da_outra_numa_coluna_que_rola(pagina):
    assert '<main class="coluna">' in pagina and 'id="palco"' not in pagina and "1920px" not in pagina
    assert "overflow: hidden" not in dashboard.ESTILO and "grid-template-rows" not in dashboard.ESTILO.split("main.coluna")[1].split("}")[0]
    posicoes = [pagina.index(f'<section id="{ancora}">') for ancora, _ in dashboard.SECOES]
    assert posicoes == sorted(posicoes)
    for ancora in ("dados", "testes", "erro-tipo-1", "poder"):   # os gráficos têm altura própria
        assert re.search(rf"#{ancora} \.corpo {{ height: \d+px; }}", dashboard.ESTILO), ancora


def test_tema_escuro_e_sem_barra_de_ferramentas_do_plotly(pagina):
    assert "background: #0b1020" in pagina and '"displayModeBar": false' in pagina


def test_secoes_tem_so_o_titulo_o_conteudo_e_a_legenda_sem_paragrafos_longos(pagina):
    for ancora, titulo in dashboard.SECOES:
        trecho = secao(pagina, ancora)
        assert f"<h2>{titulo}</h2>" in trecho and 'class="texto"' not in trecho and "<details" not in trecho


def figura_compacta(nome, *args):
    figura = getattr(graficos, nome)(*args)
    dashboard._compacto(figura, nome)
    return figura


def resultados_csv():
    cfg = config.carregar()
    return pd.read_csv(f"{cfg['pasta']}/dados/simulacao/resultados.csv")


@pytest.mark.parametrize("nome", ["g3", "g4"])
def test_figuras_compactas_sao_escuras_transparentes_e_sem_titulo(nome):
    figura = figura_compacta(nome, resultados_csv())
    assert figura.layout.title.text is None and figura.layout.height is None and figura.layout.width is None
    assert figura.layout.paper_bgcolor == "rgba(0,0,0,0)" and figura.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert figura.layout.font.size == 13 and figura.layout.xaxis.automargin is True


def test_g4_compacto_poe_a_unidade_no_titulo_da_faceta_e_um_so_titulo_no_eixo_y():
    figura = figura_compacta("g4", resultados_csv(), 0.05, dashboard.NOMES_CURTOS_CENARIOS)
    titulos = [a.text for a in figura.layout.annotations if a.text and not a.textangle]
    assert titulos[0] == "C0 normal · δ em dp" and all(t.endswith("· razão de medianas (×)") for t in titulos[1:5])
    assert [a.text for a in figura.layout.annotations if a.textangle == -90] == ["Rejeições de H₀ (%)"]
    assert all(not eixo.title.text for eixo in (figura.layout.xaxis, figura.layout.xaxis2, figura.layout.yaxis, figura.layout.yaxis4))
    assert figura.layout.legend.x == 0.72 and figura.layout.legend.orientation == "v"   # na faceta vazia


def test_g1_compacto_encurta_os_titulos_dos_paineis():
    cfg = config.carregar()
    reais = pd.read_csv(f"{cfg['pasta']}/{cfg['coleta']['saida']}")
    exemplos = gerador.exemplos_calibrados(calibracao.ler(f"{cfg['pasta']}/{cfg['calibracao']['saida']}"))
    exemplo = exemplos["com_efeito"]
    figura = figura_compacta("g1", reais, (exemplo["a"], exemplo["b"]))
    assert [a.text for a in figura.layout.annotations] == ["Dados reais", "Simulados: lognormal calibrada"]


def test_g2_compacto_esconde_a_legenda_e_deixa_o_rotulo_do_p_valor_legivel_no_tema_escuro():
    cfg = config.carregar()
    exemplos = gerador.exemplos_calibrados(calibracao.ler(f"{cfg['pasta']}/{cfg['calibracao']['saida']}"))
    figura = figura_compacta("g2", exemplos["sem_efeito"])
    assert figura.layout.showlegend is False
    rotulos = [a for a in figura.layout.annotations if a.text and a.text.startswith("p-valor")]
    assert len(rotulos) == 2 and all(a.bgcolor == "rgba(20,26,46,0.9)" for a in rotulos)


def test_g3_compacto_poe_a_legenda_em_cima():
    figura = figura_compacta("g3", resultados_csv())
    assert figura.layout.legend.orientation == "h" and figura.layout.legend.y == 1.0 and figura.layout.legend.yanchor == "bottom"


def test_figuras_do_painel_usam_nomes_curtos_nos_cenarios(pagina):
    for curto in dashboard.NOMES_CURTOS_CENARIOS.values():
        assert curto in secao(pagina, "erro-tipo-1")


def test_tabela_dos_dados_reais_tem_uma_coluna_por_teste_e_uma_linha_por_medida(pagina):
    tabela = secao_6(pagina).split("<table>")[1].split("</table>")[0]
    linhas = re.findall(r"<tr>(.*?)</tr>", tabela, flags=re.S)
    assert len(linhas) == 7   # cabeçalho + 6 medidas
    assert re.findall(r"<th>(.*?)</th>", linhas[0]) == ["Medida", "t de Welch", "Mann-Whitney"]
    assert [re.findall(r"<th>(.*?)</th>", l)[0] for l in linhas[1:]] == [
        "Compara", "Estatística", "p-valor", "Tamanho de efeito", "Razão de medianas (com bot ÷ sem bot)", "Conclusão (α = 0,05)"]
    assert all(l.count("<td>") == 2 for l in linhas[1:])


def test_selos_usam_nomes_curtos_e_guardam_a_situacao_completa_no_title():
    selo = dashboard._selo("C1: referência (lognormal calibrada)", "Em parte: o Welch ficou abaixo")
    assert "<span>C1 lognormal</span>" in selo and 'title="C1: referência (lognormal calibrada)"' in selo
    assert "<span>Muda de lado</span>" in dashboard._selo("Onde a vantagem muda de lado", "Sim")
    assert "<span>α = 1%</span>" in dashboard._selo("α = 0,01", "Sim")
    assert "<span>Situação nova</span>" in dashboard._selo("Situação nova", "Sim")   # sem apelido, usa o próprio texto


def test_nao_ha_rotacao_automatica_nem_ajuste_de_palco(pagina):
    script = pagina.split("<script>")[-1]
    assert "URLSearchParams" not in script and "setInterval" not in script   # a página é estática, o professor rola




def test_controle_com_sufixo_tem_name_proprio_mas_o_mesmo_grupo():
    a = dashboard._controle("alfa", [("5", "α = 5%"), ("1", "α = 1%")], "5", "Nível", sufixo="g3")
    b = dashboard._controle("alfa", [("5", "α = 5%"), ("1", "α = 1%")], "5", "Nível", sufixo="g4")
    assert a.count('name="alfa-g3"') == 2 and b.count('name="alfa-g4"') == 2
    assert a.count('data-grupo="alfa"') == b.count('data-grupo="alfa"') == 2
    sem = dashboard._controle("g2", [("sem", "Sem"), ("com", "Com")], "sem", "Exemplo")
    assert sem.count('name="g2"') == 2   # sem sufixo, o name é o próprio grupo


def test_indicadores_ficam_numa_linha_abaixo_do_titulo_e_a_pagina_nao_tem_barra_fixa(pagina):
    assert "position: sticky" not in pagina and ".kpis { display: grid;" in dashboard.ESTILO
    assert "repeat(auto-fit, minmax(170px, 1fr))" in dashboard.ESTILO


def test_o_seletor_de_alfa_de_uma_secao_aparece_no_cabecalho_dela(pagina):
    for ancora in ("erro-tipo-1", "poder"):
        cabecalho = secao(pagina, ancora).split('<div class="corpo">')[0]
        assert "<h2>" in cabecalho and 'class="controle"' in cabecalho and "Nível de significância" in cabecalho
