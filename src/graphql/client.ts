const GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql";

interface GraphQLResponse<T> {
  data?: T;
  errors?: Array<{ message: string }>;
}

export async function githubGraphQL<T>(query: string): Promise<T> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error(
      "GITHUB_TOKEN não definido. Configure o arquivo .env a partir de .env.example."
    );
  }

  const response = await fetch(GITHUB_GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(
      `GitHub GraphQL request failed: ${response.status} ${response.statusText}`
    );
  }

  const body = (await response.json()) as GraphQLResponse<T>;

  if (body.errors?.length) {
    throw new Error(
      `GitHub GraphQL error: ${body.errors.map((error) => error.message).join("; ")}`
    );
  }

  if (!body.data) {
    throw new Error("GitHub GraphQL response missing data.");
  }

  return body.data;
}
