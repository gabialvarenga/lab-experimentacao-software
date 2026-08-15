import type { RawRepository } from "../graphql/repositoryQuery.js";

export function obterLicenca(repo: RawRepository): string {
  return repo.licenseInfo?.name ?? "Não informado";
}
