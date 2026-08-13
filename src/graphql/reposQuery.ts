import { githubGraphQL } from "./client.js";
import { REPO_FIELDS, type RawRepository } from "./repositoryQuery.js";

const PAGE_SIZE = 10;

const SEARCH_QUERY_FILTER = "stars:>1";

const TOP_REPOSITORIES_QUERY = `
  query TopRepositories($searchQuery: String!, $first: Int!, $after: String) {
    search(query: $searchQuery, type: REPOSITORY, first: $first, after: $after) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        ... on Repository {
          ${REPO_FIELDS}
        }
      }
    }
  }
`;

interface SearchResponse {
  search: {
    pageInfo: { hasNextPage: boolean; endCursor: string | null };
    nodes: RawRepository[];
  };
}

export async function fetchTopRepositoriesByStars(
  limit: number,
): Promise<RawRepository[]> {
  const repositories: RawRepository[] = [];
  let after: string | null = null;

  while (repositories.length < limit) {
    const remaining = limit - repositories.length;
    const data: SearchResponse = await githubGraphQL<SearchResponse>(TOP_REPOSITORIES_QUERY, {
      searchQuery: SEARCH_QUERY_FILTER,
      first: Math.min(PAGE_SIZE, remaining),
      after,
    });

    repositories.push(...data.search.nodes);

    if (!data.search.pageInfo.hasNextPage) {
      break;
    }
    after = data.search.pageInfo.endCursor;
  }

  return repositories;
}
