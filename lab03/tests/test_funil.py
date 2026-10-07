import csv
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from pipeline import funil
from pipeline.funil import ERRO_DA_API, SEM_ACTIONS, Funil, aprovado

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)
FIXTURE_CSV = Path(__file__).parent / "fixtures" / "funil_exemplo.csv"


def releases(quantidade, **campos):
    return [
        {
            "tag_name": f"v{i}",
            "published_at": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            "draft": False,
            "prerelease": False,
            **campos,
        }
        for i in range(quantidade)
    ]


def runs(quantidade, conclusion="success"):
    return [{"id": i, "conclusion": conclusion} for i in range(quantidade)]


# aprovado


def test_aprovado_com_o_minimo_exato_de_releases_e_runs():
    assert aprovado(releases(5), runs(50), INICIO, FIM) == (True, None)


def test_menos_de_5_releases_descarta():
    assert aprovado(releases(4), runs(50), INICIO, FIM) == (False, "menos de 5 releases")


def test_menos_de_50_runs_validos_descarta():
    assert aprovado(releases(5), runs(49), INICIO, FIM) == (False, "menos de 50 runs")


def test_quatro_deploys_e_500_runs_sao_descartados_por_releases():
    assert aprovado(releases(4), runs(500), INICIO, FIM) == (False, "menos de 5 releases")


def test_runs_none_decide_so_pelas_releases():
    assert aprovado(releases(5), None, INICIO, FIM) == (True, None)
    assert aprovado(releases(4), None, INICIO, FIM) == (False, "menos de 5 releases")


def test_runs_ignorados_nao_contam_como_validos():
    ignorados = runs(40, "cancelled") + runs(30, "skipped") + runs(10, None)
    validos = runs(49, "failure")

    assert aprovado(releases(5), ignorados + validos, INICIO, FIM) == (False, "menos de 50 runs")
    assert aprovado(releases(5), ignorados + validos + runs(1, "timed_out"), INICIO, FIM) == (True, None)


def test_drafts_e_prereleases_nao_contam_como_release():
    mistas = releases(4) + releases(3, prerelease=True) + releases(3, draft=True)

    assert aprovado(mistas, None, INICIO, FIM) == (False, "menos de 5 releases")


def test_releases_fora_da_janela_nao_contam():
    antigas = releases(10, published_at=datetime(2024, 1, 1, tzinfo=timezone.utc))

    assert aprovado(antigas + releases(4), None, INICIO, FIM) == (False, "menos de 5 releases")


def test_release_nos_limites_da_janela_conta():
    nos_limites = [
        {"tag_name": "ini", "published_at": datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc), "draft": False, "prerelease": False},
        {"tag_name": "fim", "published_at": datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc), "draft": False, "prerelease": False},
    ]

    assert aprovado(nos_limites + releases(3), None, INICIO, FIM) == (True, None)


def test_limites_podem_ser_passados_como_parametro():
    assert aprovado(releases(2), runs(3), INICIO, FIM, min_releases=2, min_runs=3) == (True, None)
    assert aprovado(releases(2), runs(2), INICIO, FIM, min_releases=2, min_runs=3) == (False, "menos de 3 runs")


def test_motivos_sao_distintos_entre_si():
    motivos = {SEM_ACTIONS, ERRO_DA_API, funil.motivo_poucas_releases(), funil.motivo_poucos_runs()}

    assert motivos == {"sem Actions", "erro da API", "menos de 5 releases", "menos de 50 runs"}


# Funil


def exemplo():
    f = Funil()
    f.registrar("Com GitHub Actions", 4000, 2900, SEM_ACTIONS)
    f.registrar("Coleta sem erro", 2900, 2880, ERRO_DA_API)
    f.registrar("Releases na janela", 2880, 1100, funil.motivo_poucas_releases())
    f.registrar("Runs válidos na janela", 1100, 610, funil.motivo_poucos_runs())
    f.registrar("Amostra final", 610, 100, "fora da amostra (limite de 100 aprovados)")
    return f


def test_salvar_csv_grava_etapa_entrada_saida_e_motivo(tmp_path):
    caminho = tmp_path / "funil.csv"

    exemplo().salvar_csv(str(caminho))

    esperado = FIXTURE_CSV.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert caminho.read_bytes().decode("utf-8") == esperado
    assert esperado.splitlines()[0] == "etapa,entrada,saida,motivo"


def test_salvar_csv_cria_a_pasta_e_sobrescreve(tmp_path):
    caminho = tmp_path / "dados" / "saida" / "funil.csv"
    f = Funil()
    f.registrar("A", 10, 5, "x")
    f.salvar_csv(str(caminho))
    outro = Funil()
    outro.registrar("B", 3, 3, "")
    outro.salvar_csv(str(caminho))

    assert caminho.read_text(encoding="utf-8").splitlines() == ["etapa,entrada,saida,motivo", "B,3,3,"]


def test_motivo_com_virgula_e_aspas_e_escapado(tmp_path):
    f = Funil()
    f.registrar("Etapa, com vírgula", 2, 1, 'motivo "citado", com vírgula')
    caminho = tmp_path / "funil.csv"
    f.salvar_csv(str(caminho))

    with open(caminho, encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.reader(arquivo))
    assert linhas[1] == ["Etapa, com vírgula", "2", "1", 'motivo "citado", com vírgula']


def test_funil_vazio_grava_so_o_cabecalho(tmp_path):
    caminho = tmp_path / "funil.csv"
    Funil().salvar_csv(str(caminho))

    assert caminho.read_text(encoding="utf-8").splitlines() == ["etapa,entrada,saida,motivo"]


def test_registrar_preserva_a_ordem_das_etapas():
    assert [linha[0] for linha in exemplo().linhas][:2] == ["Com GitHub Actions", "Coleta sem erro"]


def test_registrar_rejeita_saida_maior_que_entrada():
    with pytest.raises(ValueError):
        Funil().registrar("A", 5, 6, "x")


def test_registrar_rejeita_valores_negativos():
    with pytest.raises(ValueError):
        Funil().registrar("A", -1, 0, "x")
    with pytest.raises(ValueError):
        Funil().registrar("A", 5, -1, "x")
