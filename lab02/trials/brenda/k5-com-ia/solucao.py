def _leituras_validas(leituras: list[dict]) -> list[dict]:
    return [dict(r) for r in leituras if r["valor"] is not None]


def _melhor(atual: dict, candidata: dict) -> dict:
    if candidata["precisao"] > atual["precisao"]:
        return candidata
    return atual


def _mesclar_em(indice: dict[int, dict], leituras: list[dict]) -> None:
    for leitura in leituras:
        ts = leitura["ts"]
        if ts not in indice:
            indice[ts] = leitura
        else:
            indice[ts] = _melhor(indice[ts], leitura)


def mesclar_leituras(a: list[dict], b: list[dict]) -> list[dict]:
    indice: dict[int, dict] = {}
    _mesclar_em(indice, _leituras_validas(a))
    _mesclar_em(indice, _leituras_validas(b))
    return sorted(indice.values(), key=lambda r: r["ts"])
