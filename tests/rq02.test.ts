import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { calcularPrsAceitas } from "../src/metrics/rq02-prs.js";

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
    ...overrides,
  };
}

describe("calcularPrsAceitas (RQ02)", () => {
  it("retorna o total de pull requests aceitas (merged)", () => {
    const repo = repoFixture({ pullRequests: { totalCount: 3421 } });

    expect(calcularPrsAceitas(repo)).toBe(3421);
  });

  it("retorna 0 quando não há PRs aceitas", () => {
    const repo = repoFixture({ pullRequests: { totalCount: 0 } });

    expect(calcularPrsAceitas(repo)).toBe(0);
  });
});
