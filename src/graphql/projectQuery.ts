import { githubGraphQL } from "./client.js";

const PROJECT_OWNER = "gabialvarenga";
const PROJECT_NUMBER = 9;
const PAGE_SIZE = 20;

export interface ProjectItem {
  numero: number | null;
  titulo: string;
  tipo: string;
  status: string;
  url: string | null;
}

interface IssueOrPrContent {
  __typename: "Issue" | "PullRequest";
  number: number;
  title: string;
  url: string;
}

interface DraftIssueContent {
  __typename: "DraftIssue";
  title: string;
}

interface RawProjectItem {
  content: IssueOrPrContent | DraftIssueContent | null;
  fieldValueByName: { name: string } | null;
}

interface ProjectItemsResponse {
  user: {
    projectV2: {
      items: {
        pageInfo: { hasNextPage: boolean; endCursor: string | null };
        nodes: RawProjectItem[];
      };
    } | null;
  } | null;
}

const PROJECT_ITEMS_QUERY = `
  query ProjectItems($login: String!, $projectNumber: Int!, $first: Int!, $after: String) {
    user(login: $login) {
      projectV2(number: $projectNumber) {
        items(first: $first, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            content {
              __typename
              ... on Issue {
                number
                title
                url
              }
              ... on PullRequest {
                number
                title
                url
              }
              ... on DraftIssue {
                title
              }
            }
            fieldValueByName(name: "Status") {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
              }
            }
          }
        }
      }
    }
  }
`;

export function parseProjectItem(node: RawProjectItem): ProjectItem {
  const content = node.content;
  const ehIssueOuPr =
    content?.__typename === "Issue" || content?.__typename === "PullRequest";

  return {
    numero: ehIssueOuPr ? (content as IssueOrPrContent).number : null,
    titulo: content?.title ?? "(sem título)",
    tipo: content?.__typename ?? "Desconhecido",
    status: node.fieldValueByName?.name ?? "Sem status",
    url: ehIssueOuPr ? (content as IssueOrPrContent).url : null,
  };
}

export async function fetchProjectItems(): Promise<ProjectItem[]> {
  const itens: ProjectItem[] = [];
  let after: string | null = null;

  while (true) {
    const data: ProjectItemsResponse =
      await githubGraphQL<ProjectItemsResponse>(PROJECT_ITEMS_QUERY, {
        login: PROJECT_OWNER,
        projectNumber: PROJECT_NUMBER,
        first: PAGE_SIZE,
        after,
      });

    if (!data.user) {
      throw new Error(`Usuário "${PROJECT_OWNER}" não encontrado.`);
    }
    if (!data.user.projectV2) {
      throw new Error(
        `Project #${PROJECT_NUMBER} não encontrado ou sem acesso. Confira se o GITHUB_TOKEN tem permissão de leitura de Projects (escopo "read:project" ou "project").`,
      );
    }

    const { nodes, pageInfo } = data.user.projectV2.items;
    itens.push(...nodes.map(parseProjectItem));

    if (!pageInfo.hasNextPage) {
      break;
    }
    after = pageInfo.endCursor;
  }

  return itens;
}
