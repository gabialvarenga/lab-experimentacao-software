"""Parser das saídas, com saídas reais gravadas em `tests/dados/`.

Os JSONs são de `memtier_benchmark` 2.6.1 (execução de exemplo de 18/11/2026) e os INFO são do
Redis 8.10.3 e do Valkey 9.1.3, nas imagens fixadas no `compose.yaml`.
"""

import json
from pathlib import Path

import pytest

from lab05 import leitura

DADOS = Path(__file__).parent / "dados"


def _texto(nome: str) -> str:
    return (DADOS / nome).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "arquivo, esperado",
    [
        ("redis-t1-set-r01.json", {"ops_s": 68107.4, "lat_p50_ms": 0.679, "lat_p99_ms": 1.415}),
        ("redis-t4-get-r01.json", None),
        ("valkey-t4-misto-r01.json", None),
    ],
)
def test_ler_memtier_com_saidas_reais(arquivo, esperado):
    texto = _texto(arquivo)
    metricas = leitura.ler_memtier(texto)
    totais = json.loads(texto)["ALL STATS"]["Totals"]
    assert metricas["ops_s"] == totais["Ops/sec"]
    assert metricas["lat_p50_ms"] == totais["Percentile Latencies"]["p50.00"]
    assert metricas["lat_p99_ms"] == totais["Percentile Latencies"]["p99.00"]
    assert 0 < metricas["lat_p50_ms"] <= metricas["lat_p99_ms"]
    if esperado:
        assert metricas == esperado


def _com_totais(**mudancas) -> str:
    dados = json.loads(_texto("redis-t1-set-r01.json"))
    dados["ALL STATS"]["Totals"].update(mudancas)
    return json.dumps(dados)


@pytest.mark.parametrize(
    "texto, mensagem",
    [
        ("{nao e json", "JSON do cliente inválido"),
        ("{}", "ALL STATS"),
        ('{"ALL STATS": {"Totals": []}}', "não é um objeto"),
        (_com_totais(**{"Ops/sec": "abc"}), "não numérico"),
        (_com_totais(**{"Ops/sec": None}), "não numérico"),
        (_com_totais(**{"Ops/sec": -1}), "valor inválido"),
        (_com_totais(**{"Ops/sec": float("nan")}), "valor inválido"),
        (_com_totais(**{"Ops/sec": 0}), "nenhuma operação"),
        (_com_totais(**{"Percentile Latencies": None}), "print-percentiles"),
        (_com_totais(**{"Percentile Latencies": {"p50.00": 0.5}}), "percentil 99"),
    ],
)
def test_ler_memtier_recusa_saida_incompleta(texto, mensagem):
    with pytest.raises(leitura.ErroLeitura, match=mensagem):
        leitura.ler_memtier(texto)


def test_ler_memtier_aceita_percentil_sem_casas_decimais():
    metricas = leitura.ler_memtier(_com_totais(**{"Percentile Latencies": {"p50": 0.5, "p99": 2}}))
    assert (metricas["lat_p50_ms"], metricas["lat_p99_ms"]) == (0.5, 2.0)


def test_ler_info_ignora_secoes_e_linhas_vazias():
    info = leitura.ler_info("# Server\r\nredis_version:8.10.3\r\n\r\nlistener0:name=tcp,port=6379\r\nsem_dois_pontos\r\n")
    assert info == {"redis_version": "8.10.3", "listener0": "name=tcp,port=6379"}


def test_versao_do_redis():
    assert leitura.versao(leitura.ler_info(_texto("info-server-redis.txt")), "redis_version") == "8.10.3"


def test_versao_do_valkey_vem_de_valkey_version_e_nao_de_redis_version():
    info = leitura.ler_info(_texto("info-server-valkey.txt"))
    assert info["redis_version"] == "7.2.4"  # campo de compatibilidade, que não deve ir para o CSV
    assert leitura.versao(info, "valkey_version") == "9.1.3"


def test_versao_ausente():
    with pytest.raises(leitura.ErroLeitura, match="valkey_version"):
        leitura.versao(leitura.ler_info(_texto("info-server-redis.txt")), "valkey_version")


@pytest.mark.parametrize("servidor", ["redis", "valkey"])
def test_memoria_bytes_com_saidas_reais(servidor):
    info = leitura.ler_info(_texto(f"info-memory-{servidor}.txt"))
    assert leitura.memoria_bytes(info) == int(info["used_memory"]) > 0


@pytest.mark.parametrize("info, mensagem", [({}, "sem o campo"), ({"used_memory": "1.5K"}, "inválido")])
def test_memoria_bytes_recusa_valor_ausente_ou_invalido(info, mensagem):
    with pytest.raises(leitura.ErroLeitura, match=mensagem):
        leitura.memoria_bytes(info)
