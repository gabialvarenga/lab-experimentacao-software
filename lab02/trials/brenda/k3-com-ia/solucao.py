def _indisponibilidades(pessoa: dict) -> set:
    return set(pessoa.get("indisponivel", []))


def _esta_disponivel(pessoa: dict, dia: str, indisponibilidades: dict) -> bool:
    return dia not in indisponibilidades[pessoa["nome"]]


def _escolher_responsavel(disponiveis: list, contagem: dict) -> dict:
    return min(disponiveis, key=lambda p: (contagem[p["nome"]], p["nome"]))


def montar_escala(pessoas: list, dias: list) -> dict:
    indisponibilidades = {p["nome"]: _indisponibilidades(p) for p in pessoas}
    escala = {p["nome"]: [] for p in pessoas}
    contagem = {p["nome"]: 0 for p in pessoas}

    for dia in dias:
        disponiveis = [
            p for p in pessoas if _esta_disponivel(p, dia, indisponibilidades)
        ]
        if not disponiveis:
            raise ValueError(f"sem cobertura para {dia}")

        responsavel = _escolher_responsavel(disponiveis, contagem)
        escala[responsavel["nome"]].append(dia)
        contagem[responsavel["nome"]] += 1

    return escala
