import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { getTotalReleases } from "../src/metrics/rq03-releases.js";

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

describe("getTotalReleases (RQ03)", () => {
  it("retorna o total de releases do repositório", () => {
    const repo = repoFixture({ releases: { totalCount: 214 } });

    expect(getTotalReleases(repo)).toBe(214);
  });

  it("retorna 0 quando o repositório não usa GitHub Releases", () => {
    const repo = repoFixture({ releases: { totalCount: 0 } });

    expect(getTotalReleases(repo)).toBe(0);
  });
});
