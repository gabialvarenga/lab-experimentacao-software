import { githubGraphQL } from "./client.js";

export const REPO_FIELDS = `
  nameWithOwner
  createdAt
  pushedAt
  pullRequests(states: MERGED) {
    totalCount
  }
  releases {
    totalCount
  }
  primaryLanguage {
    name
  }
  totalIssues: issues {
    totalCount
  }
  closedIssues: issues(states: CLOSED) {
    totalCount
  }
  forkCount
  stargazerCount
  licenseInfo {
    name
  }
  languages {
    totalCount
  }
  workflowsDir: object(expression: "HEAD:.github/workflows") {
    ... on Tree {
      entries {
        name
      }
    }
  }
`;

export interface RawRepository {
  nameWithOwner: string;
  createdAt: string;
  pushedAt: string;
  pullRequests: { totalCount: number };
  releases: { totalCount: number };
  primaryLanguage: { name: string } | null;
  totalIssues: { totalCount: number };
  closedIssues: { totalCount: number };
  forkCount: number;
  stargazerCount: number;
  licenseInfo: { name: string } | null;
  languages: { totalCount: number };
  workflowsDir: { entries: { name: string }[] } | null;
}

interface RepositoryResponse {
  repository: RawRepository | null;
}

const REPOSITORY_QUERY = `
  query Repository($owner: String!, $name: String!) {
    repository(owner: $owner, name: $name) {
      ${REPO_FIELDS}
    }
  }
`;

export async function fetchRepository(
  owner: string,
  name: string,
): Promise<RawRepository> {
  const data = await githubGraphQL<RepositoryResponse>(REPOSITORY_QUERY, {
    owner,
    name,
  });

  if (!data.repository) {
    throw new Error(`Repositório "${owner}/${name}" não encontrado.`);
  }

  return data.repository;
}

export async function fetchRepositoryByName(
  ownerAndName: string,
): Promise<RawRepository> {
  const [owner, name] = ownerAndName.split("/");
  if (!owner || !name) {
    throw new Error(
      `Formato inválido "${ownerAndName}", esperado "owner/nome".`,
    );
  }

  return fetchRepository(owner, name);
}