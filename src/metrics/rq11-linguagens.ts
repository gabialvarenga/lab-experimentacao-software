import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function contarLinguagens(repo: RawRepository): number {
  return repo.languages.totalCount;
}

export const rq11Linguagens: MetricStrategy = {
  chave: "total_linguagens",
  calcular: contarLinguagens,
};
