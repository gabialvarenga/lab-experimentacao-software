from datetime import datetime, timedelta, timezone

import pytest

from metricas.lead_time import lead_time_por_commit, lead_time_por_release

DIA = 24
PUBLICACAO = datetime(2026, 3, 15, tzinfo=timezone.utc)


def release(dias_antes, publicacao=PUBLICACAO):
    """Release com um commit a cada `dias_antes` da publicação; `None` mantém `commits = None`."""
    commits = None if dias_antes is None else [publicacao - timedelta(days=dias) for dias in dias_antes]
    return {"published_at": publicacao, "commits": commits}


@pytest.fixture
def releases(fixture_json):
    def carregar(nome):
        return [
            {
                "published_at": datetime.fromisoformat(item["published_at"]),
                "commits": item["commits"] and [datetime.fromisoformat(texto) for texto in item["commits"]],
            }
            for item in fixture_json("lead_time")[nome]
        ]

    return carregar


def test_exemplo_v1_1_variante_a_e_13_dias(releases):
    assert lead_time_por_release(releases("exemplo_v1_1")) == 13 * DIA


def test_exemplo_v1_1_variante_b_recebe_13_5_e_1_dias(releases):
    assert lead_time_por_commit(releases("exemplo_v1_1")) == 5 * DIA  # mediana de 13, 5 e 1


def test_variante_a_e_a_mediana_entre_releases(releases):
    # v1.1 = 13 dias e v1.2 = 3 dias; v1.0 (primeira) e v1.1.1 (sem commits) ficam fora
    assert lead_time_por_release(releases("historico")) == 8 * DIA


def test_variante_b_e_a_mediana_de_todos_os_commits(releases):
    # 13, 5 e 1 dias de v1.1 somados a 3 e 2 dias de v1.2
    assert lead_time_por_commit(releases("historico")) == 3 * DIA


def test_commit_antigo_esquecido_pesa_na_variante_a_e_pouco_na_b():
    dados = [release([200, 3, 2, 1]), release([4, 2])]

    assert lead_time_por_release(dados) == 102 * DIA  # mediana de 200 e 4
    assert lead_time_por_commit(dados) == 2.5 * DIA  # mediana de 200, 4, 3, 2, 2 e 1


def test_primeira_release_do_repositorio_fica_fora():
    dados = [release(None), release([4])]

    assert lead_time_por_release(dados) == 4 * DIA
    assert lead_time_por_commit(dados) == 4 * DIA


def test_release_sem_commits_novos_fica_fora():
    dados = [release([]), release([6, 2])]

    assert lead_time_por_release(dados) == 6 * DIA
    assert lead_time_por_commit(dados) == 4 * DIA


def test_repositorio_com_uma_unica_release_e_indefinido():
    assert lead_time_por_release([release(None)]) is None
    assert lead_time_por_commit([release(None)]) is None


def test_todas_as_releases_sem_commits_e_indefinido():
    assert lead_time_por_release([release(None), release([])]) is None
    assert lead_time_por_commit([release(None), release([])]) is None


def test_sem_releases_e_indefinido():
    assert lead_time_por_release([]) is None
    assert lead_time_por_commit([]) is None


def test_resultado_em_horas_com_fracao():
    publicacao = datetime(2026, 3, 15, 12, 30, tzinfo=timezone.utc)
    dados = [{"published_at": publicacao, "commits": [datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc)]}]

    assert lead_time_por_release(dados) == 1.5
    assert lead_time_por_commit(dados) == 1.5


def test_commit_com_fuso_diferente_do_utc():
    fuso = timezone(timedelta(hours=-3))
    dados = [{"published_at": PUBLICACAO, "commits": [datetime(2026, 3, 14, 20, 0, tzinfo=fuso)]}]

    assert lead_time_por_commit(dados) == 1  # 20:00 em -03:00 = 23:00 UTC


def test_commit_datado_depois_da_release_entra_com_valor_negativo():
    # Definição comum da turma (seção 3): published_at − commit.author.date, sem filtro
    dados = [release([-1, 3, 5])]

    assert lead_time_por_release(dados) == 5 * DIA
    assert lead_time_por_commit(dados) == 3 * DIA
    assert lead_time_por_commit([release([-1])]) == -1 * DIA
