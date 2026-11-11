import copy
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab04 import config, resultados, simulacao

CFG = config.carregar()
SIM = config.simulacao(CFG)
IDS = [c["id"] for c in SIM["cenarios"]]
PASTA = Path(CFG["pasta"]) / "dados" / "simulacao"
ARQUIVOS = ["c0_c1.csv", "c2_c3.csv", "c4.csv"]


def bytes_lf(caminho) -> bytes:
    return Path(caminho).read_bytes().replace(b"\r\n", b"\n")


def tabela(linhas) -> pd.DataFrame:
    """Linhas `(cenario, delta, alfa, teste, rejeicoes)` com n = 30 e 10.000 repetições, no formato do CSV."""
    saida = []
    for cenario, delta, alfa, teste, rejeicoes in linhas:
        inf, sup = simulacao.intervalo_wilson(rejeicoes, 10_000)
        saida.append({"cenario": cenario, "delta": delta, "n": 30, "n_rep": 10_000, "alfa": alfa, "teste": teste,
                      "rejeicoes": rejeicoes, "taxa": rejeicoes / 10_000, "ic_inf": inf, "ic_sup": sup})
    return pd.DataFrame(saida, columns=simulacao.COLUNAS)


@pytest.fixture
def pasta_com_csvs(tmp_path):
    for nome in ARQUIVOS:
        shutil.copy(PASTA / nome, tmp_path / nome)
    return tmp_path


# --- consolidar ---


def test_consolidar_junta_os_tres_csvs_na_ordem_do_config():
    df = resultados.consolidar(PASTA, IDS)
    assert list(df.columns) == simulacao.COLUNAS and len(df) == 120
    assert list(df["cenario"].unique()) == IDS
    assert not df.duplicated(resultados.CHAVE).any()


def test_consolidar_nao_le_o_piloto_nem_as_saidas_geradas(pasta_com_csvs):
    for nome in ("piloto.csv", "resultados.csv", "classificacao.csv", "poder.csv"):
        shutil.copy(PASTA / "c4.csv", pasta_com_csvs / nome)   # se fossem lidos, repetiriam as linhas de C4
    assert len(resultados.consolidar(pasta_com_csvs)) == 120


def test_consolidar_nao_altera_nenhum_valor(pasta_com_csvs):
    df = resultados.consolidar(pasta_com_csvs)
    esperado = pd.concat([pd.read_csv(pasta_com_csvs / nome) for nome in ARQUIVOS], ignore_index=True)
    pd.testing.assert_frame_equal(df, esperado)


def test_cenario_opcional_ausente_ou_presente_nao_atrapalha(pasta_com_csvs):
    sem = resultados.consolidar(pasta_com_csvs, IDS)
    extra = pd.read_csv(pasta_com_csvs / "c4.csv").assign(cenario="C5")
    extra.to_csv(pasta_com_csvs / "c5.csv", index=False)
    com = resultados.consolidar(pasta_com_csvs, IDS)
    assert list(com["cenario"].unique()) == IDS + ["C5"]       # o opcional vem depois dos obrigatórios
    pd.testing.assert_frame_equal(com[com["cenario"] != "C5"].reset_index(drop=True), sem)


def test_obrigatorios_define_a_ordem(pasta_com_csvs):
    df = resultados.consolidar(pasta_com_csvs, ["C4", "C3", "C2", "C1", "C0"])
    assert list(df["cenario"].unique()) == ["C4", "C3", "C2", "C1", "C0"]


def test_consolidar_exige_os_cenarios_obrigatorios(pasta_com_csvs):
    (pasta_com_csvs / "c4.csv").unlink()
    with pytest.raises(ValueError, match="faltam os cenários.*C4"):
        resultados.consolidar(pasta_com_csvs, IDS)
    assert len(resultados.consolidar(pasta_com_csvs)) == 96   # sem exigir, junta o que existe


def test_consolidar_recusa_pasta_sem_csv(tmp_path):
    with pytest.raises(ValueError, match="nenhum CSV"):
        resultados.consolidar(tmp_path)


def test_consolidar_recusa_linhas_repetidas(pasta_com_csvs):
    shutil.copy(pasta_com_csvs / "c4.csv", pasta_com_csvs / "c4_de_novo.csv")
    with pytest.raises(ValueError, match="repetidas.*C4"):
        resultados.consolidar(pasta_com_csvs)


def test_consolidar_recusa_colunas_diferentes(pasta_com_csvs):
    pd.read_csv(pasta_com_csvs / "c4.csv").drop(columns="ic_sup").to_csv(pasta_com_csvs / "c4.csv", index=False)
    with pytest.raises(ValueError, match="c4.csv: colunas"):
        resultados.consolidar(pasta_com_csvs)


