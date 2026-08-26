import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { getDaysSinceLastUpdate } from "../src/metrics/rq04-lastUpdate.js";

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

describe("getDaysSinceLastUpdate (RQ04)", () => {
  it("calcula os dias desde a última atualização", () => {
    const agora = new Date("2026-01-31T00:00:00Z");
    const repo = repoFixture({ pushedAt: "2026-01-01T00:00:00Z" });

    expect(getDaysSinceLastUpdate(repo, agora)).toBe(30);
  });

  it("retorna 0 para um repositório atualizado agora mesmo", () => {
    const agora = new Date("2026-01-01T12:00:00Z");
    const repo = repoFixture({ pushedAt: agora.toISOString() });

    expect(getDaysSinceLastUpdate(repo, agora)).toBe(0);
  });

  it("um repositório abandonado fica muito mais desatualizado que um ativo", () => {
    const agora = new Date("2026-08-11T00:00:00Z");
    const abandonado = repoFixture({ pushedAt: "2019-01-01T00:00:00Z" });
    const ativo = repoFixture({ pushedAt: "2026-08-01T00:00:00Z" });

    expect(getDaysSinceLastUpdate(abandonado, agora)).toBeGreaterThan(
      getDaysSinceLastUpdate(ativo, agora),
    );
  });
});
