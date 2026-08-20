import { describe, expect, it } from "vitest";
import { parseCsv } from "../src/csv/reader.js";

describe("parseCsv", () => {
  it("faz o parse de um CSV simples com cabeçalho e duas linhas", () => {
    const csv = "nome,estrelas\nreact,230000\nvue,200000\n";

    expect(parseCsv(csv)).toEqual([
      { nome: "react", estrelas: "230000" },
      { nome: "vue", estrelas: "200000" },
    ]);
  });

  it("desfaz o escaping de vírgula e aspas internas dentro de um campo entre aspas", () => {
    const csv = 'nome\n"a, ""b""\nc"\n';

    expect(parseCsv(csv)).toEqual([{ nome: 'a, "b"\nc' }]);
  });

  it("ignora \\r antes de \\n (arquivos com quebra de linha CRLF)", () => {
    const csv = "nome,valor\r\nexemplo,1\r\n";

    expect(parseCsv(csv)).toEqual([{ nome: "exemplo", valor: "1" }]);
  });

  it("ignora linhas em branco no meio do arquivo", () => {
    const csv = "nome\na\n\nb\n";

    expect(parseCsv(csv)).toEqual([{ nome: "a" }, { nome: "b" }]);
  });

  it("retorna array vazio para conteúdo vazio", () => {
    expect(parseCsv("")).toEqual([]);
  });
});
