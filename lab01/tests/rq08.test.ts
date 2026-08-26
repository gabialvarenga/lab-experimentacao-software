import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { calcularTotalForks } from "../src/metrics/rq08-forks.js";

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
    licenseInfo: { name: "MIT License" },
    languages: { totalCount: 1 },
    workflowsDir: null,
    ...overrides,
  };
}

describe("calcularTotalForks (RQ08)", () => {
  it("retorna o total de forks do repositório", () => {
    const repo = repoFixture({ forkCount: 4821 });

    expect(calcularTotalForks(repo)).toBe(4821);
  });

  it("retorna 0 quando o repositório não tem forks", () => {
    const repo = repoFixture({ forkCount: 0 });

    expect(calcularTotalForks(repo)).toBe(0);
  });
});
