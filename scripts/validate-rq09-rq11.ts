import { fetchRepositoryByName } from "../src/graphql/repositoryQuery.js";
import { obterLicenca } from "../src/metrics/rq09-licenca.js";
import { possuiCiCd } from "../src/metrics/rq10-ci.js";
import { contarLinguagens } from "../src/metrics/rq11-linguagens.js";

const AMOSTRA = [
  "torvalds/linux",
  "microsoft/vscode",
  "rust-lang/rust",
  "tensorflow/tensorflow",
  "sveltejs/svelte",
  "preactjs/preact",
];

async function main() {
  for (const nomeCompleto of AMOSTRA) {
    const repo = await fetchRepositoryByName(nomeCompleto);
    const licenca = obterLicenca(repo);
    const ciCd = possuiCiCd(repo);
    const linguagens = contarLinguagens(repo);

    console.log(
      `${repo.nameWithOwner} — licença: ${licenca} — CI/CD: ${ciCd} — linguagens: ${linguagens}`,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
