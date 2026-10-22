import csv
from pathlib import Path

import pytest
from scipy import stats

from analise import rq08_rework as rq08
from analise.rq05_spearman import ErroDeAnalise

CABECALHO = ["full_name", "rework_rate", "cfr_b"]
CABECALHO_HEURISTICA = ["versao", "regra", "n", "vp", "fp", "fn", "precisao", "recall", "f1"]
HEURISTICA = [
    [1, "v1", 300, 71, 198, 2, 0.26, 0.97, 0.41],
    [3, "v3", 300, 48, 28, 25, 0.63, 0.66, 0.64],
]
VERSOES_DO_REPOSITORIO = Path(__file__).parent.parent / "dados" / "rotulagem" / "versoes_heuristica.csv"


def gravar(caminho, linhas, cabecalho=CABECALHO):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return str(caminho)


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def dataset(n=40):
    """rework_rate = cfr_b + i/200 (maior, menos em 4 empates); um rework e dois cfr_b vazios."""
    linhas = []
    for i in range(n):
        cfr_b = round(i / (2 * n), 4)
        rework = cfr_b if i % 10 == 0 else round(cfr_b + i / 200, 4)
        linhas.append([f"o/r{i}", "" if i == 5 else rework, "" if i in (7, 8) else cfr_b])
    return linhas


def executar(tmp_path, linhas=None, heuristica=HEURISTICA):
    csv_repos = gravar(tmp_path / "r.csv", dataset() if linhas is None else linhas)
    csv_heuristica = gravar(tmp_path / "h.csv", heuristica, cabecalho=CABECALHO_HEURISTICA)
    saida = tmp_path / "saida"
    codigo = rq08.main(["--csv", csv_repos, "--heuristica", csv_heuristica, "--saida", str(saida)])
    return codigo, saida


# distribuição


def test_distribuicao_calculada_a_mao():
    # ordenados [0; 0,1; 0,2; 0,4; 0,8]: posição do Q1 = 1 e do Q3 = 3 (interpolação linear)
    resultado = rq08.distribuicao([0.4, 0.0, 0.8, 0.1, 0.2])

    assert resultado["mediana"] == pytest.approx(0.2)
    assert (resultado["q1"], resultado["q3"]) == (pytest.approx(0.1), pytest.approx(0.4))
    assert resultado["iqr"] == pytest.approx(0.3)
    assert (resultado["minimo"], resultado["maximo"]) == (0.0, 0.8)
    assert (resultado["n"], resultado["n_indefinido"], resultado["n_zero"]) == (5, 0, 1)


def test_quartis_interpolam_entre_posicoes():
    # [1, 2, 3, 4]: Q1 na posição 0,75 = 1,75; mediana 2,5; Q3 na posição 2,25 = 3,25
    resultado = rq08.distribuicao([4.0, 1.0, 3.0, 2.0])

    assert (resultado["q1"], resultado["mediana"], resultado["q3"]) == (1.75, 2.5, 3.25)


def test_repositorio_sem_release_avaliavel_fica_fora_e_nao_vira_zero():
    resultado = rq08.distribuicao([None, 0.5, None, 0.7, 0.9])

    assert (resultado["n"], resultado["n_indefinido"], resultado["n_zero"]) == (3, 2, 0)
    assert resultado["mediana"] == pytest.approx(0.7) and resultado["minimo"] == 0.5


def test_serie_toda_vazia_deixa_a_distribuicao_indefinida():
    resultado = rq08.distribuicao([None, None])

    assert (resultado["n"], resultado["n_indefinido"]) == (0, 2)
    assert all(resultado[c] is None for c in ("mediana", "q1", "q3", "iqr", "minimo", "maximo"))


# comparação pareada


def test_wilcoxon_calculado_a_mao():
    # diferenças [0,1; 0,2; −0,3; 0,4; 0]: o empate sai; postos de |d| = [1, 2, 3, 4]
    # W+ = 1 + 2 + 4 = 7, W− = 3, rank-biserial = (7 − 3) ÷ 10 = 0,4
    resultado = rq08.comparacao_pareada([0.6, 0.7, 0.2, 0.9, 0.5], [0.5, 0.5, 0.5, 0.5, 0.5])

    assert (resultado["n_maior"], resultado["n_menor"], resultado["n_empates"]) == (3, 1, 1)
    assert resultado["w_mais"] == 7.0
    assert resultado["rank_biserial"] == pytest.approx(0.4) and resultado["interpretacao_rank_biserial"] == "moderada"
    esperado = stats.wilcoxon([0.1, 0.2, -0.3, 0.4], alternative="greater").pvalue
    assert resultado["p_valor_wilcoxon"] == pytest.approx(esperado)


def test_todos_os_pares_maiores_dao_rank_biserial_1_e_p_pequeno():
    x = [0.1 * i + 0.05 for i in range(10)]
    y = [0.1 * i for i in range(10)]

    resultado = rq08.comparacao_pareada(x, y)

    assert resultado["rank_biserial"] == pytest.approx(1.0) and resultado["p_valor_wilcoxon"] < 0.01
    assert resultado["n_menor"] == 0


