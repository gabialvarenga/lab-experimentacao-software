import { describe, expect, it } from "vitest";
import { parseProjectItem } from "../src/graphql/projectQuery.js";

describe("parseProjectItem", () => {
  it("extrai número, título, tipo, status e url de uma Issue", () => {
    const item = parseProjectItem({
      content: {
        __typename: "Issue",
        number: 13,
        title: "Script de snapshot do board",
        url: "https://github.com/gabialvarenga/lab-experimentacao-software/issues/13",
      },
      fieldValueByName: { name: "Doing" },
    });

    expect(item).toEqual({
      numero: 13,
      titulo: "Script de snapshot do board",
      tipo: "Issue",
      status: "Doing",
      url: "https://github.com/gabialvarenga/lab-experimentacao-software/issues/13",
    });
  });

  it("extrai número, título, tipo e url de uma Pull Request", () => {
    const item = parseProjectItem({
      content: {
        __typename: "PullRequest",
        number: 27,
        title: "#13 implementa script de snapshot",
        url: "https://github.com/gabialvarenga/lab-experimentacao-software/pull/27",
      },
      fieldValueByName: { name: "Review" },
    });

    expect(item.tipo).toBe("PullRequest");
    expect(item.numero).toBe(27);
    expect(item.status).toBe("Review");
  });

  it("trata DraftIssue sem número nem url", () => {
    const item = parseProjectItem({
      content: { __typename: "DraftIssue", title: "Ideia solta" },
      fieldValueByName: { name: "Backlog" },
    });

    expect(item.numero).toBeNull();
    expect(item.url).toBeNull();
    expect(item.tipo).toBe("DraftIssue");
  });

  it('usa "Sem status" quando o item não tem valor no campo Status', () => {
    const item = parseProjectItem({
      content: {
        __typename: "Issue",
        number: 1,
        title: "Exemplo",
        url: "https://github.com/exemplo",
      },
      fieldValueByName: null,
    });

    expect(item.status).toBe("Sem status");
  });

  it('usa "(sem título)" quando o item não tem content (ex: removido)', () => {
    const item = parseProjectItem({ content: null, fieldValueByName: null });

    expect(item.titulo).toBe("(sem título)");
    expect(item.tipo).toBe("Desconhecido");
  });
});
