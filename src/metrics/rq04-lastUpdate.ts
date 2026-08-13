import type { RawRepository } from "../graphql/repositoryQuery.js";

const MS_PER_DAY = 1000 * 60 * 60 * 24;

export function getDaysSinceLastUpdate(
  repo: RawRepository,
  now: Date = new Date(),
): number {
  const pushedAt = new Date(repo.pushedAt);
  return Math.floor((now.getTime() - pushedAt.getTime()) / MS_PER_DAY);
}