# --- classificar ---


def test_classificar_aplica_o_criterio_do_intervalo_de_wilson():
    # taxa de erro tipo I em α = 0,05 com 10.000 repetições: IC de ~[4,6%; 5,4%] em torno de 5%
    df = tabela([
        ("A", 0.0, 0.05, "welch", 500), ("A", 0.0, 0.05, "mann_whitney", 600),     # 5,0% ok; 6,0% liberal
        ("B", 0.0, 0.05, "welch", 400), ("B", 0.0, 0.05, "mann_whitney", 460),     # 4,0% conservador; 4,6% ok
    ])
    c = resultados.classificar(df).set_index(["cenario", "teste"])["classificacao"]
    assert c.to_dict() == {("A", "welch"): "ok", ("A", "mann_whitney"): "liberal",
                           ("B", "welch"): "conservador", ("B", "mann_whitney"): "ok"}


def test_classificar_usa_alfa_como_referencia_em_cada_nivel():
    df = tabela([("A", 0.0, 0.05, "welch", 100), ("A", 0.0, 0.01, "welch", 100)])   # taxa de 1%: baixa para α = 0,05, nominal para α = 0,01
    c = resultados.classificar(df).set_index("alfa")["classificacao"]
    assert c[0.05] == "conservador" and c[0.01] == "ok"


@pytest.mark.parametrize("rejeicoes, esperado", [(0, "conservador"), (10_000, "liberal")])
def test_taxa_zero_ou_um_continua_classificavel(rejeicoes, esperado):
    c = resultados.classificar(tabela([("A", 0.0, 0.05, "welch", rejeicoes)]))
    assert c["classificacao"].iloc[0] == esperado


def test_limite_do_ic_exatamente_em_alfa_e_ok():
    df = tabela([("A", 0.0, 0.05, "welch", 500)])
    df["ic_inf"] = 0.05
    assert resultados.classificar(df)["classificacao"].iloc[0] == "ok"
    df["ic_inf"], df["ic_sup"] = 0.03, 0.05
    assert resultados.classificar(df)["classificacao"].iloc[0] == "ok"


def test_classificar_traz_o_desvio_em_pontos_percentuais_e_so_a_linha_de_delta_zero():
    df = tabela([("A", 0.0, 0.05, "welch", 430), ("A", 0.5, 0.05, "welch", 3000)])
    c = resultados.classificar(df)
    assert list(c.columns) == resultados.COLUNAS_CLASSIFICACAO and len(c) == 1
    assert c["desvio_pp"].iloc[0] == pytest.approx(-0.7)


def test_classificar_exige_a_linha_de_delta_zero():
    with pytest.raises(ValueError, match="sem linha de δ = 0.*B"):
        resultados.classificar(tabela([("A", 0.0, 0.05, "welch", 500), ("B", 0.5, 0.05, "welch", 500)]))


def test_classificacao_dos_resultados_reais():
    c = resultados.classificar(resultados.consolidar(PASTA, IDS)).set_index(["cenario", "alfa", "teste"])["classificacao"]
    assert len(c) == len(IDS) * len(SIM["alfas"]) * 2 == 20
    welch = {id_: c[(id_, 0.05, "welch")] for id_ in IDS}
    mw = {id_: c[(id_, 0.05, "mann_whitney")] for id_ in IDS}
    assert welch == {"C0": "ok", "C1": "conservador", "C2": "conservador", "C3": "conservador", "C4": "conservador"}
    assert mw == {"C0": "conservador", "C1": "ok", "C2": "ok", "C3": "ok", "C4": "conservador"}
    assert "liberal" not in set(c)   # nenhum teste rejeita demais em nenhuma situação simulada


def test_classificacao_real_concorda_com_o_ic_do_registro_de_c0_c1():
    """A coluna `ic_inf`/`ic_sup` é a mesma do CSV de origem e a classe segue dela, linha a linha."""
    df = resultados.consolidar(PASTA, IDS)
    c = resultados.classificar(df)
    h0 = df[df["delta"] == 0].reset_index(drop=True)
    assert (c[["taxa", "ic_inf", "ic_sup"]].to_numpy() == h0[["taxa", "ic_inf", "ic_sup"]].to_numpy()).all()
    liberal = c["ic_inf"] > c["alfa"]
    conservador = c["ic_sup"] < c["alfa"]
    assert (c["classificacao"] == np.where(liberal, "liberal", np.where(conservador, "conservador", "ok"))).all()


