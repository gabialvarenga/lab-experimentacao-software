import { fetchRepositoryByName } from "../src/graphql/repositoryQuery.js";
import { calcularIdadeAnos } from "../src/metrics/rq01-idade.js";
import { calcularPrsAceitas } from "../src/metrics/rq02-prs.js";

const AMOSTRA = [
  "torvalds/linux",
  "vuejs/vue",
  "axios/axios",
  "preactjs/preact",
  "sveltejs/svelte",
];

async function main() {
  for (const nomeCompleto of AMOSTRA) {
    const repo = await fetchRepositoryByName(nomeCompleto);
    const idade = calcularIdadeAnos(repo);
    const prs = calcularPrsAceitas(repo);

    console.log(
      `${repo.nameWithOwner} — criado em ${repo.createdAt} — idade: ${idade.toFixed(1)} anos — PRs aceitas: ${prs}`,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
