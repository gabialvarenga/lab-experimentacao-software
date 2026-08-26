function parseLinhas(conteudo: string): string[][] {
  const linhas: string[][] = [];
  let linhaAtual: string[] = [];
  let campoAtual = "";
  let dentroDeAspas = false;
  let indice = 0;

  while (indice < conteudo.length) {
    const caractere = conteudo[indice];

    if (dentroDeAspas) {
      if (caractere === '"') {
        if (conteudo[indice + 1] === '"') {
          campoAtual += '"';
          indice += 2;
          continue;
        }
        dentroDeAspas = false;
        indice++;
        continue;
      }
      campoAtual += caractere;
      indice++;
      continue;
    }

    if (caractere === '"') {
      dentroDeAspas = true;
      indice++;
      continue;
    }

    if (caractere === ",") {
      linhaAtual.push(campoAtual);
      campoAtual = "";
      indice++;
      continue;
    }

    if (caractere === "\r") {
      indice++;
      continue;
    }

    if (caractere === "\n") {
      linhaAtual.push(campoAtual);
      linhas.push(linhaAtual);
      linhaAtual = [];
      campoAtual = "";
      indice++;
      continue;
    }

    campoAtual += caractere;
    indice++;
  }

  if (campoAtual !== "" || linhaAtual.length > 0) {
    linhaAtual.push(campoAtual);
    linhas.push(linhaAtual);
  }

  return linhas;
}

export function parseCsv(conteudo: string): Record<string, string>[] {
  const linhas = parseLinhas(conteudo);
  if (linhas.length === 0) {
    return [];
  }

  const [cabecalho, ...dados] = linhas;

  return dados
    .filter((linha) => !(linha.length === 1 && linha[0] === ""))
    .map((linha) => {
      const registro: Record<string, string> = {};
      cabecalho.forEach((chave, indice) => {
        registro[chave] = linha[indice] ?? "";
      });
      return registro;
    });
}