# --- vantagem de poder e líderes ---


def poder_de(linhas):
    """`linhas`: `(cenario, delta, alfa, rejeicoes_welch, rejeicoes_mann_whitney)`."""
    base = []
    for cenario, delta, alfa, rw, rm in linhas:
        base += [(cenario, delta, alfa, "welch", rw), (cenario, delta, alfa, "mann_whitney", rm)]
    return resultados.vantagem_de_poder(tabela(base))


def test_vantagem_tem_o_sinal_e_a_unidade_certos():
    p = poder_de([("A", 0.5, 0.05, 3000, 5000), ("A", 1.0, 0.05, 7000, 6000)])
    assert list(p.columns) == resultados.COLUNAS_PODER
    assert list(p["vantagem_pp"]) == [20.0, -10.0]
    assert list(p["melhor"]) == ["mann_whitney", "welch"]


def test_diferenca_pequena_e_empate():
    p = poder_de([("A", 0.5, 0.05, 5000, 5050), ("A", 1.0, 0.05, 5000, 5300)])   # 0,5 p.p. ≈ 1 erro-padrão; 3 p.p. ≈ 4
    assert list(p["melhor"]) == ["empate", "mann_whitney"]


def test_vantagem_nao_inclui_delta_zero():
    p = poder_de([("A", 0.5, 0.05, 3000, 5000)])
    assert (p["delta"] > 0).all() and len(p) == 1


def test_vantagem_exige_as_mesmas_celulas_nos_dois_testes():
    df = tabela([("A", 0.5, 0.05, "welch", 3000), ("A", 0.5, 0.05, "mann_whitney", 5000), ("A", 1.0, 0.05, "welch", 6000)])
    with pytest.raises(ValueError, match="mesmas células"):
        resultados.vantagem_de_poder(df)


def test_lideres_distingue_lider_alternado_e_empate():
    p = poder_de([
        ("X", 0.5, 0.05, 3000, 5000), ("X", 1.0, 0.05, 6000, 8000),     # Mann-Whitney sempre
        ("Y", 0.5, 0.05, 5000, 3000), ("Y", 1.0, 0.05, 6000, 9000),     # alterna
        ("Z", 0.5, 0.05, 5000, 5020), ("Z", 1.0, 0.05, 6000, 6010),     # empate
    ])
    lid = resultados.lideres(p).set_index("cenario")
    assert lid["lider"].to_dict() == {"X": "mann_whitney", "Y": "alternado", "Z": "empate"}
    assert lid["inverte_com_o_efeito"].to_dict() == {"X": False, "Y": True, "Z": False}
    assert lid.loc["Y", "pontos_welch"] == 1 and lid.loc["Y", "pontos_mann_whitney"] == 1
    assert lid.loc["X", "vantagem_media_pp"] == 20.0 and lid.loc["X", "vantagem_maxima_pp"] == 20.0
    assert lid.loc["Y", "delta_vantagem_maxima"] == 1.0 and lid.loc["Y", "vantagem_maxima_pp"] == 30.0


def test_lideres_diferentes_do_primeiro_cenario():
    lid = pd.DataFrame({"cenario": ["C0", "C1", "C2"], "alfa": [0.05] * 3, "lider": ["welch", "mann_whitney", "welch"]})
    assert resultados.lideres_diferentes_do_primeiro(lid) == {0.05: [("C1", "mann_whitney")]}
    assert resultados.lideres_diferentes_do_primeiro(lid.assign(lider="welch")) == {0.05: []}


def test_poder_real_welch_lidera_o_controle_e_mann_whitney_lidera_os_demais():
    lid = resultados.lideres(resultados.vantagem_de_poder(resultados.consolidar(PASTA, IDS)))
    assert len(lid) == len(IDS) * len(SIM["alfas"])
    por = lid.set_index(["cenario", "alfa"])["lider"]
    for alfa in SIM["alfas"]:
        assert por[("C0", alfa)] == "welch"
        assert all(por[(c, alfa)] == "mann_whitney" for c in ("C1", "C2", "C3", "C4"))
    assert not lid["inverte_com_o_efeito"].any()   # a vantagem muda de lado entre cenários, não ao longo do efeito


def test_poder_real_tem_uma_linha_por_cenario_efeito_e_alfa_com_efeito():
    p = resultados.vantagem_de_poder(resultados.consolidar(PASTA, IDS))
    assert len(p) == sum(len(c["efeitos"]) - 1 for c in SIM["cenarios"]) * len(SIM["alfas"]) == 50
    c1 = p[(p["cenario"] == "C1") & (p["alfa"] == 0.05) & (p["delta"] == 1.6)].iloc[0]
    assert c1["poder_mann_whitney"] > c1["poder_welch"] and c1["vantagem_pp"] == pytest.approx(41.0)


