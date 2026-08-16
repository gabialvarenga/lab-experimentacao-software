import { writeFile } from "node:fs/promises";
import { toCsv } from "./csv/writer.js";
import { fetchTopRepositoriesByStars } from "./graphql/reposQuery.js";
import { calcularIdadeAnos } from "./metrics/rq01-idade.js";
import { calcularPrsAceitas } from "./metrics/rq02-prs.js";
import { getTotalReleases } from "./metrics/rq03-releases.js";
import { getDaysSinceLastUpdate } from "./metrics/rq04-lastUpdate.js";
import { obterLinguagemPrimaria } from "./metrics/rq05-linguagem.js";
import { calcularRazaoIssuesFechadas } from "./metrics/rq06-issues.js";
import { calcularTotalForks } from "./metrics/rq08-forks.js";
import { obterLicenca } from "./metrics/rq09-licenca.js";
import { possuiCiCd } from "./metrics/rq10-ci.js";
import { contarLinguagens } from "./metrics/rq11-linguagens.js";

const LIMIT = 1000;
const OUTPUT_PATH = "data/repositories.csv";

async function main() {
  console.log(`Buscando os ${LIMIT} repositórios com mais estrelas...`);
  const repositorios = await fetchTopRepositoriesByStars(LIMIT);
  console.log(
    `${repositorios.length} repositórios recebidos. Calculando métricas...`,
  );

  const linhas = repositorios.map((repo) => ({
    nome: repo.nameWithOwner,
    idade_anos: calcularIdadeAnos(repo).toFixed(2),
    prs_aceitas: calcularPrsAceitas(repo),
    total_releases: getTotalReleases(repo),
    dias_desde_atualizacao: getDaysSinceLastUpdate(repo),
    linguagem: obterLinguagemPrimaria(repo),
    razao_issues_fechadas: calcularRazaoIssuesFechadas(repo).toFixed(4),
    total_forks: calcularTotalForks(repo),
    licenca: obterLicenca(repo),
    possui_ci_cd: possuiCiCd(repo),
    total_linguagens: contarLinguagens(repo),
  }));

  await writeFile(OUTPUT_PATH, toCsv(linhas), "utf-8");
  console.log(`CSV escrito em ${OUTPUT_PATH} (${linhas.length} linhas).`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
