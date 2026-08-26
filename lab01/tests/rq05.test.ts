import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { obterLinguagemPrimaria } from "../src/metrics/rq05-linguagem.js";

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

describe("obterLinguagemPrimaria (RQ05)", () => {
  it("retorna o nome da linguagem primária", () => {
    const repo = repoFixture({ primaryLanguage: { name: "Python" } });

    expect(obterLinguagemPrimaria(repo)).toBe("Python");
  });

  it('retorna "Não informado" quando o repositório não tem linguagem primária', () => {
    const repo = repoFixture({ primaryLanguage: null });

    expect(obterLinguagemPrimaria(repo)).toBe("Não informado");
  });
});
