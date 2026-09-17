def consumo_bateria(eventos: list[dict], carga_inicial: float) -> float:
    TAXAS = {
        "leitura": -0.02,
        "transmissao": -0.15,
        "espera": -0.001,
        "recarga": 0.05,
    }

    carga = carga_inicial

    for evento in eventos:
        tipo = evento["tipo"]

        if tipo not in TAXAS:
            raise ValueError(f"tipo desconhecido: {tipo}")

        duracao = evento["duracao_s"]
        if duracao < 0:
            raise ValueError("duração negativa")

        carga += TAXAS[tipo] * duracao

        # clamp depois de CADA evento
        carga = max(0.0, min(100.0, carga))

    return round(carga, 2)