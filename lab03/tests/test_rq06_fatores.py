import csv
import random

import pytest

from analise import rq06_fatores as rq06
from analise.rq06_fatores import ErroDeAnalise

CABECALHO = [
    "full_name", "estrelas", "linguagem", "contribuidores", "idade_dias",
    "frequencia_semana", "lead_time_a_h", "lead_time_b_h", "cfr_a", "cfr_b", "recuperacao_mediana_h",
]  # fmt: skip
CABECALHO_CONSENSO = ["dimensao", "full_name", "tag_name", "consenso"]
TIPOS = ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI"]


def gravar(caminho, cabecalho, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=cabecalho, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)
    return str(caminho)


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def dados_sinteticos(n=120, semente=0):
    """Frequência depende fortemente da linguagem; as demais métricas são ruído independente."""
    sorteio = random.Random(semente)
    media = {"Python": 1.0, "Go": 5.0, "Rust": 10.0}
    linhas = []
    for i in range(n):
        linguagem = ["Python", "Go", "Rust"][i % 3]
        linhas.append(
            {
                "full_name": f"o/r{i}",
                "estrelas": 1000 + i * 10,
                "linguagem": linguagem,
                "contribuidores": sorteio.randint(1, 500),
                "idade_dias": sorteio.randint(100, 3000),
                "frequencia_semana": media[linguagem] + sorteio.random(),
                "lead_time_a_h": sorteio.random() * 100,
                "lead_time_b_h": sorteio.random() * 100,
                "cfr_a": sorteio.random(),
                "cfr_b": sorteio.random(),
                "recuperacao_mediana_h": sorteio.random() * 50,
            }
        )
    return linhas


@pytest.fixture
def entrada(tmp_path):
    linhas = dados_sinteticos()
    repos = gravar(tmp_path / "repositorios.csv", CABECALHO, linhas)
    consenso = [
        {"dimensao": "tipo_projeto", "full_name": f"o/r{i}", "tag_name": "", "consenso": TIPOS[i % 3]}
        for i in range(60)
    ] + [{"dimensao": "corretiva", "full_name": "o/r0", "tag_name": "v1", "consenso": "sim"}]
    return repos, gravar(tmp_path / "consenso.csv", CABECALHO_CONSENSO, consenso)


# estatística


def test_holm_confere_com_o_calculo_a_mao():
    # ordenados: 0,01 x 3 = 0,03; 0,03 x 2 = 0,06; 0,04 x 1 = 0,04 -> monotonia sobe para 0,06
    assert rq06.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_holm_nunca_diminui_o_p_e_limita_a_1():
    ps = [0.5, 0.9, 0.001, 0.2]

    corrigidos = rq06.holm(ps)

    assert all(c >= p for c, p in zip(corrigidos, ps)) and max(corrigidos) <= 1.0


def test_holm_sem_testes_devolve_lista_vazia():
    assert rq06.holm([]) == []


def test_delta_de_cliff_nos_extremos_e_no_empate():
    assert rq06.delta_de_cliff([1, 2, 3], [4, 5, 6])[0] == -1.0
    assert rq06.delta_de_cliff([4, 5, 6], [1, 2, 3])[0] == 1.0
    assert rq06.delta_de_cliff([1, 2, 3], [1, 2, 3])[0] == pytest.approx(0.0)


def test_delta_de_cliff_usa_a_formula_do_enunciado():
    # U1 = 2 (x vence y em 2 dos 6 pares: 3 > 2 e 5 > 2): delta = 2 * 2 / (3 * 2) - 1 = -1/3
    delta, u1 = rq06.delta_de_cliff([1, 3, 5], [2, 6])

    assert u1 == 2.0 and delta == pytest.approx(-1 / 3)


def test_epsilon_ao_quadrado_e_h_sobre_n_menos_1():
    grupos = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15]]

    resultado = rq06.testar(grupos)

    assert resultado["teste"] == "kruskal"
    assert resultado["tamanho_efeito"] == pytest.approx(resultado["estatistica"] / (15 - 1))
    assert resultado["tipo_efeito"] == "epsilon2" and resultado["interpretacao_efeito"] == "grande"


