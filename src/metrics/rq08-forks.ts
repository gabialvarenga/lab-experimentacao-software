import type { RawRepository } from "../graphql/repositoryQuery.js";

export function calcularTotalForks(repo: RawRepository): number {
  return repo.forkCount;
}
