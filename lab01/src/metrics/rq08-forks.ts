import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function calcularTotalForks(repo: RawRepository): number {
  return repo.forkCount;
}

export const rq08Forks: MetricStrategy = {
  chave: "total_forks",
  calcular: calcularTotalForks,
};
