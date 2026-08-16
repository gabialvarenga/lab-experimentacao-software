import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function calcularRazaoIssuesFechadas(repo: RawRepository): number {
  const total = repo.totalIssues.totalCount;
  if (total === 0) {
    return 0;
  }
  return repo.closedIssues.totalCount / total;
}

export const rq06RazaoIssuesFechadas: MetricStrategy = {
  chave: "razao_issues_fechadas",
  calcular: (repo) => calcularRazaoIssuesFechadas(repo).toFixed(4),
};
