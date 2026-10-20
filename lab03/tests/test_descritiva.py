import math
import os

import pandas as pd
import pytest

from analise.descritiva import (
    categorias_c1,
    descrever,
    faixas_por_metrica,
    main,
    proporcao_censurada,
)


def tabela(**colunas):
    """DataFrame mínimo de repositórios; colunas ausentes ficam de fora."""
    return pd.DataFrame(colunas)


def linha(df, metrica):
    return df[df["metrica"] == metrica].iloc[0]


def csv_completo(**extras):
    base = {
        "full_name": ["a/a", "b/b", "c/c", "d/d"],
        "frequencia_semana": [0.5, 2.0, 10.0, 0.05],
        "lead_time_a_h": [10.0, 100.0, 400.0, 1000.0],
        "lead_time_b_h": [5.0, 50.0, 300.0, None],
        "cfr_a": [0.0, 0.2, 0.4, 0.9],
        "recuperacao_mediana_h": [0.5, 5.0, None, 200.0],
        "n_episodios": [4, 10, 0, 5],
        "n_censurados_direita": [1, 0, 0, 5],
        "n_censurados_esquerda": [1, 1, 0, 0],
        "categoria_c1": ["Elite", "High", "Medium", "Low"],
    }
    base.update(extras)
    return pd.DataFrame(base)


def test_descrever_mediana_quartis_e_n():
    df = tabela(lead_time_a_h=[1.0, 2.0, 3.0, 4.0, 5.0])
    r = linha(descrever(df, ["lead_time_a_h"]), "lead_time_a_h")
    assert r["n"] == 5
    assert r["n_indefinido"] == 0
    assert (r["mediana"], r["q1"], r["q3"], r["minimo"], r["maximo"]) == (3.0, 2.0, 4.0, 1.0, 5.0)


def test_descrever_conta_vazios_sem_tratar_como_zero():
    df = tabela(recuperacao_mediana_h=[2.0, None, 4.0, None])
    r = linha(descrever(df, ["recuperacao_mediana_h"]), "recuperacao_mediana_h")
    assert (r["n"], r["n_indefinido"]) == (2, 2)
    assert r["mediana"] == 3.0
    assert r["minimo"] == 2.0


def test_descrever_metrica_sem_nenhum_valor_vira_nan():
    df = tabela(cfr_a=[None, None])
    r = linha(descrever(df, ["cfr_a"]), "cfr_a")
    assert (r["n"], r["n_indefinido"]) == (0, 2)
    assert math.isnan(r["mediana"])


def test_descrever_valor_extremo_nao_move_a_mediana():
    df = tabela(frequencia_semana=[1.0, 2.0, 3.0, 4.0, 50000.0])
    r = linha(descrever(df, ["frequencia_semana"]), "frequencia_semana")
    assert r["mediana"] == 3.0
    assert r["maximo"] == 50000.0


def test_faixas_por_metrica_usa_as_notas_da_classificacao():
    df = csv_completo()
    f = faixas_por_metrica(df, ["frequencia_semana"])
    r = linha(f, "frequencia_semana")
    # 0.5 -> Medium (>= 12/52,14 semanas), 2 -> High, 10 -> Elite, 0.05 -> Low
    assert (r["Elite"], r["High"], r["Medium"], r["Low"], r["indefinido"]) == (1, 1, 1, 1, 0)


def test_faixas_por_metrica_conta_indefinido_a_parte():
    df = csv_completo()
    r = linha(faixas_por_metrica(df, ["recuperacao_mediana_h"]), "recuperacao_mediana_h")
    # 0.5 h Elite, 5 h High, vazio, 200 h Low (>= 1 semana = 168 h)
    assert (r["Elite"], r["High"], r["Medium"], r["Low"], r["indefinido"]) == (1, 1, 0, 1, 1)
    assert r[["Elite", "High", "Medium", "Low", "indefinido"]].sum() == 4


