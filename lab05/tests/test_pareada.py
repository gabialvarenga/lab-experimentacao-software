"""Testes de `lab05/pareada.py` (S02-01)."""

import itertools

import numpy as np
import pandas as pd
import pytest

from conftest import coleta_sintetica
from lab05 import pareada, testes


def _com_ids(df):
    return df.assign(execucao_id=[f"{l.servidor}-t{l.io_threads}-{l.carga}-r{l.repeticao:02d}" for l in df.itertuples()])


def test_ler_refeitas(tmp_path):
    assert pareada.ler_refeitas(tmp_path / "falhas.csv") == set()
    pd.DataFrame({"execucao_id": ["redis-t1-get-r02", "redis-t1-get-r02"], "etapa": ["subida", "carga"]}).to_csv(
        tmp_path / "falhas.csv", index=False
    )
    assert pareada.ler_refeitas(tmp_path / "falhas.csv") == {"redis-t1-get-r02"}


def test_formar_pares_exclui_o_par_refeito_e_o_incompleto():
    df = _com_ids(coleta_sintetica(n=3))
    df = df[~((df["servidor"] == "valkey") & (df["io_threads"] == 4) & (df["carga"] == "set") & (df["repeticao"] == 3))]
    pares = pareada.formar_pares(df, "ops_s", {"redis-t1-get-r02"})
    assert len(pares) == 2 * 3 * 3 and list(pares.columns) == ["io_threads", "carga", "repeticao", "valkey", "redis", "excluido"]
    excluidos = pares[pares["excluido"]][["io_threads", "carga", "repeticao"]].to_records(index=False).tolist()
    assert sorted(excluidos) == [(1, "get", 2), (4, "set", 3)]


def test_formar_pares_recusa_entradas_invalidas():
    df = coleta_sintetica(n=2)
    with pytest.raises(ValueError, match="execucao_id"):
        pareada.formar_pares(df, "ops_s", {"x"})
    with pytest.raises(ValueError, match="repeticao"):
        pareada.formar_pares(df.drop(columns="repeticao"), "ops_s")
    with pytest.raises(ValueError, match="mais de uma"):
        pareada.formar_pares(pd.concat([df, df.head(1)]), "ops_s")


def test_formar_pares_sem_um_dos_servidores_exclui_tudo():
    pares = pareada.formar_pares(coleta_sintetica(n=2).query("servidor == 'redis'"), "ops_s")
    assert pares["excluido"].all() and pares["valkey"].isna().all()


