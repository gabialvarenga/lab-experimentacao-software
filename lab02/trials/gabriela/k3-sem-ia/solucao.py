def montar_escala(pessoas: list[dict], dias: list[str]) -> dict:
    resultado = {pessoa["nome"]: [] for pessoa in pessoas}
    plantoes = {pessoa["nome"]: 0 for pessoa in pessoas}

    for dia in dias:
        disponiveis = []

        for pessoa in pessoas:
            indisp = pessoa.get("indisponivel", [])
            if dia not in indisp:
                disponiveis.append(pessoa)

        if not disponiveis:
            raise ValueError(f"sem cobertura para {dia}")

        escolhida = min(
            disponiveis,
            key=lambda pessoa: (
                plantoes[pessoa["nome"]],
                pessoa["nome"]
            )
        )

        resultado[escolhida["nome"]].append(dia)
        plantoes[escolhida["nome"]] += 1

    return resultado