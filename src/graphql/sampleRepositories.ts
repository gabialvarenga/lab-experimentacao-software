import { githubGraphQL } from "./client.js";

export interface RepositorySample {
  owner: string;
  name: string;
}

export interface RepositorySampleResult {
  requestedOwner: string;
  requestedName: string;
  nameWithOwner: string;
  pushedAt: string;
  totalReleases: number;
}

interface RawRepository {
  nameWithOwner: string;
  pushedAt: string;
  releases: {
    totalCount: number;
  };
}

export const SAMPLE_REPOSITORIES: RepositorySample[] = [
  { owner: "facebook", name: "react" },
  { owner: "microsoft", name: "vscode" },
  { owner: "tensorflow", name: "tensorflow" },
  { owner: "freeCodeCamp", name: "freeCodeCamp" },
  { owner: "sindresorhus", name: "awesome" },
  { owner: "torvalds", name: "linux" },
  { owner: "996icu", name: "996.ICU" },
];

function repositoryFragment(alias: string, { owner, name }: RepositorySample): string {
  return `
    ${alias}: repository(owner: "${owner}", name: "${name}") {
      nameWithOwner
      pushedAt
      releases {
        totalCount
      }
    }
  `;
}

export async function fetchSampleRepositories(
  repositories: RepositorySample[] = SAMPLE_REPOSITORIES
): Promise<RepositorySampleResult[]> {
  const query = `
    query SampleRepositories {
      ${repositories.map((repo, index) => repositoryFragment(`r${index}`, repo)).join("\n")}
    }
  `;

  const data = await githubGraphQL<Record<string, RawRepository>>(query);

  return repositories.map((repo, index) => {
    const raw = data[`r${index}`];
    return {
      requestedOwner: repo.owner,
      requestedName: repo.name,
      nameWithOwner: raw.nameWithOwner,
      pushedAt: raw.pushedAt,
      totalReleases: raw.releases.totalCount,
    };
  });
}
