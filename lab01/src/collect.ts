import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { toCsv } from "./csv/writer.js";
import type { RawRepository } from "./graphql/repositoryQuery.js";
import { fetchTopRepositoriesByStars } from "./graphql/reposQuery.js";
import { rq01Idade } from "./metrics/rq01-idade.js";
import { rq02Prs } from "./metrics/rq02-prs.js";
import { rq03Releases } from "./metrics/rq03-releases.js";
import { rq04UltimaAtualizacao } from "./metrics/rq04-lastUpdate.js";
import { rq05Linguagem } from "./metrics/rq05-linguagem.js";
import { rq06RazaoIssuesFechadas } from "./metrics/rq06-issues.js";
import { rq08Forks } from "./metrics/rq08-forks.js";
import {
  rq08Estrelas,
  rq08RazaoForkEstrela,
} from "./metrics/rq08-estrelas-fork.js";
import { rq09Licenca } from "./metrics/rq09-licenca.js";
import { rq10Ci } from "./metrics/rq10-ci.js";
import { rq11Linguagens } from "./metrics/rq11-linguagens.js";
import type { MetricStrategy } from "./metrics/types.js";

const LIMIT = 1000;
const OUTPUT_PATH = "data/repositories.csv";

export const METRICAS: MetricStrategy[] = [
  rq01Idade,
  rq02Prs,
  rq03Releases,
  rq04UltimaAtualizacao,
  rq05Linguagem,
  rq06RazaoIssuesFechadas,
  rq08Forks,
  rq08Estrelas,
  rq08RazaoForkEstrela,
  rq09Licenca,
  rq10Ci,
  rq11Linguagens,
];

export function calcularLinha(
  repo: RawRepository,
  metricas: MetricStrategy[] = METRICAS,
): Record<string, unknown> {
  const linha: Record<string, unknown> = { nome: repo.nameWithOwner };
  for (const metrica of metricas) {
    linha[metrica.chave] = metrica.calcular(repo);
  }
  return linha;
}

async function main() {
  console.log(`Buscando os ${LIMIT} repositórios com mais estrelas...`);
  const repositorios = await fetchTopRepositoriesByStars(LIMIT);
  console.log(
    `${repositorios.length} repositórios recebidos. Calculando métricas...`,
  );

  const linhas = repositorios.map((repo) => calcularLinha(repo));

  await writeFile(OUTPUT_PATH, toCsv(linhas), "utf-8");
  console.log(`CSV escrito em ${OUTPUT_PATH} (${linhas.length} linhas).`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
