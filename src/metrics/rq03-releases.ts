import type { RawRepository } from "../graphql/repositoryQuery.js";

export function getTotalReleases(repo: RawRepository): number {
  return repo.releases.totalCount;
}
