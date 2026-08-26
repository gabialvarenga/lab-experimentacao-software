import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { calcularIdadeAnos } from "../src/metrics/rq01-idade.js";

function repoFixture(overrides: Partial<RawRepository> = {}): RawRepository {
  return {
    nameWithOwner: "exemplo/repo",
    createdAt: "2016-08-11T00:00:00Z",
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

describe("calcularIdadeAnos (RQ01)", () => {
  it("calcula a idade em anos a partir da data de criação", () => {
    const repo = repoFixture({ createdAt: "2016-08-11T00:00:00Z" });
    const dataReferencia = new Date("2026-08-11T00:00:00Z");

    expect(calcularIdadeAnos(repo, dataReferencia)).toBeCloseTo(10, 1);
  });

  it("retorna ~0 para um repositório criado hoje", () => {
    const hoje = new Date("2026-08-11T12:00:00Z");
    const repo = repoFixture({ createdAt: hoje.toISOString() });

    expect(calcularIdadeAnos(repo, hoje)).toBeCloseTo(0, 5);
  });
});
