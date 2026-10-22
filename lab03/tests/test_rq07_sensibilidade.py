import csv

import pytest

from analise import rq07_sensibilidade as rq07
from analise.rq07_sensibilidade import ErroDeAnalise

CABECALHO = ["full_name", "categoria_c1", "categoria_c2", "categoria_c3"]


def gravar_csv(caminho, linhas, cabecalho=CABECALHO):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return str(caminho)


def ler_csv(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


@pytest.fixture
def repositorios(tmp_path):
    return gravar_csv(
        tmp_path / "repositorios.csv",
        [
            ["o/a", "Elite", "Elite", "High"],
            ["o/b", "High", "High", "High"],
            ["o/c", "High", "Medium", "Low"],
            ["o/d", "Medium", "Medium", "Medium"],
            ["o/e", "Low", "Low", ""],  # C3 indefinida
            ["o/f", "Medium", "", ""],  # C2 e C3 indefinidas
        ],
    )


# leitura


def test_ler_categorias_troca_vazio_por_none(repositorios):
    categorias = rq07.ler_categorias(repositorios)

    assert categorias["c1"] == ["Elite", "High", "High", "Medium", "Low", "Medium"]
    assert categorias["c2"][-1] is None and categorias["c3"][-2:] == [None, None]


def test_ler_categorias_sem_as_colunas_de_c2_e_c3_orienta_a_coleta(tmp_path):
    caminho = gravar_csv(tmp_path / "r.csv", [["o/a", "High"]], cabecalho=["full_name", "categoria_c1"])

    with pytest.raises(ErroDeAnalise, match="categoria_c2.*S03-07"):
        rq07.ler_categorias(caminho)


def test_ler_categorias_com_valor_invalido_cita_a_linha(tmp_path):
    caminho = gravar_csv(tmp_path / "r.csv", [["o/a", "Elite", "Elite", "Elite"], ["o/b", "Alta", "High", "High"]])

    with pytest.raises(ErroDeAnalise, match="linha 3.*Alta"):
        rq07.ler_categorias(caminho)


def test_ler_categorias_com_arquivo_ausente(tmp_path):
    with pytest.raises(ErroDeAnalise, match="repositorios.csv"):
        rq07.ler_categorias(str(tmp_path / "repositorios.csv"))


# comparação de um par


def test_exemplo_calculado_a_mao_percentual_e_kappa_ponderado():
    # Low=1 e Medium=2 entre 4 níveis: discordância observada 1/12, esperada 1/6, kappa = 0,5
    x = ["Low", "Low", "Medium", "Medium"]
    y = ["Low", "Medium", "Medium", "Medium"]

    linha = rq07.comparar_par("c1", "c2", x, y)

    assert linha["n"] == 4 and linha["n_excluidos"] == 0
    assert linha["n_mudaram"] == 1 and linha["pct_mudanca"] == 25.0
    assert linha["kappa_linear"] == pytest.approx(0.5)
    assert linha["interpretacao"] == "moderada"


def test_classificacoes_identicas_tem_kappa_1_e_mudanca_zero():
    x = ["Elite", "High", "Medium", "Low"]

    linha = rq07.comparar_par("c1", "c3", x, list(x))

    assert (linha["pct_mudanca"], linha["kappa_linear"], linha["interpretacao"]) == (0.0, 1.0, "quase perfeita")


def test_pares_com_categoria_indefinida_ficam_fora_e_sao_contados():
    x = ["High", "High", None, "Low"]
    y = ["High", None, "High", "Medium"]

    linha = rq07.comparar_par("c1", "c2", x, y)

    assert (linha["n"], linha["n_excluidos"]) == (2, 2)
    assert linha["n_mudaram"] == 1 and linha["pct_mudanca"] == 50.0


def test_direcao_da_mudanca_e_vizinhanca():
    # c1 -> c2: High->Elite (melhora, vizinha), Low->High (melhora, não vizinha),
    # Medium->Low (piora, vizinha), High->High (igual)
    x = ["High", "Low", "Medium", "High"]
    y = ["Elite", "High", "Low", "High"]

    linha = rq07.comparar_par("c1", "c2", x, y)

    assert (linha["n_melhor"], linha["n_pior"], linha["n_vizinha"]) == (2, 1, 2)
    assert linha["n_mudaram"] == 3


def test_uma_so_categoria_deixa_o_kappa_indefinido():
    linha = rq07.comparar_par("c1", "c2", ["High"] * 3, ["High"] * 3)

    assert linha["pct_mudanca"] == 0.0
    assert linha["kappa_linear"] is None and linha["interpretacao"] == "indefinido"


def test_par_sem_nenhum_repositorio_comparavel_fica_vazio():
    linha = rq07.comparar_par("c2", "c3", [None, "High"], ["High", None])

    assert linha["n"] == 0 and linha["n_excluidos"] == 2
    assert linha["pct_mudanca"] is None and linha["kappa_linear"] is None


# matriz e distribuição


def test_matriz_de_transicao_conta_de_x_para_y_na_ordem_das_categorias():
    x = ["High", "High", "Low", None]
    y = ["Elite", "High", "Low", "High"]

    matriz = rq07.matriz_de_transicao(x, y)

    assert matriz["Elite"]["High"] == 0
    assert matriz["High"] == {"Elite": 1, "High": 1, "Medium": 0, "Low": 0}  # de High para...
    assert matriz["Low"]["Low"] == 1
    assert sum(sum(linha.values()) for linha in matriz.values()) == 3  # o par com None fica fora


def test_distribuicao_por_categoria(repositorios):
    categorias = rq07.ler_categorias(repositorios)

    assert rq07.distribuicao(categorias["c1"]) == {"Elite": 1, "High": 2, "Medium": 2, "Low": 1}
    assert rq07.distribuicao(categorias["c3"]) == {"Elite": 0, "High": 2, "Medium": 1, "Low": 1}


# execução completa


def test_main_grava_as_tabelas_e_a_figura(repositorios, tmp_path, capsys):
    saida = tmp_path / "saida"

    codigo = rq07.main(["--csv", repositorios, "--saida", str(saida)])

    assert codigo == 0
    pares = {(l["combinacao_x"], l["combinacao_y"]): l for l in ler_csv(saida / "rq07.csv")}
    assert set(pares) == {("c1", "c2"), ("c1", "c3"), ("c2", "c3")}
    assert pares[("c1", "c2")]["n"] == "5" and pares[("c1", "c2")]["n_excluidos"] == "1"
    assert pares[("c1", "c3")]["n"] == "4"
    assert pares[("c2", "c3")]["n"] == "4"
    assert len(ler_csv(saida / "rq07_matrizes.csv")) == 3 * 16
    assert len(ler_csv(saida / "rq07_categorias.csv")) == 3 * 4
    assert (saida / "rq07_matrizes.png").stat().st_size > 0
    assert "c1 x c2" in capsys.readouterr().out


def test_main_sem_nenhum_repositorio_com_c2_e_c3_encerra_com_erro(tmp_path, capsys):
    caminho = gravar_csv(tmp_path / "r.csv", [["o/a", "High", "", ""], ["o/b", "Low", "", ""]])

    assert rq07.main(["--csv", caminho, "--saida", str(tmp_path / "saida")]) == 1
    assert "C2" in capsys.readouterr().err
    assert not (tmp_path / "saida" / "rq07.csv").exists()


def test_main_com_arquivo_ausente_encerra_com_erro(tmp_path, capsys):
    assert rq07.main(["--csv", str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path)]) == 1
    assert "nao_existe.csv" in capsys.readouterr().err


