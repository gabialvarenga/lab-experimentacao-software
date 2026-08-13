import { fetchRepositoryByName } from "../src/graphql/repositoryQuery.js";
import { calcularTotalForks } from "../src/metrics/rq08-forks.js";

const AMOSTRA = [
  "torvalds/linux",
  "microsoft/vscode",
  "facebook/react",
  "rust-lang/rust",
  "tensorflow/tensorflow",
  "sveltejs/svelte",
  "preactjs/preact",
];

async function main() {
  for (const nomeCompleto of AMOSTRA) {
    const repo = await fetchRepositoryByName(nomeCompleto);
    const forks = calcularTotalForks(repo);

    console.log(`${repo.nameWithOwner} — forks: ${forks}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