# --- resumo e saídas ---


def test_resumo_traz_as_secoes_e_responde_onde_a_vantagem_muda_de_lado():
    df = resultados.consolidar(PASTA, IDS)
    poder = resultados.vantagem_de_poder(df)
    texto = resultados.resumo(resultados.classificar(df), poder, resultados.lideres(poder))
    for secao in ("## Erro tipo I (δ = 0)", "## Poder (α = 0,05)", "## Quem lidera em cada cenário",
                  "## Onde a vantagem de poder muda de lado"):
        assert secao in texto
    assert "em C0 lidera Welch; o líder muda em C1 (Mann-Whitney), C2 (Mann-Whitney)" in texto
    assert "**Ao longo do efeito, dentro de um cenário:** nenhum." in texto
    assert "0.05" not in texto and "0,05" in texto   # vírgula decimal em todo o texto


def test_resumo_lista_os_cenarios_que_alternam_ao_longo_do_efeito():
    p = poder_de([("Y", 0.5, 0.05, 5000, 3000), ("Y", 1.0, 0.05, 6000, 9000)])
    texto = resultados.resumo(resultados.classificar(tabela([("Y", 0.0, 0.05, "welch", 500)])), p, resultados.lideres(p))
    assert "**Ao longo do efeito, dentro de um cenário:** Y (α = 0,05)." in texto


def cfg_em(pasta):
    cfg = copy.deepcopy(CFG)
    cfg["pasta"] = str(pasta)
    return cfg


def test_executar_grava_as_quatro_saidas_ao_lado_de_resultados(tmp_path):
    (tmp_path / "dados" / "simulacao").mkdir(parents=True)
    for nome in ARQUIVOS:
        shutil.copy(PASTA / nome, tmp_path / "dados" / "simulacao" / nome)
    saida = resultados.executar(cfg_em(tmp_path))
    pasta = tmp_path / "dados" / "simulacao"
    assert {p.name for p in saida["caminhos"].values()} == {"resultados.csv", "classificacao.csv", "poder.csv", "resumo-resultados.md"}
    assert all((pasta / p.name).exists() for p in saida["caminhos"].values())


def test_executar_sem_um_cenario_obrigatorio_falha_sem_gravar(tmp_path):
    (tmp_path / "dados" / "simulacao").mkdir(parents=True)
    shutil.copy(PASTA / "c0_c1.csv", tmp_path / "dados" / "simulacao" / "c0_c1.csv")
    with pytest.raises(ValueError, match="faltam os cenários"):
        resultados.executar(cfg_em(tmp_path))
    assert not (tmp_path / "dados" / "simulacao" / "resultados.csv").exists()


def test_resultados_csv_e_a_concatenacao_dos_tres_csvs():
    esperado = bytes_lf(PASTA / "c0_c1.csv")
    for nome in ARQUIVOS[1:]:
        esperado += b"".join(bytes_lf(PASTA / nome).splitlines(keepends=True)[1:])
    assert bytes_lf(PASTA / "resultados.csv") == esperado


@pytest.mark.parametrize("nome", ["resultados.csv", "classificacao.csv", "poder.csv", "resumo-resultados.md"])
def test_arquivos_versionados_sao_os_que_o_comando_gera_dos_csvs_atuais(tmp_path, nome):
    """Se um CSV de simulação mudar, as saídas versionadas precisam ser regeradas (`python -m lab04.resultados`)."""
    (tmp_path / "dados" / "simulacao").mkdir(parents=True)
    for csv in ARQUIVOS:
        shutil.copy(PASTA / csv, tmp_path / "dados" / "simulacao" / csv)
    resultados.executar(cfg_em(tmp_path))
    assert bytes_lf(tmp_path / "dados" / "simulacao" / nome) == bytes_lf(PASTA / nome)


def test_main_imprime_os_caminhos_e_a_contagem(capsys, tmp_path):
    (tmp_path / "dados" / "simulacao").mkdir(parents=True)
    for nome in ARQUIVOS:
        shutil.copy(PASTA / nome, tmp_path / "dados" / "simulacao" / nome)
    config_copia = tmp_path / "config.yaml"
    shutil.copy(Path(CFG["pasta"]) / "config.yaml", config_copia)
    assert resultados.main(["--config", str(config_copia)]) == 0
    saida = capsys.readouterr().out
    assert "120 linhas consolidadas" in saida and "'conservador': 12" in saida and "'ok': 8" in saida