def test_dois_grupos_usam_mann_whitney_e_delta_de_cliff():
    resultado = rq06.testar([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])

    assert resultado["teste"] == "mannwhitney" and resultado["tipo_efeito"] == "cliff_delta"
    assert resultado["tamanho_efeito"] == -1.0 and resultado["interpretacao_efeito"] == "grande"


@pytest.mark.parametrize(
    "delta, esperado",
    [(0.0, "desprezível"), (0.146, "desprezível"), (-0.2, "pequeno"), (0.4, "médio"), (-0.474, "grande"), (1.0, "grande")],
)
def test_interpretacao_do_delta_de_cliff_segue_romano(delta, esperado):
    assert rq06.interpretar_delta(delta) == esperado


@pytest.mark.parametrize("eps, esperado", [(0.0, "desprezível"), (0.05, "pequeno"), (0.1, "médio"), (0.3, "grande")])
def test_interpretacao_de_epsilon_ao_quadrado(eps, esperado):
    assert rq06.interpretar_epsilon(eps) == esperado


# fatores


def test_quartis_dividem_em_quatro_grupos_ordenados():
    rotulos = rq06.quartis([1, 2, 3, 4, 5, 6, 7, 8])

    assert rotulos == ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4"]


def test_quartis_com_valores_repetidos_geram_menos_grupos_sem_quebrar():
    rotulos = rq06.quartis([1] * 6 + [2, 3])

    assert set(rotulos) < {"Q1", "Q2", "Q3", "Q4"} and len(set(rotulos)) < 4


def test_quartis_deixam_o_valor_ausente_sem_grupo():
    assert rq06.quartis([1, None, 3, 4, 5, 6, 7, 8])[1] is None


def test_linguagens_raras_e_vazias_viram_outras():
    linguagens = ["Python"] * 20 + ["Go"] * 16 + ["Zig"] * 3 + [""]

    rotulos = rq06.agrupar_linguagens(linguagens, minimo=15)

    assert set(rotulos) == {"Python", "Go", "outras"}
    assert rotulos[-1] == "outras" and rotulos[-2] == "outras" and rotulos[0] == "Python"


def test_tipo_de_projeto_vem_do_consenso_e_so_existe_na_amostra_ouro(entrada):
    linhas = rq06.ler_repositorios(entrada[0])

    tipos = rq06.tipos_de_projeto(linhas, entrada[1])

    assert tipos[0] == "biblioteca/framework" and tipos[1] == "aplicação/serviço"
    assert sum(t is not None for t in tipos) == 60 and tipos[100] is None


def test_agrupar_exclui_grupo_pequeno_e_metrica_ausente():
    rotulos = ["A"] * 6 + ["B"] * 6 + ["C"] * 2
    valores = [1.0, 2.0, 3.0, 4.0, 5.0, None, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]

    grupos, excluidos = rq06.agrupar(valores, rotulos, minimo=5)

    assert list(grupos) == ["A", "B"] and len(grupos["A"]) == 5 and len(grupos["B"]) == 6
    assert excluidos == {"C": 2}


# execução completa


def test_efeito_forte_da_linguagem_na_frequencia_e_significativo_apos_holm(entrada, tmp_path):
    saida = tmp_path / "saida"

    assert rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)]) == 0

    linhas = {(l["fator"], l["metrica"]): l for l in ler(saida / "rq06.csv")}
    forte = linhas[("linguagem", "frequencia_semana")]
    assert forte["status"] == "ok" and forte["significativo_holm"] == "True"
    assert float(forte["p_holm"]) < 0.001 and float(forte["tamanho_efeito"]) > 0.8
    assert linhas[("linguagem", "cfr_a")]["significativo_holm"] == "False"  # ruído


def test_uma_linha_por_fator_e_metrica_com_os_quatro_da_issue(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    linhas = ler(saida / "rq06.csv")

    assert {l["fator"] for l in linhas} == {"linguagem", "estrelas", "contribuidores", "idade", "tipo_projeto"}
    assert {l["metrica"] for l in linhas} == {"frequencia_semana", "lead_time_a_h", "cfr_a", "recuperacao_mediana_h"}
    assert len(linhas) == 20


def test_variantes_b_acrescentam_duas_metricas(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida), "--variantes-b"])

    linhas = ler(saida / "rq06.csv")

    assert len(linhas) == 30 and {"lead_time_b_h", "cfr_b"} <= {l["metrica"] for l in linhas}


