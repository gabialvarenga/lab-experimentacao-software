import type { RawRepository } from "../graphql/repositoryQuery.js";

export function contarLinguagens(repo: RawRepository): number {
  return repo.languages.totalCount;
}
