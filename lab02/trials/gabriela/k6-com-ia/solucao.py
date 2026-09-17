def ranking_trilhas(trilhas: list[dict], pesos: dict, limite: int | None = None) -> list[str]:
    validas = [
        t for t in trilhas
        if 0 <= t["nota"] <= 5 and t["distancia_km"] > 0
    ]

    pontuadas = []
    for t in validas:
        pontuacao = (
            t["distancia_km"] * pesos.get("distancia", 0)
            + t["desnivel_m"] * pesos.get("desnivel", 0)
            + t["nota"] * pesos.get("nota", 0)
        )
        pontuadas.append((round(pontuacao, 3), t["nome"]))

    pontuadas.sort(key=lambda item: (-item[0], item[1]))

    nomes = [nome for _, nome in pontuadas]
    return nomes[:limite] if limite is not None else nomes
