import { writeFile } from "node:fs/promises";
import { toCsv } from "./csv/writer.js";
import { fetchProjectItems } from "./graphql/projectQuery.js";

async function main() {
  const sprint = process.argv[2];
  if (!sprint) {
    throw new Error(
      'Informe o identificador da sprint. Uso: npm run snapshot -- <id>  (ex: npm run snapshot -- s01)',
    );
  }

  const outputPath = `data/snapshots/lab01-${sprint}.csv`;

  console.log("Buscando itens do GitHub Project...");
  const itens = await fetchProjectItems();
  console.log(`${itens.length} itens recebidos.`);

  const linhas = itens.map((item) => ({ ...item }));
  await writeFile(outputPath, toCsv(linhas), "utf-8");
  console.log(`Snapshot escrito em ${outputPath} (${itens.length} linhas).`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
