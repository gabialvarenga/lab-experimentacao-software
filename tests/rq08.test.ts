import { describe, expect, it } from "vitest";
import type { RawRepository } from "../src/graphql/repositoryQuery.js";
import { calcularTotalForks } from "../src/metrics/rq08-forks.js";

function repoFixture(overrides: Partial<RawRepository> = {}): RawRepository {
  return {
    nameWithOwner: "exemplo/repo",
    forkCount: 0,
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