def test_faixas_cfr_e_lead_time_usam_os_cortes_de_cada_metrica():
    df = csv_completo()
    cfr = linha(faixas_por_metrica(df, ["cfr_a"]), "cfr_a")
    assert (cfr["Elite"], cfr["High"], cfr["Medium"], cfr["Low"]) == (1, 1, 1, 1)
    lead = linha(faixas_por_metrica(df, ["lead_time_a_h"]), "lead_time_a_h")
    # 10 h Elite, 100 h High, 400 h Medium, 1000 h Low (>= 720 h)
    assert (lead["Elite"], lead["High"], lead["Medium"], lead["Low"]) == (1, 1, 1, 1)


def test_categorias_c1_soma_o_total_e_inclui_categorias_vazias():
    df = tabela(categoria_c1=["High", "High", "Elite"])
    c = categorias_c1(df)
    assert list(c["categoria"]) == ["Elite", "High", "Medium", "Low"]
    assert list(c["n_repositorios"]) == [1, 2, 0, 0]


def test_categorias_c1_registra_repositorio_sem_categoria():
    df = tabela(categoria_c1=["High", None])
    c = categorias_c1(df)
    assert c["n_repositorios"].sum() == 2
    assert c.iloc[-1]["categoria"] == "indefinida"


def test_proporcao_censurada_soma_as_duas_pontas_e_divide_pelos_episodios():
    df = csv_completo()
    p = proporcao_censurada(df)
    # repositório c/c tem 0 episódios: proporção indefinida
    assert p.tolist()[:2] == [0.5, 0.1]
    assert math.isnan(p.iloc[2])
    assert p.iloc[3] == 1.0


def test_main_grava_tabelas_e_figuras(tmp_path):
    csv = tmp_path / "repositorios.csv"
    csv_completo().to_csv(csv, index=False)
    saida = tmp_path / "saida"
    assert main(["--csv", str(csv), "--saida", str(saida)]) == 0
    for nome in ("descritiva.csv", "faixas_por_metrica.csv", "categorias_c1.csv"):
        assert (saida / nome).is_file()
    pngs = sorted(p.name for p in saida.glob("*.png"))
    assert "hist_frequencia_semana.png" in pngs
    assert "faixas_por_metrica.png" in pngs
    assert "categorias_c1.png" in pngs


def test_main_sem_cfr_b_ignora_a_metrica(tmp_path):
    csv = tmp_path / "repositorios.csv"
    csv_completo().to_csv(csv, index=False)
    saida = tmp_path / "saida"
    main(["--csv", str(csv), "--saida", str(saida)])
    d = pd.read_csv(saida / "descritiva.csv")
    assert "cfr_b" not in set(d["metrica"])
    assert "cfr_a" in set(d["metrica"])


def test_main_com_cfr_b_inclui_a_metrica(tmp_path):
    csv = tmp_path / "repositorios.csv"
    csv_completo(cfr_b=[0.1, 0.5, None, 0.2]).to_csv(csv, index=False)
    saida = tmp_path / "saida"
    main(["--csv", str(csv), "--saida", str(saida)])
    d = pd.read_csv(saida / "descritiva.csv")
    r = linha(d, "cfr_b")
    assert (r["n"], r["n_indefinido"]) == (3, 1)
    assert (saida / "hist_cfr_b.png").is_file()
    f = pd.read_csv(saida / "faixas_por_metrica.csv")
    assert "cfr_b" in set(f["metrica"])


def test_main_csv_ausente_devolve_erro(tmp_path, capsys):
    assert main(["--csv", str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path)]) == 1
    assert "nao_existe.csv" in capsys.readouterr().err


def test_main_coluna_obrigatoria_ausente_devolve_erro(tmp_path, capsys):
    csv = tmp_path / "repositorios.csv"
    csv_completo().drop(columns=["cfr_a"]).to_csv(csv, index=False)
    assert main(["--csv", str(csv), "--saida", str(tmp_path / "s")]) == 1
    assert "cfr_a" in capsys.readouterr().err


def test_main_e_reexecutavel(tmp_path):
    csv = tmp_path / "repositorios.csv"
    csv_completo().to_csv(csv, index=False)
    saida = tmp_path / "saida"
    main(["--csv", str(csv), "--saida", str(saida)])
    primeira = (saida / "descritiva.csv").read_text(encoding="utf-8")
    main(["--csv", str(csv), "--saida", str(saida)])
    assert (saida / "descritiva.csv").read_text(encoding="utf-8") == primeira
    assert os.path.isdir(saida)
