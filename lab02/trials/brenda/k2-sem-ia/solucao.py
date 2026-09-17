import re
import string


def validar_lote(codigo: str) -> list[str]:
    padrao_formato = r"^[a-zA-Z]{3}-\d{4}-[a-zA-Z]$"
    if not re.match(padrao_formato, codigo):
        return ["FORMATO"]

    prefixo, digitos, verificador = codigo.split("-")
    erros = []

    if not prefixo.isupper():
        erros.append("PREFIXO")

    if len(set(digitos)) == 1:
        erros.append("SEQUENCIA")

    soma_digitos = sum(int(d) for d in digitos)
    indice_esperado = soma_digitos % 26
    letra_esperada = string.ascii_uppercase[indice_esperado]

    if verificador != letra_esperada:
        erros.append("DIGITO")

    return erros
