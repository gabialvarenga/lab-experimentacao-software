import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function calcularPrsAceitas(repo: RawRepository): number {
  return repo.pullRequests.totalCount;
}

export const rq02Prs: MetricStrategy = {
  chave: "prs_aceitas",
  calcular: calcularPrsAceitas,
};
