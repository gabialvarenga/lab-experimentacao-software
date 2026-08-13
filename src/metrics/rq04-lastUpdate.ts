import type { RepositorySampleResult } from "../graphql/sampleRepositories.js";

const MS_PER_DAY = 1000 * 60 * 60 * 24;

export function getDaysSinceLastUpdate(
  repository: Pick<RepositorySampleResult, "pushedAt">,
  now: Date = new Date()
): number {
  const pushedAt = new Date(repository.pushedAt);
  return Math.floor((now.getTime() - pushedAt.getTime()) / MS_PER_DAY);
}
