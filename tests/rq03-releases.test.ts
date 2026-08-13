import { beforeAll, describe, expect, it } from "vitest";
import {
  fetchSampleRepositories,
  type RepositorySampleResult,
} from "../src/graphql/sampleRepositories.js";
import { getTotalReleases } from "../src/metrics/rq03-releases.js";

describe("RQ03 - total de releases", () => {
  let repositories: RepositorySampleResult[];

  beforeAll(async () => {
    repositories = await fetchSampleRepositories();
  }, 30_000);

  it("retorna um número não negativo de releases para cada repositório da amostra", () => {
    for (const repository of repositories) {
      expect(getTotalReleases(repository)).toBeGreaterThanOrEqual(0);
    }
  });

  it("identifica repositórios sem uso relevante de GitHub Releases", () => {
    const awesome = repositories.find(
      (repository) =>
        repository.requestedOwner === "sindresorhus" && repository.requestedName === "awesome"
    );
    expect(awesome).toBeDefined();
    expect(getTotalReleases(awesome!)).toBeLessThanOrEqual(3);
  });

  it("identifica repositórios com releases frequentes", () => {
    const vscode = repositories.find(
      (repository) =>
        repository.requestedOwner === "microsoft" && repository.requestedName === "vscode"
    );
    expect(vscode).toBeDefined();
    expect(getTotalReleases(vscode!)).toBeGreaterThan(20);
  });
});
