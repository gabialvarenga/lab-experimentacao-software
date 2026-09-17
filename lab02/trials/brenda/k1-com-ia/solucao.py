TAXAS_POR_SEGUNDO = {
    "leitura": -0.02,
    "transmissao": -0.15,
    "espera": -0.001,
    "recarga": 0.05,
}


def consumo_bateria(eventos, carga_inicial):
    carga = carga_inicial

    for evento in eventos:
        tipo = evento["tipo"]
        duracao_s = evento["duracao_s"]

        if tipo not in TAXAS_POR_SEGUNDO:
            raise ValueError(f"tipo desconhecido: {tipo}")
        if duracao_s < 0:
            raise ValueError("duração negativa")

        carga = carga + TAXAS_POR_SEGUNDO[tipo] * duracao_s
        carga = min(100.0, max(0.0, carga))

    return round(carga, 2)
