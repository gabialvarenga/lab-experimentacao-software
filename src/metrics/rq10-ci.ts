import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function possuiCiCd(repo: RawRepository): boolean {
  return (repo.workflowsDir?.entries?.length ?? 0) > 0;
}

export const rq10Ci: MetricStrategy = {
  chave: "possui_ci_cd",
  calcular: possuiCiCd,
};
