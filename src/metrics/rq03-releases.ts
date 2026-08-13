import type { RepositorySampleResult } from "../graphql/sampleRepositories.js";

export function getTotalReleases(
  repository: Pick<RepositorySampleResult, "totalReleases">
): number {
  return repository.totalReleases;
}