def test_rodar_de_novo_gera_as_mesmas_saidas(repositorios, tmp_path):
    saida = tmp_path / "saida"
    rq07.main(["--csv", repositorios, "--saida", str(saida)])
    primeira = (saida / "rq07.csv").read_text(encoding="utf-8")

    rq07.main(["--csv", repositorios, "--saida", str(saida)])

    assert (saida / "rq07.csv").read_text(encoding="utf-8") == primeira


# métricas sozinhas

COLUNAS_DAS_METRICAS = sorted({c for por_combinacao in rq07.METRICAS.values() for c in por_combinacao.values()})


def valores_das_metricas(**preenchidos):
    """Três repositórios, com as colunas das métricas em branco, exceto as de `preenchidos`."""
    valores = {coluna: [None, None, None] for coluna in COLUNAS_DAS_METRICAS}
    valores.update(preenchidos)
    return valores


def test_comparar_metrica_conta_as_notas_que_mudam_e_a_direcao():
    # CFR: 0,10 e 0,50 são Elite e Low (notas 4 e 1); 0,20 e 0,20 são High nas duas
    valores = valores_das_metricas(cfr_a=[0.10, 0.50, 0.20], cfr_b_c2=[0.50, 0.10, 0.20])

    linha = rq07.comparar_metrica("cfr", "c1", "c2", valores)

    assert (linha["n"], linha["n_mudaram"], linha["n_melhor"], linha["n_pior"]) == (3, 2, 1, 1)
    assert linha["pct_mudanca"] == pytest.approx(200 / 3)


