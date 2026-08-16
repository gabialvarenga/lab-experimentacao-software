import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function obterLicenca(repo: RawRepository): string {
  return repo.licenseInfo?.name ?? "Não informado";
}

export const rq09Licenca: MetricStrategy = {
  chave: "licenca",
  calcular: obterLicenca,
};
