def ranking_trilhas(
    trilhas: list[dict],
    pesos: dict,
    limite: int | None = None,
) -> list[str]:
    validas = []

    for trilha in trilhas:
        nota = trilha["nota"]
        distancia = trilha["distancia_km"]

        # descarta antes de ordenar
        if not (0 <= nota <= 5) or distancia <= 0:
            continue

        pontuacao = (
            distancia * pesos.get("distancia", 0)
            + trilha["desnivel_m"] * pesos.get("desnivel", 0)
            + nota * pesos.get("nota", 0)
        )
        pontuacao = round(pontuacao, 3)

        validas.append((trilha["nome"], pontuacao))

    # maior pontuação primeiro; empate → nome alfabético
    validas.sort(key=lambda par: (-par[1], par[0]))

    nomes = [nome for nome, _ in validas]

    if limite is not None:
        nomes = nomes[:limite]

    return nomes