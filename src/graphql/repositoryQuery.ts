import { githubGraphQL } from "./client.js";

export const REPO_FIELDS_RQ08 = `
  nameWithOwner
  forkCount
`;

export interface RawRepository {
  nameWithOwner: string;
  forkCount: number;
}

interface RepositoryByNameResponse {
  repository: RawRepository | null;
}

const REPOSITORY_BY_NAME_QUERY = `
  query RepositoryByName($owner: String!, $name: String!) {
    repository(owner: $owner, name: $name) {
      ${REPO_FIELDS_RQ08}
    }
  }
`;

export async function fetchRepositoryByName(
  ownerAndName: string,
): Promise<RawRepository> {
  const [owner, name] = ownerAndName.split("/");
  if (!owner || !name) {
    throw new Error(
      `Formato inválido "${ownerAndName}", esperado "owner/nome".`,
    );
  }

  const data = await githubGraphQL<RepositoryByNameResponse>(
    REPOSITORY_BY_NAME_QUERY,
    { owner, name },
  );

  if (!data.repository) {
    throw new Error(`Repositório "${ownerAndName}" não encontrado.`);
  }

  return data.repository;
}
