import { fetchRepository } from "../src/graphql/repositoryQuery.js";
import { obterLinguagemPrimaria } from "../src/metrics/rq05-linguagem.js";
import { calcularRazaoIssuesFechadas } from "../src/metrics/rq06-issues.js";

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
    const [owner, name] = nomeCompleto.split("/");
    const repo = await fetchRepository(owner, name);

    const linguagem = obterLinguagemPrimaria(repo);
    const razaoFechadas = calcularRazaoIssuesFechadas(repo);

    console.log(
      `${repo.nameWithOwner} — linguagem: ${linguagem} — issues: ` +
        `${repo.closedIssues.totalCount}/${repo.totalIssues.totalCount} fechadas ` +
        `(${(razaoFechadas * 100).toFixed(1)}%)`,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
