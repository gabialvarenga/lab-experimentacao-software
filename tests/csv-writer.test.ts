import { describe, expect, it } from "vitest";
import { toCsv } from "../src/csv/writer.js";

describe("toCsv", () => {
  it("gera cabeçalho e linhas a partir dos objetos", () => {
    const csv = toCsv([
      { nome: "react", estrelas: 230000 },
      { nome: "vue", estrelas: 200000 },
    ]);

    expect(csv).toBe("nome,estrelas\nreact,230000\nvue,200000\n");
  });

  it("escapa valores com vírgula, aspas ou quebra de linha", () => {
    const csv = toCsv([{ nome: 'a, "b"\nc' }]);

    expect(csv).toBe('nome\n"a, ""b""\nc"\n');
  });

  it("retorna string vazia para lista vazia", () => {
    expect(toCsv([])).toBe("");
  });
});
