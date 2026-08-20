import { describe, expect, it } from "vitest";
import {
  mediana,
  quartis,
  detectarOutliers,
  paraNumeroOuNulo,
  resumoNumerico,
  resumoCategorico,
  resumoBooleano,
} from "../src/stats/descriptive.js";

describe("mediana", () => {
  it("calcula a mediana de um array com número ímpar de elementos", () => {
    expect(mediana([3, 1, 2])).toBe(2);
  });

  it("calcula a mediana de um array com número par de elementos", () => {
    expect(mediana([1, 2, 3, 4])).toBe(2.5);
  });
});

describe("quartis", () => {
  it("calcula Q1 e Q3 por interpolação linear", () => {
    const { q1, q3 } = quartis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);

    expect(q1).toBeCloseTo(3.25, 2);
    expect(q3).toBeCloseTo(7.75, 2);
  });
});

describe("detectarOutliers", () => {
  it("identifica outlier acima do limite superior do IQR", () => {
    const resultado = detectarOutliers([1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]);

    expect(resultado.contagem).toBe(1);
  });

  it("não aponta outliers num conjunto sem valores extremos", () => {
    const resultado = detectarOutliers([1, 2, 3, 4, 5]);

    expect(resultado.contagem).toBe(0);
  });
});

describe("paraNumeroOuNulo", () => {
  it("converte string numérica em número", () => {
    expect(paraNumeroOuNulo("42")).toBe(42);
  });

  it("retorna null para string vazia", () => {
    expect(paraNumeroOuNulo("")).toBeNull();
  });

  it("retorna null para valor não numérico", () => {
    expect(paraNumeroOuNulo("abc")).toBeNull();
  });
});

describe("resumoNumerico", () => {
  it("calcula min, max, mediana e conta ausentes", () => {
    const resumo = resumoNumerico([1, 2, null, 4, 5]);

    expect(resumo.min).toBe(1);
    expect(resumo.max).toBe(5);
    expect(resumo.mediana).toBe(3);
    expect(resumo.ausentes).toBe(1);
    expect(resumo.total).toBe(5);
  });
});

describe("resumoCategorico", () => {
  it("retorna o top de categorias por frequência e conta ausentes", () => {
    const valores = ["JavaScript", "Python", "JavaScript", "Não informado", "Python", "JavaScript"];
    const resumo = resumoCategorico(valores, "Não informado", 2);

    expect(resumo.topCategorias).toEqual([
      { valor: "JavaScript", contagem: 3 },
      { valor: "Python", contagem: 2 },
    ]);
    expect(resumo.ausentes).toBe(1);
    expect(resumo.categoriasUnicas).toBe(2);
  });
});

describe("resumoBooleano", () => {
  it("conta valores true/false", () => {
    const resumo = resumoBooleano(["true", "false", "true"]);

    expect(resumo.verdadeiro).toBe(2);
    expect(resumo.falso).toBe(1);
    expect(resumo.ausentes).toBe(0);
  });
});
