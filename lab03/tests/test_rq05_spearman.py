import csv
import random

import pytest

from analise import rq05_spearman as rq05
from analise.rq05_spearman import ErroDeAnalise

CABECALHO = ["full_name", "frequencia_semana", "cfr_a", "cfr_b"]


def gravar(caminho, linhas, cabecalho=CABECALHO):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return str(caminho)


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def dataset(n=60, semente=1):
    """cfr_a independente da frequência; cfr_b decresce com ela; 3 valores de cfr_b ausentes."""
    sorteio = random.Random(semente)
    linhas = []
    for i in range(n):
        frequencia = 0.1 + i * 0.5
        cfr_b = "" if i in (3, 10, 20) else round(1 / (1 + frequencia) + sorteio.random() * 0.05, 4)
        linhas.append([f"o/r{i}", frequencia, round(sorteio.random(), 4), cfr_b])
    return linhas


# correlação


def test_relacao_monotona_crescente_tem_rho_1():
    resultado = rq05.correlacao([1, 2, 3, 4, 5], [0.1, 0.2, 0.3, 0.4, 0.5])

    assert resultado["rho"] == pytest.approx(1.0) and resultado["p_valor"] < 0.05
    assert resultado["direcao"] == "positiva" and resultado["interpretacao"] == "forte"


def test_relacao_monotona_decrescente_tem_rho_menos_1():
    resultado = rq05.correlacao([1, 2, 3, 4, 5], [0.5, 0.4, 0.3, 0.2, 0.1])

    assert resultado["rho"] == pytest.approx(-1.0) and resultado["direcao"] == "negativa"


def test_exemplo_calculado_a_mao():
    # postos iguais, d = [0, 1, -1, 0]: rho = 1 - 6 * 2 / (4 * 15) = 0,8
    assert rq05.correlacao([1, 2, 3, 4], [1, 3, 2, 4])["rho"] == pytest.approx(0.8)


def test_empates_usam_postos_medios():
    # postos de y: [2, 2, 2, 4, 5, 6]; correlação de Pearson dos postos = 15,5 / raiz(17,5 * 15,5)
    resultado = rq05.correlacao([1, 2, 3, 4, 5, 6], [0, 0, 0, 1, 2, 3])

    assert resultado["rho"] == pytest.approx(15.5 / (17.5 * 15.5) ** 0.5)
    assert resultado["n_y_zero"] == 3


def test_pares_com_valor_ausente_ficam_fora_e_sao_contados():
    x = [1, 2, None, 4, 5, 6]
    y = [0.1, None, 0.3, 0.4, 0.5, 0.6]

    resultado = rq05.correlacao(x, y)

    assert (resultado["n"], resultado["n_excluidos"]) == (4, 2)
    assert resultado["rho"] == pytest.approx(1.0)


def test_entrada_constante_deixa_a_correlacao_indefinida():
    resultado = rq05.correlacao([1, 2, 3, 4], [0.2, 0.2, 0.2, 0.2])

    assert resultado["rho"] is None and resultado["p_valor"] is None
    assert resultado["interpretacao"] == "indefinido" and resultado["direcao"] == ""


def test_menos_de_3_pares_deixa_a_correlacao_indefinida():
    resultado = rq05.correlacao([1, 2], [3, 4])

    assert resultado["n"] == 2 and resultado["rho"] is None


@pytest.mark.parametrize(
    "rho, esperado",
    [(0.0, "desprezível"), (-0.09, "desprezível"), (0.1, "fraca"), (-0.29, "fraca"), (0.3, "moderada"), (0.49, "moderada"), (-0.5, "forte"), (1.0, "forte")],
)
def test_interpretacao_da_magnitude_segue_cohen(rho, esperado):
    assert rq05.interpretar(rho) == esperado


# execução completa


def test_main_grava_a_tabela_e_os_dois_graficos(tmp_path, capsys):
    csv_repos = gravar(tmp_path / "r.csv", dataset())
    saida = tmp_path / "saida"

    assert rq05.main(["--csv", csv_repos, "--saida", str(saida)]) == 0

    linhas = {l["variante"]: l for l in ler(saida / "rq05.csv")}
    assert set(linhas) == {"cfr_a", "cfr_b"}
    assert linhas["cfr_a"]["n"] == "60" and linhas["cfr_b"]["n"] == "57" and linhas["cfr_b"]["n_excluidos"] == "3"
    assert float(linhas["cfr_b"]["rho"]) < -0.9 and linhas["cfr_b"]["direcao"] == "negativa"
    assert abs(float(linhas["cfr_a"]["rho"])) < 0.35
    for nome in ("rq05_cfr_a.png", "rq05_cfr_b.png"):
        assert (saida / nome).stat().st_size > 0
    assert "cfr_b" in capsys.readouterr().out


def test_figura_aceita_frequencia_zero_sem_quebrar(tmp_path):
    caminho = tmp_path / "f.png"

    rq05.figura([0.0, 1.0, 2.0, 4.0], [0.1, 0.2, 0.3, 0.4], "cfr_a", rq05.correlacao([0.0, 1.0, 2.0, 4.0], [0.1, 0.2, 0.3, 0.4]), str(caminho))

    assert caminho.stat().st_size > 0


def test_rodar_de_novo_gera_o_mesmo_csv(tmp_path):
    csv_repos = gravar(tmp_path / "r.csv", dataset())
    saida = tmp_path / "saida"
    rq05.main(["--csv", csv_repos, "--saida", str(saida)])
    primeira = (saida / "rq05.csv").read_text(encoding="utf-8")

    rq05.main(["--csv", csv_repos, "--saida", str(saida)])

    assert (saida / "rq05.csv").read_text(encoding="utf-8") == primeira


# erros


def test_coluna_ausente_encerra_com_erro(tmp_path, capsys):
    csv_repos = gravar(tmp_path / "r.csv", [["o/a", 1.0]], cabecalho=["full_name", "frequencia_semana"])

    assert rq05.main(["--csv", csv_repos, "--saida", str(tmp_path)]) == 1
    assert "cfr_a" in capsys.readouterr().err


def test_arquivo_ausente_encerra_com_erro(tmp_path, capsys):
    assert rq05.main(["--csv", str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path)]) == 1
    assert "nao_existe.csv" in capsys.readouterr().err


def test_numero_invalido_cita_a_linha_e_a_coluna(tmp_path):
    linhas = dataset(n=6)
    linhas[3][2] = "abc"
    csv_repos = gravar(tmp_path / "r.csv", linhas)

    with pytest.raises(ErroDeAnalise, match="linha 5.*cfr_a"):
        rq05.ler_repositorios(csv_repos)


def test_ler_repositorios_troca_vazio_por_none(tmp_path):
    csv_repos = gravar(tmp_path / "r.csv", dataset(n=5))

    linhas = rq05.ler_repositorios(csv_repos)

    assert linhas["cfr_b"][3] is None and linhas["cfr_b"][0] is not None
    assert len(linhas["frequencia_semana"]) == 5
