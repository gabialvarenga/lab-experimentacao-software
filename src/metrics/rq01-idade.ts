import type { RawRepository } from "../graphql/repositoryQuery.js";

const MS_POR_ANO = 1000 * 60 * 60 * 24 * 365.25;

export function calcularIdadeAnos(
  repo: RawRepository,
  dataReferencia: Date = new Date(),
): number {
  const criadoEm = new Date(repo.createdAt);
  const diferencaMs = dataReferencia.getTime() - criadoEm.getTime();
  return diferencaMs / MS_POR_ANO;
}
