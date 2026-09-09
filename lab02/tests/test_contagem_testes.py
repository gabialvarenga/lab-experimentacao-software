from cronometro import Contagem

from contagem_testes import (
    COLUNAS,
    calcular_falhas_e_taxa,
    contar_testes_da_kata,
    extrair_kata_e_tratamento,
    ler_contagem_do_trial,
    montar_linha_contagem,
)


def test_extrair_kata_e_tratamento_kata_simples():
    assert extrair_kata_e_tratamento("k1-com-ia") == ("k1", "com-ia")
    assert extrair_kata_e_tratamento("k1-sem-ia") == ("k1", "sem-ia")


def test_extrair_kata_e_tratamento_kata_com_hifen_no_nome():
    assert extrair_kata_e_tratamento("kata-dois-sem-ia") == ("kata-dois", "sem-ia")


def test_contar_testes_da_kata(tmp_path):
    arq = tmp_path / "test_aceitacao.py"
    arq.write_text(
        "from solucao import f\n\n"
        "def test_um():\n    assert f() == 1\n\n"
        "def test_dois():\n    assert f() == 2\n\n"
        "def test_tres():\n    assert f() == 3\n\n"
        "def test_quatro():\n    assert f() == 4\n",
        encoding="utf-8",
    )
    assert contar_testes_da_kata(arq) == 4


def test_contar_testes_da_kata_arquivo_vazio(tmp_path):
    arq = tmp_path / "test_aceitacao.py"
    arq.write_text("", encoding="utf-8")
    assert contar_testes_da_kata(arq) == 0


def test_calcular_falhas_e_taxa_caso_normal():
    falhando, taxa = calcular_falhas_e_taxa(testes_total_kata=4, passando=3)
    assert falhando == 1
    assert taxa == 75.0


def test_calcular_falhas_e_taxa_zero_passando():
    falhando, taxa = calcular_falhas_e_taxa(testes_total_kata=4, passando=0)
    assert falhando == 4
    assert taxa == 0.0


def test_calcular_falhas_e_taxa_total_zero_nao_divide_por_zero():
    assert calcular_falhas_e_taxa(testes_total_kata=0, passando=0) == (0, 0.0)


def test_montar_linha_contagem_ordem_e_arredondamento():
    linha = montar_linha_contagem(
        integrante="carlos",
        kata="k1",
        tratamento="com-ia",
        testes_total=4,
        testes_passando=3,
        testes_falhando=1,
        taxa_sucesso=75.0001,
    )
    assert list(linha.keys()) == COLUNAS
    assert linha["taxa_sucesso"] == 75.0


def test_ler_contagem_do_trial_report_valido(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuite name="pytest" tests="4" failures="1" errors="0" skipped="0"/>',
        encoding="utf-8",
    )
    c = ler_contagem_do_trial(report)
    assert c == Contagem(total=4, passando=3, falhando=1, erros=0, ignorados=0)


def test_ler_contagem_do_trial_arquivo_ausente(tmp_path):
    c = ler_contagem_do_trial(tmp_path / "nao-existe.xml")
    assert c == Contagem(total=0, passando=0, falhando=0, erros=0, ignorados=0)
