import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import calibracao, config

E = math.e


def quantis_normais(n):
    """n quantis da normal padrão, a amostra mais 'normal' possível para n pontos."""
    return stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)


def tabela(com_bot, sem_bot):
    grupos = ["com_bot"] * len(com_bot) + ["sem_bot"] * len(sem_bot)
    return pd.DataFrame({"grupo": grupos, "horas_ate_merge": [*com_bot, *sem_bot]})


def test_mu_sigma_e_mediana_conferem_com_a_conta_feita_a_mao():
    # log(1), log(e), log(e²) = 0, 1, 2: média 1 e desvio-padrão amostral 1
    r = calibracao.estimar_grupo([1, E, E**2])
    assert r["n"] == 3 and r["mu"] == pytest.approx(1) and r["sigma"] == pytest.approx(1)
    assert r["mediana_implicita"] == pytest.approx(E)
    assert r["piso_somado"] == 0


def test_ic_de_sigma_pela_qui_quadrado_e_de_mu_pela_t_conferem_com_a_conta_feita_a_mao():
    # com 2 graus de liberdade a qui-quadrado tem ppf(q) = −2 · ln(1 − q); t(0,975; 2) = 4,302653
    r = calibracao.estimar_grupo([1, E, E**2])
    qui_inf, qui_sup = -2 * math.log(1 - 0.025), -2 * math.log(1 - 0.975)
    assert r["sigma_ic"] == pytest.approx([math.sqrt(2 / qui_sup), math.sqrt(2 / qui_inf)])
    erro = 4.302653 / math.sqrt(3)
    assert r["mu_ic"] == pytest.approx([1 - erro, 1 + erro], rel=1e-6)
    assert r["confianca"] == 0.95


def test_recupera_os_parametros_de_uma_amostra_grande():
    horas = np.random.default_rng(0).lognormal(mean=2.0, sigma=0.8, size=5000)
    r = calibracao.estimar_grupo(horas, reps=500)
    assert r["mu"] == pytest.approx(2.0, abs=0.05) and r["sigma"] == pytest.approx(0.8, abs=0.03)
    assert r["mu_ic"][0] < r["mu"] < r["mu_ic"][1] and r["sigma_ic"][0] < r["sigma"] < r["sigma_ic"][1]
    assert r["sigma_ic"][1] - r["sigma_ic"][0] < 0.05


def test_bootstrap_e_qui_quadrado_concordam_quando_log_e_normal():
    horas = np.exp(quantis_normais(200) * 0.8 + 1)
    r = calibracao.estimar_grupo(horas, reps=2000)
    assert r["sigma_ic_bootstrap"] == pytest.approx(r["sigma_ic"], rel=0.1)


def test_mesma_semente_gera_a_mesma_calibracao():
    df = tabela(np.exp(quantis_normais(30)), np.exp(quantis_normais(30) * 2))
    a = calibracao.calibrar(df, reps=200, rng=np.random.default_rng(7))
    b = calibracao.calibrar(df, reps=200, rng=np.random.default_rng(7))
    assert a == b
    # sem rng, a semente padrão é 42
    assert calibracao.calibrar(df, reps=200) == calibracao.calibrar(df, reps=200, rng=np.random.default_rng(42))


def test_calibrar_devolve_um_dicionario_por_grupo_com_mu_e_sigma():
    r = calibracao.calibrar(tabela([1, E, E**2], [E, E**2, E**3, E**4]), reps=100)
    assert list(r) == ["com_bot", "sem_bot"]
    assert r["com_bot"]["mu"] == pytest.approx(1) and r["sem_bot"]["mu"] == pytest.approx(2.5)
    assert r["sem_bot"]["sigma"] == pytest.approx(np.std([1, 2, 3, 4], ddof=1))


def test_horas_zero_somam_o_piso_a_todas_as_horas_do_grupo():
    r = calibracao.estimar_grupo([0, 1, 2, 3], piso=0.5, reps=100)
    assert r["piso_somado"] == 0.5
    esperado = np.log([0.5, 1.5, 2.5, 3.5])
    assert r["mu"] == pytest.approx(esperado.mean()) and r["sigma"] == pytest.approx(esperado.std(ddof=1))
    assert calibracao.estimar_grupo([1, 2, 3], piso=0.5, reps=100)["piso_somado"] == 0


def test_horas_negativas_ausentes_ou_piso_invalido_levantam_erro():
    with pytest.raises(ValueError, match="não negativos"):
        calibracao.estimar_grupo([-1, 1, 2])
    with pytest.raises(ValueError, match="não negativos"):
        calibracao.estimar_grupo([np.nan, 1, 2])
    with pytest.raises(ValueError, match="piso"):
        calibracao.estimar_grupo([0, 1, 2], piso=0)


def test_poucos_prs_levantam_erro_ou_avisam():
    with pytest.raises(ValueError, match="sem_bot.*ao menos 3"):
        calibracao.calibrar(tabela([1, 2, 3], [1, 2]), reps=100)
    assert "aviso" in calibracao.estimar_grupo(np.arange(1, 10), reps=100)
    assert "aviso" not in calibracao.estimar_grupo(np.arange(1, 11), reps=100)


