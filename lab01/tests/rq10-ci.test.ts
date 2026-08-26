import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { possuiCiCd } from "../src/metrics/rq10-ci.js";

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

describe("possuiCiCd (RQ10)", () => {
  it("retorna true quando existem arquivos de workflow em .github/workflows", () => {
    const repo = repoFixture({
      workflowsDir: { entries: [{ name: "ci.yml" }] },
    });

    expect(possuiCiCd(repo)).toBe(true);
  });

  it("retorna false quando .github/workflows não existe", () => {
    const repo = repoFixture({ workflowsDir: null });

    expect(possuiCiCd(repo)).toBe(false);
  });

  it("retorna false quando .github/workflows existe mas está vazio", () => {
    const repo = repoFixture({ workflowsDir: { entries: [] } });

    expect(possuiCiCd(repo)).toBe(false);
  });
});
