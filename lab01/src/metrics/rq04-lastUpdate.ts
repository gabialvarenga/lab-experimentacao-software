import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

const MS_PER_DAY = 1000 * 60 * 60 * 24;

export function getDaysSinceLastUpdate(
  repo: RawRepository,
  now: Date = new Date(),
): number {
  const pushedAt = new Date(repo.pushedAt);
  return Math.floor((now.getTime() - pushedAt.getTime()) / MS_PER_DAY);
}

export const rq04UltimaAtualizacao: MetricStrategy = {
  chave: "dias_desde_atualizacao",
  calcular: (repo) => getDaysSinceLastUpdate(repo),
};
