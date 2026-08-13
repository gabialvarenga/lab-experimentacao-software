import { beforeAll, describe, expect, it } from "vitest";
import {
  fetchSampleRepositories,
  type RepositorySampleResult,
} from "../src/graphql/sampleRepositories.js";
import { getDaysSinceLastUpdate } from "../src/metrics/rq04-lastUpdate.js";

describe("RQ04 - tempo até a última atualização", () => {
  let repositories: RepositorySampleResult[];

  beforeAll(async () => {
    repositories = await fetchSampleRepositories();
  }, 30_000);

  it("retorna um número não negativo de dias para cada repositório da amostra", () => {
    for (const repository of repositories) {
      expect(getDaysSinceLastUpdate(repository)).toBeGreaterThanOrEqual(0);
    }
  });

  it("identifica repositórios abandonados como desatualizados há muito tempo", () => {
    const abandoned = repositories.find(
      (repository) => repository.requestedOwner === "996icu" && repository.requestedName === "996.ICU"
    );
    expect(abandoned).toBeDefined();
    expect(getDaysSinceLastUpdate(abandoned!)).toBeGreaterThan(180);
  });

  it("identifica repositórios ativamente mantidos como atualizados recentemente", () => {
    const react = repositories.find(
      (repository) => repository.requestedOwner === "facebook" && repository.requestedName === "react"
    );
    expect(react).toBeDefined();
    expect(getDaysSinceLastUpdate(react!)).toBeLessThan(30);
  });

  it("um repositório abandonado está muito mais desatualizado que um ativo", () => {
    const abandoned = repositories.find(
      (repository) => repository.requestedOwner === "996icu" && repository.requestedName === "996.ICU"
    );
    const react = repositories.find(
      (repository) => repository.requestedOwner === "facebook" && repository.requestedName === "react"
    );
    expect(getDaysSinceLastUpdate(abandoned!)).toBeGreaterThan(
      getDaysSinceLastUpdate(react!)
    );
  });
});
