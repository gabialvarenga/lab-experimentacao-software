import type { RawRepository } from "../graphql/repositoryQuery.js";

export interface MetricStrategy {
  chave: string;
  calcular: (repo: RawRepository) => string | number | boolean;
}
