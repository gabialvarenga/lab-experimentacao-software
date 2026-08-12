import type { RawRepository } from "../graphql/repositoryQuery.js";

export function obterLinguagemPrimaria(repo: RawRepository): string {
  return repo.primaryLanguage?.name ?? "Não informado";
}
