import type { RawRepository } from "../graphql/repositoryQuery.js";

export function calcularRazaoIssuesFechadas(repo: RawRepository): number {
  const total = repo.totalIssues.totalCount;
  if (total === 0) {
    return 0;
  }
  return repo.closedIssues.totalCount / total;
}
