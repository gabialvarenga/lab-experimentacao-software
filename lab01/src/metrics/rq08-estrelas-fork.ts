import type { RawRepository } from "../graphql/repositoryQuery.js";
import type { MetricStrategy } from "./types.js";

export function contarEstrelas(repo: RawRepository): number {
  return repo.stargazerCount;
}

export function calcularRazaoForkEstrela(repo: RawRepository): number {
  if (repo.stargazerCount === 0) {
    return 0;
  }
  return repo.forkCount / repo.stargazerCount;
}

export const rq08Estrelas: MetricStrategy = {
  chave: "total_estrelas",
  calcular: contarEstrelas,
};

export const rq08RazaoForkEstrela: MetricStrategy = {
  chave: "razao_fork_estrela",
  calcular: calcularRazaoForkEstrela,
};
