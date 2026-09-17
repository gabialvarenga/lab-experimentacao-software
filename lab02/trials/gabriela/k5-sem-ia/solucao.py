def mesclar_leituras(a: list[dict], b: list[dict]) -> list[dict]:
    leituras = {}

    for leitura in a:
        if leitura["valor"] is None:
            continue

        ts = leitura["ts"]

        if ts not in leituras:
            leituras[ts] = leitura.copy()

        elif leitura["precisao"] > leituras[ts]["precisao"]:
            leituras[ts] = leitura.copy()

    for leitura in b:
        if leitura["valor"] is None:
            continue

        ts = leitura["ts"]

        if ts not in leituras:
            leituras[ts] = leitura.copy()

        elif leitura["precisao"] > leituras[ts]["precisao"]:
            leituras[ts] = leitura.copy()

    return sorted(leituras.values(), key=lambda leitura: leitura["ts"])