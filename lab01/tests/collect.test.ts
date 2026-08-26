import { describe, expect, it } from "vitest";
import { calcularLinha, METRICAS } from "../src/collect.js";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import type { MetricStrategy } from "../src/metrics/types.js";

function repoFixture(overrides: Partial<RawRepository> = {}): RawRepository {
  return {
    nameWithOwner: "exemplo/repo",
    createdAt: "2016-08-11T00:00:00Z",
    pushedAt: "2026-01-01T00:00:00Z",
    pullRequests: { totalCount: 100 },
    releases: { totalCount: 10 },
    primaryLanguage: { name: "TypeScript" },
    totalIssues: { totalCount: 50 },
    closedIssues: { totalCount: 40 },
    forkCount: 25,
    licenseInfo: { name: "MIT License" },
    languages: { totalCount: 3 },
    workflowsDir: { entries: [{ name: "ci.yml" }] },
    ...overrides,
  };
}

describe("METRICAS (estrategias de metrica)", () => {
  it("tem uma estrategia para cada RQ coletada (RQ01-06, RQ08-11)", () => {
    expect(METRICAS).toHaveLength(10);
  });

  it("cada estrategia tem uma chave unica", () => {
    const chaves = METRICAS.map((m) => m.chave);
    expect(new Set(chaves).size).toBe(chaves.length);
  });
});

describe("calcularLinha", () => {
  it("monta uma linha com nome do repo + todas as metricas registradas", () => {
    const repo = repoFixture();
    const linha = calcularLinha(repo);

    expect(linha.nome).toBe("exemplo/repo");
    expect(linha.prs_aceitas).toBe(100);
    expect(linha.total_releases).toBe(10);
    expect(linha.linguagem).toBe("TypeScript");
    expect(linha.razao_issues_fechadas).toBe("0.8000");
    expect(linha.total_forks).toBe(25);
    expect(linha.licenca).toBe("MIT License");
    expect(linha.possui_ci_cd).toBe(true);
    expect(linha.total_linguagens).toBe(3);
  });

  it("aceita uma lista de estrategias diferente (extensibilidade)", () => {
    const estrategiaCustom: MetricStrategy = {
      chave: "sempre_dez",
      calcular: () => 10,
    };

    const linha = calcularLinha(repoFixture(), [estrategiaCustom]);

    expect(linha).toEqual({ nome: "exemplo/repo", sempre_dez: 10 });
  });
});
