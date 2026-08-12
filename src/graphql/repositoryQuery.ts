const GITHUB_GRAPHQL_URL = "https://api.github.com/graphql";

const REPOSITORY_QUERY = `
  query RepositoryLinguagemEIssues($owner: String!, $name: String!) {
    repository(owner: $owner, name: $name) {
      nameWithOwner
      primaryLanguage {
        name
      }
      totalIssues: issues {
        totalCount
      }
      closedIssues: issues(states: CLOSED) {
        totalCount
      }
    }
  }
`;

export interface RawRepository {
  nameWithOwner: string;
  primaryLanguage: { name: string } | null;
  totalIssues: { totalCount: number };
  closedIssues: { totalCount: number };
}

interface RepositoryQueryResponse {
  data?: {
    repository: RawRepository | null;
  };
  errors?: { message: string }[];
}

export async function fetchRepository(
  owner: string,
  name: string,
): Promise<RawRepository> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error(
      "GITHUB_TOKEN não definido. Crie um .env a partir do .env.example.",
    );
  }

  const response = await fetch(GITHUB_GRAPHQL_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: REPOSITORY_QUERY,
      variables: { owner, name },
    }),
  });

  if (!response.ok) {
    throw new Error(
      `GitHub GraphQL respondeu ${response.status}: ${await response.text()}`,
    );
  }

  const result = (await response.json()) as RepositoryQueryResponse;

  if (result.errors?.length) {
    throw new Error(
      `Erros do GraphQL: ${result.errors.map((error) => error.message).join("; ")}`,
    );
  }

  if (!result.data?.repository) {
    throw new Error(`Repositório "${owner}/${name}" não encontrado.`);
  }

  return result.data.repository;
}
