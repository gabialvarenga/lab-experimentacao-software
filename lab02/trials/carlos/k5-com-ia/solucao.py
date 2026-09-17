def mesclar_leituras(a: list[dict], b: list[dict]) -> list[dict]:
    melhores: dict[int, dict] = {}

    for lista in (a, b):
        for leitura in lista:
            if leitura["valor"] is None:
                continue
            ts = leitura["ts"]
            atual = melhores.get(ts)
            if atual is None or leitura["precisao"] > atual["precisao"]:
                melhores[ts] = dict(leitura)

    return [melhores[ts] for ts in sorted(melhores)]
