import { githubGraphQL, sleep } from "./client.js";
import { REPO_FIELDS, type RawRepository } from "./repositoryQuery.js";

// A busca paginada do GitHub fica progressivamente mais lenta quanto mais
// fundo o cursor pagina — combinado com os campos aninhados do REPO_FIELDS
// (issues, licença, CI/CD, linguagens), isso estoura timeout de gateway (502)
// bem antes de chegar em 1000 repositórios. Por isso a busca roda em duas
// fases: (1) busca leve, só com nameWithOwner, que não sofre esse problema de
// profundidade (testado até offset 900 sem degradação); (2) enriquecimento
// com os campos completos via lookup direto em lote (repository(owner, name)
// com alias), que também não depende de profundidade — só do tamanho do lote.
const SEARCH_PAGE_SIZE = 100;
const ENRICH_BATCH_SIZE = 10;
const MIN_RATE_LIMIT_REMAINING = 50;
const DELAY_BETWEEN_REQUESTS_MS = 1000;

const SEARCH_QUERY_FILTER = "stars:>1";

interface RateLimitInfo {
  remaining: number;
  resetAt: string;
}

async function respeitarRateLimit(rateLimit: RateLimitInfo): Promise<void> {
  if (rateLimit.remaining >= MIN_RATE_LIMIT_REMAINING) {
    return;
  }

  const esperaMs = new Date(rateLimit.resetAt).getTime() - Date.now();
  if (esperaMs > 0) {
    console.warn(
      `Rate limit baixo (${rateLimit.remaining} restantes). Aguardando reset em ${Math.ceil(esperaMs / 1000)}s...`,
    );
    await sleep(esperaMs + 1000);
  }
}

const SEARCH_NAMES_QUERY = `
  query TopRepositoryNames($searchQuery: String!, $first: Int!, $after: String) {
    rateLimit {
      remaining
      resetAt
    }
    search(query: $searchQuery, type: REPOSITORY, first: $first, after: $after) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        ... on Repository {
          nameWithOwner
        }
      }
    }
  }
`;

interface SearchNamesResponse {
  rateLimit: RateLimitInfo;
  search: {
    pageInfo: { hasNextPage: boolean; endCursor: string | null };
    nodes: { nameWithOwner: string }[];
  };
}

async function fetchTopRepositoryNames(limit: number): Promise<string[]> {
  const nomes: string[] = [];
  let after: string | null = null;

  while (nomes.length < limit) {
    const restante = limit - nomes.length;
    const data: SearchNamesResponse = await githubGraphQL<SearchNamesResponse>(
      SEARCH_NAMES_QUERY,
      {
        searchQuery: SEARCH_QUERY_FILTER,
        first: Math.min(SEARCH_PAGE_SIZE, restante),
        after,
      },
    );

    nomes.push(...data.search.nodes.map((node) => node.nameWithOwner));
    console.log(
      `Busca: ${nomes.length}/${limit} nomes (rate limit restante: ${data.rateLimit.remaining}).`,
    );

    await respeitarRateLimit(data.rateLimit);

    if (!data.search.pageInfo.hasNextPage) {
      break;
    }
    after = data.search.pageInfo.endCursor;
    await sleep(DELAY_BETWEEN_REQUESTS_MS);
  }

  return nomes;
}

function montarQueryEnriquecimento(nomes: string[]): string {
  const campos = nomes
    .map((nomeCompleto, indice) => {
      const [owner, name] = nomeCompleto.split("/");
      return `r${indice}: repository(owner: ${JSON.stringify(owner)}, name: ${JSON.stringify(name)}) {
        ${REPO_FIELDS}
      }`;
    })
    .join("\n");

  return `query {
    rateLimit {
      remaining
      resetAt
    }
    ${campos}
  }`;
}

type EnrichResponse = Record<string, RawRepository | null> & {
  rateLimit: RateLimitInfo;
};

async function fetchRepositoriesByNames(
  nomes: string[],
): Promise<RawRepository[]> {
  const repositorios: RawRepository[] = [];

  for (let inicio = 0; inicio < nomes.length; inicio += ENRICH_BATCH_SIZE) {
    const lote = nomes.slice(inicio, inicio + ENRICH_BATCH_SIZE);
    const { rateLimit, ...repos } = await githubGraphQL<EnrichResponse>(
      montarQueryEnriquecimento(lote),
    );

    for (const repo of Object.values(repos)) {
      if (repo) {
        repositorios.push(repo);
      }
    }

    console.log(
      `Enriquecimento: ${repositorios.length}/${nomes.length} repositórios (rate limit restante: ${rateLimit.remaining}).`,
    );

    await respeitarRateLimit(rateLimit);

    if (inicio + ENRICH_BATCH_SIZE < nomes.length) {
      await sleep(DELAY_BETWEEN_REQUESTS_MS);
    }
  }

  return repositorios;
}

export async function fetchTopRepositoriesByStars(
  limit: number,
): Promise<RawRepository[]> {
  const nomes = await fetchTopRepositoryNames(limit);
  console.log(`Nomes coletados: ${nomes.length}. Buscando detalhes completos...`);
  return fetchRepositoriesByNames(nomes);
}
