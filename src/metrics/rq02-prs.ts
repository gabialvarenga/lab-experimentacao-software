import type { RawRepository } from "../graphql/repositoryQuery.js";

export function calcularPrsAceitas(repo: RawRepository): number {
  return repo.pullRequests.totalCount;
}
