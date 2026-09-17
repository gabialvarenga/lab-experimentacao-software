def montar_escala(pessoas: list[dict], dias: list[str]) -> dict:
    escala = {p["nome"]: [] for p in pessoas}

    contagem = {p["nome"]: 0 for p in pessoas}

    for dia in dias:

        disponiveis = [
            p["nome"]
            for p in pessoas
            if dia not in p.get("indisponivel", [])
        ]

        if not disponiveis:
            raise ValueError(f"sem cobertura para {dia}")

        escolhido = min(disponiveis, key=lambda nome: (contagem[nome], nome))

        escala[escolhido].append(dia)
        contagem[escolhido] += 1

    return escala