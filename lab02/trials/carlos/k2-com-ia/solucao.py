import re

ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FORMATO = re.compile(r"^([A-Za-z]{3})-(\d{4})-([A-Za-z])$")


def validar_lote(codigo: str) -> list[str]:
    match = FORMATO.match(codigo)
    if not match:
        return ["FORMATO"]

    prefixo, digitos, verificador = match.groups()
    erros = []

    if prefixo != prefixo.upper():
        erros.append("PREFIXO")

    if len(set(digitos)) == 1:
        erros.append("SEQUENCIA")

    soma = sum(int(d) for d in digitos)
    esperado = ALFABETO[soma % 26]
    if verificador.upper() != esperado:
        erros.append("DIGITO")

    return erros
