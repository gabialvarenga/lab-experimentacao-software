import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function obterLinguagemPrimaria(repo: RawRepository): string {
  return repo.primaryLanguage?.name ?? "Não informado";
}

export const rq05Linguagem: MetricStrategy = {
  chave: "linguagem",
  calcular: obterLinguagemPrimaria,
};
