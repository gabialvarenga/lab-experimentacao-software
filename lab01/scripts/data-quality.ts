import { readFile, writeFile } from "node:fs/promises";
import { parseCsv } from "../src/csv/reader.js";
import {
  paraNumeroOuNulo,
  resumoNumerico,
  resumoCategorico,
  resumoBooleano,
  type ResumoNumerico,
  type ResumoCategorico,
  type ResumoBooleano,
} from "../src/stats/descriptive.js";

const CSV_PATH = "data/repositories.csv";
const RELATORIO_PATH = "data/data-quality-report.md";

type Coluna =
  | { rq: string; label: string; coluna: string; tipo: "numerica" }
  | { rq: string; label: string; coluna: string; tipo: "categorica"; ausente: string }
  | { rq: string; label: string; coluna: string; tipo: "booleana" };

const COLUNAS: Coluna[] = [
  { rq: "RQ01", label: "Idade (anos)", coluna: "idade_anos", tipo: "numerica" },
  { rq: "RQ02", label: "PRs aceitas", coluna: "prs_aceitas", tipo: "numerica" },
  { rq: "RQ03", label: "Total de releases", coluna: "total_releases", tipo: "numerica" },
  {
    rq: "RQ04",
    label: "Dias desde a última atualização",
    coluna: "dias_desde_atualizacao",
    tipo: "numerica",
  },
  {
    rq: "RQ05",
    label: "Linguagem primária",
    coluna: "linguagem",
    tipo: "categorica",
    ausente: "Não informado",
  },
  { rq: "RQ06", label: "Razão de issues fechadas", coluna: "razao_issues_fechadas", tipo: "numerica" },
  { rq: "RQ08 (bônus)", label: "Total de forks", coluna: "total_forks", tipo: "numerica" },
  { rq: "RQ08 (bônus)", label: "Total de estrelas", coluna: "total_estrelas", tipo: "numerica" },
  { rq: "RQ08 (bônus)", label: "Razão fork/estrela", coluna: "razao_fork_estrela", tipo: "numerica" },
  {
    rq: "RQ09 (extra)",
    label: "Licença",
    coluna: "licenca",
    tipo: "categorica",
    ausente: "Não informado",
  },
  { rq: "RQ10 (extra)", label: "Possui CI/CD", coluna: "possui_ci_cd", tipo: "booleana" },
  { rq: "RQ11 (extra)", label: "Total de linguagens", coluna: "total_linguagens", tipo: "numerica" },
];

type Resultado =
  | { coluna: Coluna & { tipo: "numerica" }; resumo: ResumoNumerico }
  | { coluna: Coluna & { tipo: "categorica" }; resumo: ResumoCategorico }
  | { coluna: Coluna & { tipo: "booleana" }; resumo: ResumoBooleano };

function analisarColuna(coluna: Coluna, registros: Record<string, string>[]): Resultado {
  const valores = registros.map((registro) => registro[coluna.coluna] ?? "");

  if (coluna.tipo === "numerica") {
    const numeros = valores.map(paraNumeroOuNulo);
    return { coluna, resumo: resumoNumerico(numeros) };
  }

  if (coluna.tipo === "categorica") {
    return { coluna, resumo: resumoCategorico(valores, coluna.ausente) };
  }

  return { coluna, resumo: resumoBooleano(valores) };
}

function imprimirConsole(resultado: Resultado): void {
  const { coluna, resumo } = resultado;
  console.log(`\n${coluna.rq} — ${coluna.label} (${coluna.coluna})`);

  if (coluna.tipo === "numerica") {
    const r = resumo as ResumoNumerico;
    console.log(
      `  min=${r.min} max=${r.max} mediana=${r.mediana.toFixed(2)} ` +
        `q1=${r.q1.toFixed(2)} q3=${r.q3.toFixed(2)} outliers=${r.outliers} ausentes=${r.ausentes}/${r.total}`,
    );
    return;
  }

  if (coluna.tipo === "categorica") {
    const r = resumo as ResumoCategorico;
    const top = r.topCategorias.map((c) => `${c.valor}: ${c.contagem}`).join(", ");
    console.log(`  top: ${top} | categorias únicas=${r.categoriasUnicas} ausentes=${r.ausentes}/${r.total}`);
    return;
  }

  const r = resumo as ResumoBooleano;
  console.log(`  true=${r.verdadeiro} false=${r.falso} ausentes=${r.ausentes}/${r.total}`);
}

function gerarMarkdown(resultados: Resultado[]): string {
  const linhas: string[] = [
    "# Relatório de qualidade de dados",
    "",
    `Gerado a partir de \`${CSV_PATH}\` — base para as hipóteses informais das Issues #9, #10 e #11.`,
    "",
  ];

  for (const resultado of resultados) {
    const { coluna, resumo } = resultado;
    linhas.push(`## ${coluna.rq} — ${coluna.label}`, "", `Coluna: \`${coluna.coluna}\``, "");

    if (coluna.tipo === "numerica") {
      const r = resumo as ResumoNumerico;
      linhas.push(
        "| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |",
        "|---|---|---|---|---|---|---|",
        `| ${r.min} | ${r.max} | ${r.mediana.toFixed(2)} | ${r.q1.toFixed(2)} | ${r.q3.toFixed(2)} | ${r.outliers} | ${r.ausentes}/${r.total} |`,
        "",
      );
      continue;
    }

    if (coluna.tipo === "categorica") {
      const r = resumo as ResumoCategorico;
      linhas.push("| Categoria | Contagem |", "|---|---|");
      for (const item of r.topCategorias) {
        linhas.push(`| ${item.valor} | ${item.contagem} |`);
      }
      const restantes = Math.max(r.categoriasUnicas - r.topCategorias.length, 0);
      if (restantes > 0) {
        linhas.push(`| *(demais ${restantes} categorias)* | — |`);
      }
      linhas.push(`| **Não informado** | ${r.ausentes} |`, "");
      continue;
    }

    const r = resumo as ResumoBooleano;
    linhas.push(
      "| Valor | Contagem |",
      "|---|---|",
      `| true | ${r.verdadeiro} |`,
      `| false | ${r.falso} |`,
      "",
    );
  }

  return linhas.join("\n") + "\n";
}

async function main() {
  const conteudo = await readFile(CSV_PATH, "utf-8");
  const registros = parseCsv(conteudo);

  console.log(`Analisando ${registros.length} repositórios de ${CSV_PATH}...`);

  const resultados = COLUNAS.map((coluna) => analisarColuna(coluna, registros));
  resultados.forEach(imprimirConsole);

  const markdown = gerarMarkdown(resultados);
  await writeFile(RELATORIO_PATH, markdown, "utf-8");
  console.log(`\nRelatório gravado em ${RELATORIO_PATH}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
