import { githubGraphQL } from "./client.js";

export const REPO_FIELDS = `
  nameWithOwner
  createdAt
  pullRequests(states: MERGED) {
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
`;

export interface RawRepository {
  nameWithOwner: string;
  createdAt: string;
  pullRequests: { totalCount: number };
  primaryLanguage: { name: string } | null;
  totalIssues: { totalCount: number };
  closedIssues: { totalCount: number };
  forkCount: number;
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