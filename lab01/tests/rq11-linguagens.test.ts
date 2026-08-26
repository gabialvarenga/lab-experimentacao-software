import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { contarLinguagens } from "../src/metrics/rq11-linguagens.js";

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

describe("contarLinguagens (RQ11)", () => {
  it("retorna o número de linguagens usadas no repositório", () => {
    const repo = repoFixture({ languages: { totalCount: 7 } });

    expect(contarLinguagens(repo)).toBe(7);
  });

  it("retorna 0 quando não há linguagens detectadas", () => {
    const repo = repoFixture({ languages: { totalCount: 0 } });

    expect(contarLinguagens(repo)).toBe(0);
  });
});
