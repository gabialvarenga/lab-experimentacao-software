import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function getTotalReleases(repo: RawRepository): number {
  return repo.releases.totalCount;
}

export const rq03Releases: MetricStrategy = {
  chave: "total_releases",
  calcular: getTotalReleases,
};