@pytest.mark.parametrize("n", [1, 3, 6, 10])
def test_distribuicao_dos_postos_sinalizados_confere_com_a_enumeracao(n):
    somas = [sum(k for k, s in zip(range(1, n + 1), sinais) if s) for sinais in itertools.product([0, 1], repeat=n)]
    esperado = np.bincount(somas, minlength=n * (n + 1) // 2 + 1) / 2**n
    assert pareada._distribuicao_postos_sinalizados(n) == pytest.approx(esperado)


def test_hodges_lehmann_confere_com_a_conta_feita_a_mao():
    d = np.array([1.0, 2.0, 4.0])
    # médias de Walsh: 1; 1,5; 2,5; 2; 3; 4 → mediana 2,25
    r = pareada.hodges_lehmann(d)
    assert r["estimativa"] == pytest.approx(2.25)
    # 3 pares: nem c = 0 dá 95%; o IC é o mais largo, com cobertura 1 − 2/8
    assert (r["ic_inf"], r["ic_sup"], r["cobertura"]) == (1.0, 4.0, pytest.approx(0.75))


def test_hodges_lehmann_com_5_pares_tem_cobertura_de_93_75_e_com_10_atinge_95():
    cinco = pareada.hodges_lehmann([0.1, 0.3, 0.2, 0.5, 0.4])
    assert cinco["cobertura"] == pytest.approx(0.9375) and (cinco["ic_inf"], cinco["ic_sup"]) == (0.1, 0.5)
    dez = pareada.hodges_lehmann(np.arange(1, 11, dtype=float))
    # valor crítico do Wilcoxon para n = 10, bicaudal a 5%: c = 8, P(T⁺ ≤ 8) = 25/1024
    walsh = np.sort([(a + b) / 2 for i, a in enumerate(range(1, 11)) for b in range(a, 11)])
    assert dez["cobertura"] == pytest.approx(1 - 2 * 25 / 1024)
    assert (dez["ic_inf"], dez["ic_sup"]) == (walsh[8], walsh[-9]) and dez["estimativa"] == pytest.approx(5.5)


def test_comparar_recupera_a_razao_e_tira_a_deriva_entre_blocos():
    df = coleta_sintetica(n=30, sigma=0.02, semente=1, razao=1.2)
    fatores = np.exp(np.random.default_rng(9).normal(0, 0.2, 30))  # deriva forte, comum aos dois servidores
    df["ops_s"] *= fatores[df["repeticao"] - 1]
    t = pareada.comparar(df, "ops_s")
    assert list(t.columns) == pareada.COLUNAS and len(t) == 6
    assert t["razao_hl"].to_numpy() == pytest.approx(1.2, rel=0.02)
    assert (t["desvio_log_razao"] < 0.05).all() and (t["cobertura_ic"] >= 0.95).all()
    assert (t["situacao"] == "diferença relevante").all() and (t["p_holm"] >= t["p_wilcoxon"]).all()
    assert t["situacao_principal"].isna().all()
    independente = testes.comparar(df, "ops_s", "mann_whitney", np.random.default_rng(0), 500)
    assert (independente["ic_sup"] - independente["ic_inf"]).min() > (t["ic_sup"] - t["ic_inf"]).max()


def test_comparar_junta_a_situacao_do_teste_principal():
    df = coleta_sintetica(n=8, sigma=0.05, semente=2)
    principal = testes.comparar(df, "lat_p99_ms", "mann_whitney", np.random.default_rng(0), 200)
    principal.loc[0, "situacao"] = "outra"
    t = pareada.comparar(df, "lat_p99_ms", principal=principal)
    assert (t["situacao_principal"] == principal["situacao"]).all()
    assert t["concorda"].tolist() == (t["situacao"] == principal["situacao"]).tolist() and not t.loc[0, "concorda"]


def test_comparar_conta_os_pares_excluidos():
    df = _com_ids(coleta_sintetica(n=5))
    t = pareada.comparar(df, "ops_s", {"valkey-t4-misto-r01", "redis-t4-misto-r03"}).set_index(["io_threads", "carga"])
    assert t.loc[(4, "misto"), "n_pares"] == 3 and t.loc[(4, "misto"), "n_excluidos"] == 2
    assert t["n_excluidos"].sum() == 2


def test_razao_constante_e_deterministica():
    df = coleta_sintetica(n=4, sigma=0.0, razao=0.87)
    t = pareada.comparar(df, "memoria_bytes")
    assert t["deterministica"].all() and t["p_wilcoxon"].isna().all()
    assert (t["situacao"] == "diferença relevante").all() and t["razao_hl"].to_numpy() == pytest.approx(0.87)


def test_comparar_recusa_poucos_pares_e_valores_nao_positivos():
    df = coleta_sintetica(n=3)
    with pytest.raises(ValueError, match="ao menos 2 pares"):
        pareada.comparar(df[df["repeticao"] == 1], "ops_s")
    with pytest.raises(ValueError, match="positivos"):
        pareada.comparar(df.assign(ops_s=0.0), "ops_s")


def test_no_piloto_o_wilcoxon_com_5_pares_nao_passa_de_0_0625(piloto):
    t = pareada.comparar(piloto, "ops_s")
    assert (t["n_pares"] == 5).all() and (t["p_wilcoxon"] >= 0.0625 - 1e-12).all()
    assert t["cobertura_ic"].to_numpy() == pytest.approx([0.9375] * 6) and (t["situacao"] == "inconclusivo").all()