def test_comparar_metrica_ignora_o_repositorio_sem_valor_em_um_dos_lados():
    valores = valores_das_metricas(lead_time_a_h=[10, 100, None], lead_time_b_h_c2=[100, 1000, 10])

    linha = rq07.comparar_metrica("lead_time", "c1", "c2", valores)

    # só os dois primeiros entram: Elite->High e High->Medium (cada um desce uma nota)
    assert (linha["n"], linha["n_mudaram"], linha["n_pior"], linha["pct_mudanca"]) == (2, 2, 2, 100.0)
    assert linha["mediana_x"] == 55.0  # mediana dos valores definidos de C1, e não só dos pares
    assert linha["mediana_y"] == 100.0


def test_comparar_metrica_sem_nenhum_par_fica_vazia():
    linha = rq07.comparar_metrica("frequencia", "c1", "c2", valores_das_metricas())

    assert linha["n"] == 0 and linha["pct_mudanca"] is None and linha["mediana_x"] is None


def test_cfr_de_c1_e_c3_e_o_mesmo_e_nunca_muda():
    valores = valores_das_metricas(cfr_a=[0.1, 0.5, 0.2])

    assert rq07.comparar_metrica("cfr", "c1", "c3", valores)["pct_mudanca"] == 0.0


def test_ler_valores_sem_as_colunas_das_metricas_devolve_none(repositorios):
    assert rq07.ler_valores(repositorios) is None


def test_main_grava_a_tabela_por_metrica_quando_o_csv_traz_as_colunas(tmp_path):
    cabecalho = CABECALHO + COLUNAS_DAS_METRICAS
    linha = ["o/a", "Elite", "High", "High"] + ["0.1"] * len(COLUNAS_DAS_METRICAS)
    vazia = ["o/b", "High", "High", "High"] + [""] * len(COLUNAS_DAS_METRICAS)
    caminho = gravar_csv(tmp_path / "r.csv", [linha, vazia], cabecalho=cabecalho)
    saida = tmp_path / "saida"

    assert rq07.main(["--csv", caminho, "--saida", str(saida)]) == 0

    metricas = ler_csv(saida / "rq07_metricas.csv")
    assert len(metricas) == len(rq07.METRICAS) * 3
    assert {l["metrica"] for l in metricas} == {"frequencia", "lead_time", "cfr"}


def test_main_sem_as_colunas_das_metricas_nao_gera_a_tabela_por_metrica(repositorios, tmp_path):
    saida = tmp_path / "saida"

    assert rq07.main(["--csv", repositorios, "--saida", str(saida)]) == 0

    assert not (saida / "rq07_metricas.csv").exists()
