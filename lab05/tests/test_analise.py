import shutil

import pandas as pd
import pytest

from conftest import PILOTO
from lab05 import analise, config, executor, testes

RAPIDO = {"grade_n": [5, 10], "candidatos_n": [5, 10], "diferencas": [0.05, 0.5], "simulacoes": 100, "bootstrap": 200}
ARQUIVOS = ["descritiva", "teste-principal", "comparacoes", "repeticoes", "curva-poder", "diferenca-detectavel", "q3", "q3-curva-poder", "q3-diferenca-detectavel", "pareada"]


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "coleta").mkdir()
    shutil.copy(PILOTO, tmp_path / "coleta" / "piloto.csv")
    c = {**config.carregar(), "pasta": str(tmp_path)}
    c["analise"] = {**c["analise"], **RAPIDO}
    return executor.aplicar_ajustes(c, saida="coleta", nome="piloto")


def test_parametros_completam_o_config_com_os_padroes():
    p = analise.parametros({"analise": {"poder": 0.9}})
    assert p["poder"] == 0.9 and p["diferenca_relevante"] == 0.05 and p["cenario_holm"] == "conservador"
    assert analise.parametros({})["simulacoes"] == analise.PADROES["simulacoes"]


def test_config_versionado_tem_o_bloco_de_analise():
    p = analise.parametros(config.carregar())
    assert (p["diferenca_relevante"], p["alfa"], p["poder"], p["bootstrap"]) == (0.05, 0.05, 0.80, 10000)
    assert set(p["teste_principal"].values()) == {"mann_whitney"} and p["metodo_q3"] == {"ops_s": "art", "lat_p99_ms": "art"}


def test_fixadas_confere_as_decisoes_do_config():
    assert analise.fixadas({}, "metodo_q3", ["ops_s"], ("anova", "art")) == {}
    assert analise.fixadas({"metodo_q3": {"ops_s": "art"}}, "metodo_q3", ["ops_s"], ("anova", "art")) == {"ops_s": "art"}
    with pytest.raises(ValueError, match="faltam"):
        analise.fixadas({"metodo_q3": {"ops_s": "art"}}, "metodo_q3", ["ops_s", "lat_p99_ms"], ("anova", "art"))
    with pytest.raises(ValueError, match="desconhecidos"):
        analise.fixadas({"metodo_q3": {"ops_s": "kruskal"}}, "metodo_q3", ["ops_s"], ("anova", "art"))


def test_decisoes_fixas_valem_mesmo_quando_a_regra_discorda(cfg):
    cfg["analise"] = {**cfg["analise"], "teste_principal": dict.fromkeys(analise.descritiva.METRICAS, "welch"),
                      "metodo_q3": {"ops_s": "anova", "lat_p99_ms": "anova"}}  # fmt: skip
    r = analise.analisar(cfg)
    escolha = r["teste-principal"]
    assert (escolha["teste"] == "mann_whitney").all() and (escolha["teste_usado"] == "welch").all() and (escolha["origem"] == "config").all()
    assert (r["comparacoes"]["teste_principal"] == "welch").all()
    assert (r["q3"]["teste"] == "anova").all() and (r["q3"]["regra_metodo"] == "art").all()


def test_sem_decisoes_fixas_a_regra_decide(cfg):
    cfg["analise"] = {k: v for k, v in cfg["analise"].items() if k not in ("teste_principal", "metodo_q3")}
    r = analise.analisar(cfg)
    assert (r["teste-principal"]["origem"] == "regra").all() and (r["q3"]["teste"] == r["q3"]["regra_metodo"]).all()


