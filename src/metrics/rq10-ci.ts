import type { RawRepository } from "../graphql/repositoryQuery.js";

export function possuiCiCd(repo: RawRepository): boolean {
  return (repo.workflowsDir?.entries?.length ?? 0) > 0;
}