def test_todos_os_pares_empatados_deixam_o_teste_indefinido():
    resultado = rq08.comparacao_pareada([0.2, 0.3, 0.4, 0.5], [0.2, 0.3, 0.4, 0.5])

    assert resultado["n_empates"] == 4
    assert resultado["p_valor_wilcoxon"] is None and resultado["rank_biserial"] is None
    assert resultado["interpretacao_rank_biserial"] == "indefinido"


def test_menos_de_3_pares_nao_empatados_deixam_o_teste_indefinido():
    resultado = rq08.comparacao_pareada([0.5, 0.6, 0.3], [0.4, 0.5, 0.3])

    assert resultado["n_maior"] == 2 and resultado["p_valor_wilcoxon"] is None


def test_par_com_lado_vazio_fica_fora_da_comparacao():
    resultado = rq08.comparacao_pareada([0.5, None, 0.7, 0.9], [0.1, 0.2, None, 0.3])

    assert (resultado["n_maior"], resultado["n_menor"], resultado["n_empates"]) == (2, 0, 0)


# execução completa


def test_main_grava_a_tabela_e_os_dois_graficos(tmp_path, capsys):
    codigo, saida = executar(tmp_path)

    assert codigo == 0
    linhas = ler(saida / "rq08.csv")
    assert list(linhas[0]) == list(rq08.COLUNAS_RQ08)
    rework, cfr_b = linhas
    assert (rework["metrica"], cfr_b["metrica"]) == ("rework_rate", "cfr_b")
    assert (rework["n"], rework["n_indefinido"], cfr_b["n"], cfr_b["n_indefinido"]) == ("39", "1", "38", "2")
    assert rework["comparado_com"] == "cfr_b" and rework["n_pares"] == "37" and rework["n_excluidos"] == "3"
    assert float(rework["rho"]) > 0.9 and rework["direcao"] == "positiva"
    assert (rework["n_maior"], rework["n_menor"], rework["n_empates"]) == ("33", "0", "4")
    assert float(rework["p_valor_wilcoxon"]) < 0.001 and float(rework["rank_biserial"]) == pytest.approx(1.0)
    for coluna in rq08.COLUNAS_RQ08[rq08.COLUNAS_RQ08.index("comparado_com") : rq08.COLUNAS_RQ08.index("versao_heuristica")]:
        assert cfr_b[coluna] == ""
    for linha in linhas:
        assert linha["versao_heuristica"] == "3" and float(linha["f1_heuristica"]) == pytest.approx(0.64)
    for nome in ("rq08_hist.png", "rq08_cfr_b.png"):
        assert (saida / nome).stat().st_size > 0
    assert "rework_rate x cfr_b" in capsys.readouterr().out


def test_rodar_de_novo_gera_o_mesmo_csv(tmp_path):
    _, saida = executar(tmp_path)
    primeira = (saida / "rq08.csv").read_text(encoding="utf-8")

    executar(tmp_path)

    assert (saida / "rq08.csv").read_text(encoding="utf-8") == primeira


def test_main_com_serie_vazia_grava_celulas_vazias(tmp_path):
    codigo, saida = executar(tmp_path, linhas=[["o/a", "", "0.1"], ["o/b", "", "0.2"]])

    assert codigo == 0
    rework = ler(saida / "rq08.csv")[0]
    assert rework["n"] == "0" and rework["mediana"] == "" and rework["rho"] == ""
    assert rework["interpretacao_rho"] == "indefinido" and rework["p_valor_wilcoxon"] == ""


# erros


def test_coluna_ausente_encerra_com_erro(tmp_path, capsys):
    csv_repos = gravar(tmp_path / "r.csv", [["o/a", 0.1]], cabecalho=["full_name", "cfr_b"])

    assert rq08.main(["--csv", csv_repos, "--saida", str(tmp_path)]) == 1
    assert "rework_rate" in capsys.readouterr().err


def test_arquivo_ausente_encerra_com_erro(tmp_path, capsys):
    assert rq08.main(["--csv", str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path)]) == 1
    assert "nao_existe.csv" in capsys.readouterr().err


def test_numero_invalido_cita_a_linha_e_a_coluna(tmp_path):
    linhas = dataset(n=6)
    linhas[3][1] = "abc"
    csv_repos = gravar(tmp_path / "r.csv", linhas)

    with pytest.raises(ErroDeAnalise, match="linha 5.*rework_rate"):
        rq08.ler_repositorios(csv_repos)


def test_versao_da_heuristica_ausente_encerra_com_erro(tmp_path, capsys):
    codigo, _ = executar(tmp_path, heuristica=HEURISTICA[:1])

    assert codigo == 1
    assert "versão 3" in capsys.readouterr().err


def test_ler_heuristica_devolve_precisao_recall_e_f1(tmp_path):
    caminho = gravar(tmp_path / "h.csv", HEURISTICA, cabecalho=CABECALHO_HEURISTICA)

    assert rq08.ler_heuristica(caminho, 3) == {"precisao": 0.63, "recall": 0.66, "f1": 0.64}


def test_heuristica_padrao_do_repositorio_tem_a_versao_usada():
    assert rq08.ler_heuristica(str(VERSOES_DO_REPOSITORIO), rq08.VERSAO_HEURISTICA)["f1"] < 0.70
