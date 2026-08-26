import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { calcularRazaoIssuesFechadas } from "../src/metrics/rq06-issues.js";

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

describe("calcularRazaoIssuesFechadas (RQ06)", () => {
  it("calcula a razão entre issues fechadas e total de issues", () => {
    const repo = repoFixture({
      totalIssues: { totalCount: 50 },
      closedIssues: { totalCount: 30 },
    });

    expect(calcularRazaoIssuesFechadas(repo)).toBeCloseTo(0.6, 5);
  });

  it("retorna 0 quando o repositório não tem nenhuma issue (evita NaN)", () => {
    const repo = repoFixture({
      totalIssues: { totalCount: 0 },
      closedIssues: { totalCount: 0 },
    });

    expect(calcularRazaoIssuesFechadas(repo)).toBe(0);
  });

  it("retorna 1 quando todas as issues estão fechadas", () => {
    const repo = repoFixture({
      totalIssues: { totalCount: 10 },
      closedIssues: { totalCount: 10 },
    });

    expect(calcularRazaoIssuesFechadas(repo)).toBe(1);
  });
});