def test_analisar_o_piloto_gera_todas_as_tabelas(cfg):
    r = analise.analisar(cfg)
    assert list(r) == ARQUIVOS
    assert len(r["descritiva"]) == 48 and len(r["teste-principal"]) == 4 and len(r["comparacoes"]) == 24
    assert len(r["repeticoes"]) == 3 * 4 and set(r["repeticoes"]["variabilidade"]) == {"bruta", "sem efeito de bloco"}
    assert set(r["repeticoes"]["cenario"]) == {"conservador", "todas"}
    assert len(r["curva-poder"]) == 4 * 2 * 6 and len(r["diferenca-detectavel"]) == 2 * 4 * 2
    assert r["diferenca-detectavel"]["analise"].value_counts().to_dict() == {"independente": 8, "pareada": 8}
    assert len(r["q3"]) == 2 * 3 and (r["q3"]["teste"] == "art").all()
    assert len(r["q3-diferenca-detectavel"]) == 2 * 3 and len(r["q3-curva-poder"]) == 2 * 3 * len(analise.parametros(cfg)["diferencas_q3"])
    assert len(r["pareada"]) == 24 and (r["pareada"]["n_excluidos"] == 0).all() and r["pareada"]["situacao_principal"].notna().all()


def test_q3_nao_muda_os_sorteios_das_comparacoes(cfg):
    r = analise.analisar(cfg)
    p = analise.parametros(cfg)
    sozinhas = testes.comparar(analise.ler_coleta(cfg), "ops_s", "mann_whitney", config.criar_rng(cfg), p["bootstrap"])
    pd.testing.assert_frame_equal(sozinhas, r["comparacoes"].head(6))


def test_execucao_refeita_sai_da_analise_pareada(cfg):
    pasta = executor.caminhos(cfg)["pasta"]
    pd.DataFrame({"execucao_id": ["redis-t1-get-r02"], "etapa": ["carga"]}).to_csv(pasta / "falhas.csv", index=False)
    t = analise.analisar(cfg)["pareada"].set_index(["metrica", "io_threads", "carga"])
    assert (t.xs((1, "get"), level=["io_threads", "carga"])["n_pares"] == 4).all()
    assert t["n_excluidos"].sum() == 4  # uma por métrica


def test_gravar_escreve_os_csvs_e_um_registro_deterministico(cfg):
    r = analise.analisar(cfg)
    pasta = analise.gravar(cfg, r, "python -m lab05 analisar")
    assert pasta == analise.pasta_saida(cfg)
    assert all((pasta / f"{nome}.csv").exists() for nome in ARQUIVOS)
    texto = (pasta / "registro-analise.md").read_text(encoding="utf-8")
    assert texto == analise.registro(cfg, analise.analisar(cfg), "python -m lab05 analisar")
    for trecho in ("# Registro da análise — piloto.csv", "`python -m lab05 analisar`", "| Execuções | 60 |",
                   "## Teste principal por métrica (regra 5.1)", "**não é conclusão**", "| n = 5 | n = 10 |",
                   "## Q3: interação servidor × io_threads", "## Análise pareada por bloco (sensibilidade)",
                   "| `ops_s` | pareada |"):  # fmt: skip
        assert trecho in texto
    assert analise.sha256(executor.caminhos(cfg)["csv"]) in texto


def test_aviso_de_piloto_so_aparece_com_as_repeticoes_do_piloto(cfg):
    desc = pd.DataFrame({"n": [5, 5]})
    assert "não é conclusão" in analise._aviso_repeticoes(cfg, desc)
    completa = analise._aviso_repeticoes(cfg, pd.DataFrame({"n": [40, 40]}))
    assert completa == "40 repetições por combinação."


def test_sha256_ignora_a_diferenca_entre_lf_e_crlf(tmp_path):
    (tmp_path / "lf.txt").write_bytes(b"a\nb\n")
    (tmp_path / "crlf.txt").write_bytes(b"a\r\nb\r\n")
    assert analise.sha256(tmp_path / "lf.txt") == analise.sha256(tmp_path / "crlf.txt")


def test_sem_csv_levanta_erro(cfg):
    executor.caminhos(cfg)["csv"].unlink()
    with pytest.raises(FileNotFoundError, match="rode o executor"):
        analise.analisar(cfg)
