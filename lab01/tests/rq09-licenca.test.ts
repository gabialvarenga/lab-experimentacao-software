import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { obterLicenca } from "../src/metrics/rq09-licenca.js";

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

describe("obterLicenca (RQ09)", () => {
  it("retorna o nome da licença do repositório", () => {
    const repo = repoFixture({ licenseInfo: { name: "Apache License 2.0" } });

    expect(obterLicenca(repo)).toBe("Apache License 2.0");
  });

  it('retorna "Não informado" quando o repositório não tem licença detectada', () => {
    const repo = repoFixture({ licenseInfo: null });

    expect(obterLicenca(repo)).toBe("Não informado");
  });
});
