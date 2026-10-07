from datetime import date, datetime, timezone

import pytest

from metricas.frequencia import deploys_na_janela, frequencia_deploy

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)  # 365 dias


def release(tag, publicada, draft=False, prerelease=False):
    return {"tag_name": tag, "published_at": publicada, "draft": draft, "prerelease": prerelease}


def utc(ano, mes, dia, hora=12, minuto=0, segundo=0):
    return datetime(ano, mes, dia, hora, minuto, segundo, tzinfo=timezone.utc)


def tags(releases):
    return [r["tag_name"] for r in releases]


def test_52_deploys_em_365_dias_dao_cerca_de_1_por_semana():
    releases = [release(f"v{i}", utc(2025, 10, 1) + (utc(2026, 9, 30) - utc(2025, 10, 1)) * i // 51) for i in range(52)]

    assert len(deploys_na_janela(releases, INICIO, FIM)) == 52
    assert frequencia_deploy(releases, INICIO, FIM) == pytest.approx(52 / (365 / 7))
    assert frequencia_deploy(releases, INICIO, FIM) == pytest.approx(0.997, abs=0.001)


def test_release_no_primeiro_instante_da_janela_entra():
    releases = [release("v1", utc(2025, 10, 1, 0, 0, 0))]

    assert tags(deploys_na_janela(releases, INICIO, FIM)) == ["v1"]


def test_release_no_ultimo_instante_da_janela_entra():
    releases = [release("v1", datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc))]

    assert tags(deploys_na_janela(releases, INICIO, FIM)) == ["v1"]


def test_release_um_segundo_antes_ou_depois_da_janela_nao_entra():
    releases = [
        release("antes", utc(2025, 9, 30, 23, 59, 59)),
        release("depois", utc(2026, 10, 1, 0, 0, 0)),
    ]

    assert deploys_na_janela(releases, INICIO, FIM) == []


def test_draft_e_prerelease_nao_contam_como_deploy():
    releases = [
        release("v1", utc(2026, 1, 1)),
        release("v2-rc1", utc(2026, 1, 2), prerelease=True),
        release("v2-rascunho", None, draft=True),
        release("v3-rascunho-com-data", utc(2026, 1, 3), draft=True),
    ]

    assert tags(deploys_na_janela(releases, INICIO, FIM)) == ["v1"]
    assert frequencia_deploy(releases, INICIO, FIM) == pytest.approx(1 / (365 / 7))


def test_release_sem_data_de_publicacao_nao_conta():
    assert deploys_na_janela([release("v1", None)], INICIO, FIM) == []


def test_sem_releases_a_frequencia_e_zero():
    assert frequencia_deploy([], INICIO, FIM) == 0.0


def test_releases_de_fora_da_janela_nao_entram_na_frequencia():
    releases = [release("velha", utc(2024, 5, 1)), release("v1", utc(2026, 5, 1))]

    assert frequencia_deploy(releases, INICIO, FIM) == pytest.approx(1 / (365 / 7))


def test_janela_invertida_levanta_erro():
    with pytest.raises(ValueError):
        frequencia_deploy([], FIM, INICIO)
