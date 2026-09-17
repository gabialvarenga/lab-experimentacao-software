def ranking_trilhas(trilhas: list[dict], pesos: dict, limite: int | None = None) -> list[str]:
    trilhas_validas = []

    peso_distancia = pesos.get("distancia", 0)
    peso_desnivel = pesos.get("desnivel", 0)
    peso_nota = pesos.get("nota", 0)

    for trilha in trilhas:
        distancia = trilha["distancia_km"]
        nota = trilha["nota"]

        if distancia <= 0 or not (0 <= nota <= 5):
            continue

        desnivel = trilha["desnivel_m"]
        pontuacao_bruta = (
            distancia * peso_distancia +
            desnivel * peso_desnivel +
            nota * peso_nota
        )
        pontuacao = round(pontuacao_bruta, 3)

        trilhas_validas.append((pontuacao, trilha["nome"]))

    trilhas_validas.sort(key=lambda x: (-x[0], x[1]))

    nomes = [trilha[1] for trilha in trilhas_validas]

    if limite is not None:
        return nomes[:limite]

    return nomes
