def validar_lote(codigo: str) -> list[str]:
    erros = []

    formato_ok = (
        len(codigo) == 10
        and codigo[3] == "-"
        and codigo[8] == "-"
        and codigo[0:3].isalpha()
        and codigo[4:8].isdigit()
        and codigo[9].isalpha()
    )

    if not formato_ok:
        return ["FORMATO"]

    prefixo = codigo[0:3]

    if not prefixo.isupper():
        erros.append("PREFIXO")

    sequencia = codigo[4:8]

    if len(set(sequencia)) == 1:
        erros.append("SEQUENCIA")

    digitos = codigo[4:8]

    soma = sum(int(d) for d in digitos)

    alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    letra_correta = alfabeto[soma % 26]

    if codigo[9] != letra_correta:
        erros.append("DIGITO")

    return erros