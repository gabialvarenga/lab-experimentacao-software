"""Validação sobre a execução de exemplo real (`dados/brutos/exemplo/`), copiada e alterada."""

import csv
import json
import shutil
from pathlib import Path

import pytest

from lab05 import config, executor, validacao

EXEMPLO = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "exemplo"


@pytest.fixture
def cfg(tmp_path):
    shutil.copytree(EXEMPLO, tmp_path / "coleta")
    c = {**config.carregar(), "pasta": str(tmp_path)}
    return executor.aplicar_ajustes(c, repeticoes=1, saida="coleta")


def _csv(cfg):
    return executor.caminhos(cfg)["csv"]


def _ler(cfg):
    with open(_csv(cfg), newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def _gravar(cfg, linhas, colunas=executor.COLUNAS):
    with open(_csv(cfg), "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def _alterar(cfg, execucao_id, **valores):
    linhas = _ler(cfg)
    for linha in linhas:
        if linha["execucao_id"] == execucao_id:
            linha.update(valores)
    _gravar(cfg, linhas)


def test_exemplo_real_passa_sem_erros(cfg):
    r = validacao.validar(cfg)
    assert r.ok and r.erros == [] and r.avisos == []
    assert r.plano == len(r.dados) == 12


def test_sem_csv(cfg):
    _csv(cfg).unlink()
    assert "rode o executor" in validacao.validar(cfg).erros[0]


def test_colunas_diferentes(cfg):
    _gravar(cfg, [{"a": 1}], colunas=["a"])
    assert "colunas diferentes" in validacao.validar(cfg).erros[0]


@pytest.mark.parametrize(
    "valores, mensagem",
    [
        ({"ops_s": ""}, "valor faltante em `ops_s`"),
        ({"ops_s": "abc"}, "`ops_s` não numérico"),
        ({"memoria_bytes": "-5"}, "`memoria_bytes` ≤ 0"),
        ({"lat_p50_ms": "2", "lat_p99_ms": "1"}, "`lat_p99_ms` menor que `lat_p50_ms`"),
        ({"fim": "2026-11-18T19:00:00-03:00"}, "`fim` antes de `inicio`"),
        ({"fim": "ontem"}, "data inválida"),
        ({"versao": "8.0.0"}, "versão 8.0.0, esperada 8.10.3"),
        ({"ordem": "5"}, "diferente do plano"),
        ({"carga": "get"}, "diferente do plano"),
    ],
)
def test_erros_em_uma_linha(cfg, valores, mensagem):
    _alterar(cfg, "redis-t1-set-r01", **valores)
    r = validacao.validar(cfg)
    assert not r.ok
    assert any(mensagem in erro and "redis-t1-set-r01" in erro for erro in r.erros), r.erros


def test_execucao_fora_do_plano_e_repetida(cfg):
    linhas = _ler(cfg)
    _gravar(cfg, linhas + [linhas[0], {**linhas[1], "execucao_id": "redis-t2-set-r01"}])
    erros = validacao.validar(cfg).erros
    assert any("mais de uma vez" in e for e in erros)
    assert any("redis-t2-set-r01" in e and "fora do plano" in e for e in erros)


def test_execucao_faltando_com_e_sem_falha_registrada(cfg):
    linhas = _ler(cfg)
    _gravar(cfg, linhas[2:])
    falha = {c: "" for c in executor.COLUNAS_FALHAS} | {"execucao_id": linhas[0]["execucao_id"], "etapa": "subida"}
    executor.anexar(executor.caminhos(cfg)["falhas"], executor.COLUNAS_FALHAS, falha)
    erros = validacao.validar(cfg).erros
    assert f"`{linhas[0]['execucao_id']}`: falta no CSV (falhou na etapa subida; rodar de novo o executor)" in erros
    assert f"`{linhas[1]['execucao_id']}`: falta no CSV e não há falha registrada" in erros


def test_falha_repetida_com_sucesso_vira_aviso(cfg):
    falha = {c: "" for c in executor.COLUNAS_FALHAS} | {"execucao_id": "redis-t1-set-r01", "etapa": "medicao"}
    executor.anexar(executor.caminhos(cfg)["falhas"], executor.COLUNAS_FALHAS, falha)
    r = validacao.validar(cfg)
    assert r.ok and r.avisos == ["`redis-t1-set-r01`: falhou (medicao) e foi repetida com sucesso"]


def test_saida_do_cliente_ausente_ilegivel_ou_com_erros_de_conexao(cfg):
    saidas = executor.caminhos(cfg)["saidas"]
    (saidas / "redis-t1-set-r01.json").unlink()
    (saidas / "valkey-t1-get-r01.json").write_text("{", encoding="utf-8")
    arquivo = saidas / "valkey-t1-set-r01.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    dados["ALL STATS"]["Totals"]["Connection Errors"] = 3
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    erros = validacao.validar(cfg).erros
    assert any("redis-t1-set-r01" in e and "ausente" in e for e in erros)
    assert any("valkey-t1-get-r01" in e and "ilegível" in e for e in erros)
    assert "`valkey-t1-set-r01`: 3 erros de conexão do cliente" in erros


def test_versao_esperada_e_opcional(cfg):
    for s in cfg["plano"]["servidores"].values():
        s.pop("versao_esperada")
    _alterar(cfg, "redis-t1-set-r01", versao="1.0")
    assert validacao.validar(cfg).ok


def _duas_repeticoes(cfg, fator):
    """Duplica o exemplo como repetição 2, com `ops_s` multiplicado por `fator`."""
    cfg = executor.aplicar_ajustes(cfg, repeticoes=2)
    plano = {ex.execucao_id: ex for ex in executor.gerar_plano(cfg)}
    linhas = _ler(cfg)
    saidas = executor.caminhos(cfg)["saidas"]
    novas = []
    for linha in linhas:
        eid = linha["execucao_id"].replace("-r01", "-r02")
        shutil.copy(saidas / f"{linha['execucao_id']}.json", saidas / f"{eid}.json")
        novas.append({**linha, "execucao_id": eid, "ordem": plano[eid].ordem, "repeticao": 2, "ops_s": float(linha["ops_s"]) * fator})
    _gravar(cfg, linhas + novas)
    return cfg


def test_cv_alto_vira_aviso_e_aparece_no_relatorio(cfg):
    cfg = _duas_repeticoes(cfg, 1.5)
    r = validacao.validar(cfg)
    assert r.ok
    assert len(r.avisos) == 12 and all("`ops_s`" in a and "acima de 10%" in a for a in r.avisos)
    texto = validacao.escrever_relatorio(cfg, r)
    assert "⚠" in texto and "| 2 |" in texto


def test_resumo_por_combinacao(cfg):
    cfg = _duas_repeticoes(cfg, 1.0)
    resumo = validacao.resumo_por_combinacao(validacao.validar(cfg).dados)
    assert len(resumo) == 12 * 4
    assert (resumo["n"] == 2).all() and (resumo["cv"] == 0).all()


def test_relatorio_sem_erros(cfg):
    r = validacao.validar(cfg)
    texto = validacao.escrever_relatorio(cfg, r)
    assert texto == executor.caminhos(cfg)["qualidade"].read_text(encoding="utf-8")
    assert "**Sem erros**" in texto and "plano: 12; gravadas: 12" in texto
    assert "Tempo total (primeiro início ao último fim): 5,5 min" in texto
    assert "| redis | 1 | set | `ops_s` | 1 | 68.107 | 0 | — |" in texto
    assert "| redis | 1 | set | `lat_p99_ms` | 1 | 1,415 | 0,000 | — |" in texto


def test_relatorio_com_erros_e_sem_dados(cfg, tmp_path):
    _csv(cfg).unlink()
    r = validacao.validar(cfg)
    texto = validacao.escrever_relatorio(cfg, r, tmp_path / "rel.md")
    assert "**1 erro(s)**" in texto and "Variabilidade" not in texto


def test_tempo_sem_datas():
    import pandas as pd

    t = validacao.tempo(pd.DataFrame({"inicio": ["x"], "fim": ["y"]}))
    assert pd.isna(t["total_min"])


def test_caminhos_com_e_sem_nome(cfg):
    piloto = executor.aplicar_ajustes(cfg, piloto=True)
    arquivos = executor.caminhos(piloto)
    assert arquivos["csv"].name == "piloto.csv" and arquivos["registro"].name == "registro-piloto.md"
    assert arquivos["qualidade"].name == "qualidade-piloto.md"
    assert arquivos["pasta"] == (Path(cfg["pasta"]) / "dados" / "piloto").resolve()
    assert piloto["plano"]["repeticoes"] == 5
    assert executor.caminhos(cfg)["registro"] is None
