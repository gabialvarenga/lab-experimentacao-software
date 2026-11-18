"""Leitura das saídas do cliente de carga e do servidor (parser), separada do executor.

Não usa Docker: recebe o texto já gravado. Por isso é testada no CI com saídas reais gravadas
em `tests/dados/`.

- `ler_memtier`: o JSON de `memtier_benchmark --json-out-file` (2.6.1) -> ops/s, p50 e p99 em ms.
- `ler_info`: a resposta de `INFO` do Redis ou do Valkey -> dicionário campo: valor.
- `versao` e `memoria_bytes`: os campos de `INFO server` e `INFO memory` usados no CSV.

Nenhuma função inventa valor: se o campo falta ou não é número, levanta `ErroLeitura`.
"""

import json
import math


class ErroLeitura(Exception):
    """A saída não tem o formato esperado; a execução vira falha, sem valor inventado."""


def _numero(valor, nome: str) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErroLeitura(f"{nome}: valor não numérico ({valor!r})") from None
    if not math.isfinite(numero) or numero < 0:
        raise ErroLeitura(f"{nome}: valor inválido ({valor!r})")
    return numero


def _percentil(percentis: dict, alvo: float, nome: str) -> float:
    """Procura a chave do percentil (`p50.00`, `p99.00`, ...) pelo valor, não pelo texto."""
    for chave, valor in percentis.items():
        try:
            if float(str(chave).lstrip("pP")) == alvo:
                return _numero(valor, nome)
        except ValueError:
            continue
    raise ErroLeitura(f"{nome}: percentil {alvo:g} ausente na saída do cliente")


def ler_memtier(texto: str) -> dict:
    """Extrai `ops_s`, `lat_p50_ms` e `lat_p99_ms` do bloco `ALL STATS` > `Totals`.

    O memtier_benchmark já mede a latência em milissegundos. Exige `--print-percentiles=50,99`.
    """
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise ErroLeitura(f"JSON do cliente inválido: {erro}") from None
    try:
        totais = dados["ALL STATS"]["Totals"]
    except (KeyError, TypeError):
        raise ErroLeitura("JSON do cliente sem 'ALL STATS' > 'Totals'") from None
    if not isinstance(totais, dict):
        raise ErroLeitura("JSON do cliente: 'Totals' não é um objeto")
    ops = _numero(totais.get("Ops/sec"), "ops_s")
    if ops == 0:
        raise ErroLeitura("ops_s: nenhuma operação concluída")
    percentis = totais.get("Percentile Latencies")
    if not isinstance(percentis, dict):
        raise ErroLeitura("JSON do cliente sem 'Percentile Latencies' (faltou --print-percentiles?)")
    return {
        "ops_s": ops,
        "lat_p50_ms": _percentil(percentis, 50.0, "lat_p50_ms"),
        "lat_p99_ms": _percentil(percentis, 99.0, "lat_p99_ms"),
    }


def ler_info(texto: str) -> dict:
    """Transforma a resposta de `INFO` (linhas `campo:valor`, seções com `#`) em dicionário."""
    campos = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or ":" not in linha:
            continue
        campo, valor = linha.split(":", 1)
        campos[campo] = valor
    return campos


def versao(info: dict, campo: str) -> str:
    """Versão do servidor no campo indicado (`redis_version` ou `valkey_version`)."""
    valor = info.get(campo, "").strip()
    if not valor:
        raise ErroLeitura(f"INFO server sem o campo '{campo}'")
    return valor


def memoria_bytes(info: dict) -> int:
    """`used_memory` de `INFO memory`, em bytes."""
    if "used_memory" not in info:
        raise ErroLeitura("INFO memory sem o campo 'used_memory'")
    valor = info["used_memory"].strip()
    if not valor.isdigit():
        raise ErroLeitura(f"used_memory: valor inválido ({valor!r})")
    return int(valor)