def test_grupo_ausente_levanta_erro():
    df = pd.DataFrame({"grupo": ["com_bot"] * 3, "horas_ate_merge": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="sem_bot"):
        calibracao.calibrar(df, reps=100)


def test_ajuste_bom_para_log_normal_e_ruim_para_log_bimodal():
    rng = np.random.default_rng(3)
    bom = calibracao.estimar_grupo(np.exp(quantis_normais(50)), reps=100)["ajuste"]
    assert bom["bom"] is True and bom["shapiro_p"] > 0.5 and bom["qq_r"] > 0.99
    assert bom["assimetria_log"] == pytest.approx(0, abs=1e-6)
    bimodal = np.exp(np.concatenate([rng.normal(0, 0.1, 30), rng.normal(5, 0.1, 30)]))
    ruim = calibracao.estimar_grupo(bimodal, reps=100)
    assert ruim["ajuste"]["bom"] is False and ruim["ajuste"]["shapiro_p"] < 0.05
    assert ruim["mu"] == pytest.approx(2.5, abs=0.2)  # ajuste ruim é registrado e a calibração segue


def test_horas_todas_iguais_dao_sigma_zero_e_ajuste_nao_avaliado():
    r = calibracao.estimar_grupo([5.0, 5.0, 5.0, 5.0], reps=100)
    assert r["sigma"] == 0 and r["sigma_ic"] == [0, 0] and r["sigma_ic_bootstrap"] == [0, 0]
    assert r["ajuste"] == {"shapiro_p": None, "qq_r": None, "assimetria_log": None, "bom": None}


def test_gravar_e_ler_fazem_ida_e_volta_em_json_valido(tmp_path):
    r = calibracao.calibrar(tabela([1, E, E**2], [1, 2, 4, 8]), reps=100)
    caminho = tmp_path / "pasta" / "calibracao.json"
    calibracao.gravar(r, caminho)
    texto = caminho.read_text(encoding="utf-8")
    assert texto.endswith("\n") and "NaN" not in texto
    assert json.loads(texto)["com_bot"]["mu"] == pytest.approx(1)
    assert calibracao.ler(caminho) == r


def test_qq_pontos_de_amostra_lognormal_ficam_sobre_a_reta():
    horas = np.exp(quantis_normais(50) * 0.7 + 1)
    p = calibracao.qq_pontos(horas)
    assert len(p["teoricos"]) == len(p["observados"]) == len(p["reta"]) == 50
    assert p["r"] > 0.99 and np.all(np.diff(p["reta"]) > 0)
    assert p["reta"] == pytest.approx(p["observados"], rel=0.2)


def test_qq_figura_tem_um_painel_por_grupo_com_eixo_log():
    df = tabela(np.exp(quantis_normais(20)), np.exp(quantis_normais(20) * 2))
    fig = calibracao.qq_figura(df)
    assert len(fig.data) == 4 and fig.layout.yaxis.type == "log" and fig.layout.yaxis2.type == "log"
    assert [a.text.split(" (")[0] for a in fig.layout.annotations] == ["com_bot", "sem_bot"]
    assert all("r = " in a.text and "…" not in a.text for a in fig.layout.annotations)


def test_executar_grava_tabela_json_e_qqplot(tmp_path, capsys):
    tabela(np.exp(quantis_normais(30)), np.exp(quantis_normais(30) + 1)).to_csv(tmp_path / "prs.csv", index=False)
    cfg = {
        "semente": 42,
        "pasta": str(tmp_path),
        "coleta": {"saida": "prs.csv"},
        "calibracao": {
            "piso_horas": 0.01, "confianca": 0.9, "repeticoes_bootstrap": 100,
            "descritiva": "saida/descritiva.csv", "saida": "saida/calibracao.json", "qqplot": "saida/qq.html",
        },
    }
    r = calibracao.executar(cfg)
    assert calibracao.ler(tmp_path / "saida" / "calibracao.json") == r
    assert r["com_bot"]["confianca"] == 0.9
    assert pd.read_csv(tmp_path / "saida" / "descritiva.csv", index_col="grupo").loc["sem_bot", "n"] == 30
    assert "plotly" in (tmp_path / "saida" / "qq.html").read_text(encoding="utf-8")
    saida = capsys.readouterr().out
    assert "com_bot: n = 30" in saida and "sem_bot: n = 30" in saida


def test_calibracao_versionada_confere_com_os_dados_reais():
    # Se prs.csv ou o código mudarem, regrave com `python -m lab04 calibrar`.
    cfg = config.carregar()
    base = Path(cfg["pasta"])
    c = cfg["calibracao"]
    df = pd.read_csv(base / cfg["coleta"]["saida"])
    refeita = calibracao.calibrar(
        df, piso=c["piso_horas"], confianca=c["confianca"], reps=c["repeticoes_bootstrap"], rng=config.criar_rng(cfg)
    )
    versionada = calibracao.ler(base / c["saida"])
    for grupo in ("com_bot", "sem_bot"):
        assert refeita[grupo]["n"] == versionada[grupo]["n"] == 30
        for campo in ("mu", "sigma", "mu_ic", "sigma_ic", "sigma_ic_bootstrap"):
            assert versionada[grupo][campo] == pytest.approx(refeita[grupo][campo], rel=1e-6)