def test_holm_corrige_sobre_todos_os_testes_executados_juntos(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    executados = [l for l in ler(saida / "rq06.csv") if l["status"] == "ok"]

    brutos = [float(l["p_bruto"]) for l in executados]
    assert [float(l["p_holm"]) for l in executados] == pytest.approx(rq06.holm(brutos))
    assert all(float(l["p_holm"]) >= float(l["p_bruto"]) for l in executados)


def test_tipo_de_projeto_testa_so_os_60_da_amostra_ouro(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    linha = next(l for l in ler(saida / "rq06.csv") if l["fator"] == "tipo_projeto" and l["metrica"] == "cfr_a")

    assert linha["n"] == "60" and linha["n_grupos"] == "3"


def test_fator_sem_grupos_suficientes_fica_sem_teste_e_fora_do_holm(tmp_path):
    linhas = dados_sinteticos(n=30)
    repos = gravar(tmp_path / "repositorios.csv", CABECALHO, linhas)
    consenso = gravar(
        tmp_path / "consenso.csv", CABECALHO_CONSENSO,
        [{"dimensao": "tipo_projeto", "full_name": "o/r0", "tag_name": "", "consenso": "outro"}],
    )  # fmt: skip

    assert rq06.main(["--csv", repos, "--consenso", consenso, "--saida", str(tmp_path / "s")]) == 0

    tipo = [l for l in ler(tmp_path / "s" / "rq06.csv") if l["fator"] == "tipo_projeto"]
    assert tipo and all(l["status"] == "sem grupos suficientes" and l["p_holm"] == "" for l in tipo)


def test_tabela_de_grupos_traz_n_mediana_e_quartis(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    grupos = [l for l in ler(saida / "rq06_grupos.csv") if l["fator"] == "linguagem" and l["metrica"] == "frequencia_semana"]

    assert {g["grupo"] for g in grupos} == {"Python", "Go", "Rust"}
    rust = next(g for g in grupos if g["grupo"] == "Rust")
    assert rust["n"] == "40" and 10 <= float(rust["mediana"]) <= 11
    assert float(rust["q1"]) <= float(rust["mediana"]) <= float(rust["q3"])


def test_quartis_registram_a_faixa_de_valores_de_cada_grupo(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    q1 = next(l for l in ler(saida / "rq06_grupos.csv") if l["fator"] == "estrelas" and l["grupo"] == "Q1")

    assert q1["faixa"].startswith("1000") and "-" in q1["faixa"]


def test_rodar_de_novo_gera_as_mesmas_saidas(entrada, tmp_path):
    saida = tmp_path / "saida"
    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])
    primeira = (saida / "rq06.csv").read_text(encoding="utf-8")

    rq06.main(["--csv", entrada[0], "--consenso", entrada[1], "--saida", str(saida)])

    assert (saida / "rq06.csv").read_text(encoding="utf-8") == primeira


# erros


def test_coluna_ausente_encerra_com_erro(tmp_path, capsys):
    repos = gravar(tmp_path / "r.csv", ["full_name", "estrelas"], [{"full_name": "o/a", "estrelas": 1}])
    consenso = gravar(tmp_path / "c.csv", CABECALHO_CONSENSO, [])

    assert rq06.main(["--csv", repos, "--consenso", consenso, "--saida", str(tmp_path)]) == 1
    assert "linguagem" in capsys.readouterr().err


def test_arquivo_ausente_encerra_com_erro(tmp_path, capsys):
    assert rq06.main(["--csv", str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path)]) == 1
    assert "nao_existe.csv" in capsys.readouterr().err


def test_valor_numerico_invalido_cita_a_linha(tmp_path):
    linhas = dados_sinteticos(n=6)
    linhas[3]["cfr_a"] = "abc"
    repos = gravar(tmp_path / "r.csv", CABECALHO, linhas)

    with pytest.raises(ErroDeAnalise, match="linha 5.*cfr_a"):
        rq06.ler_repositorios(repos)
