import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import {
  calcularRazaoForkEstrela,
  contarEstrelas,
} from "../src/metrics/rq08-estrelas-fork.js";

function repoFixture(overrides: Partial<RawRepository> = {}): RawRepository {
  return {
    nameWithOwner: "exemplo/repo",
    createdAt: "2020-01-01T00:00:00Z",
    pushedAt: "2026-01-01T00:00:00Z",
    pullRequests: { totalCount: 0 },
    releases: { totalCount: 0 },
    primaryLanguage: { name: "TypeScript" },
    totalIssues: { totalCount: 0 },
    closedIssues: { totalCount: 0 },
    forkCount: 0,
    stargazerCount: 0,
    licenseInfo: { name: "MIT License" },
    languages: { totalCount: 1 },
    workflowsDir: null,
    ...overrides,
  };
}

describe("contarEstrelas", () => {
  it("retorna o total de estrelas do repositório", () => {
    const repo = repoFixture({ stargazerCount: 15000 });

    expect(contarEstrelas(repo)).toBe(15000);
  });
});

describe("calcularRazaoForkEstrela (RQ08 — hipótese original da Issue #4)", () => {
  it("calcula a razão entre forks e estrelas", () => {
    const repo = repoFixture({ forkCount: 250, stargazerCount: 1000 });

    expect(calcularRazaoForkEstrela(repo)).toBeCloseTo(0.25, 5);
  });

  it("retorna 0 quando o repositório não tem estrelas (evita divisão por zero)", () => {
    const repo = repoFixture({ forkCount: 10, stargazerCount: 0 });

    expect(calcularRazaoForkEstrela(repo)).toBe(0);
  });

  it("retorna 0 quando não há forks nem estrelas", () => {
    const repo = repoFixture({ forkCount: 0, stargazerCount: 0 });

    expect(calcularRazaoForkEstrela(repo)).toBe(0);
  });
});
