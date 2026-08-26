const GITHUB_GRAPHQL_URL = "https://api.github.com/graphql";

interface GraphQLError {
  message: string;
}

interface GraphQLResponse<T> {
  data?: T;
  errors?: GraphQLError[];
}

const RETRYABLE_STATUS_CODES = new Set([502, 503, 504]);
const RATE_LIMIT_STATUS_CODES = new Set([403, 429]);
const MAX_ATTEMPTS = 4;
const RETRY_DELAY_MS = 2000;

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function requestOnce<T>(
  query: string,
  variables: Record<string, unknown> | undefined,
  token: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(GITHUB_GRAPHQL_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, variables }),
    });
  } catch (causa) {
    const error = new Error(
      `Falha de rede ao chamar a API do GitHub: ${(causa as Error).message}`,
    );
    (error as Error & { isNetworkError?: boolean }).isNetworkError = true;
    throw error;
  }

  if (!response.ok) {
    const error = new Error(
      `GitHub GraphQL respondeu ${response.status}: ${await response.text()}`,
    );
    (error as Error & { status?: number }).status = response.status;

    const retryAfter = response.headers.get("retry-after");
    if (retryAfter) {
      (error as Error & { retryAfterSeconds?: number }).retryAfterSeconds =
        Number(retryAfter);
    }

    throw error;
  }

  const result = (await response.json()) as GraphQLResponse<T>;

  if (result.errors?.length) {
    throw new Error(
      `Erros do GraphQL: ${result.errors.map((error) => error.message).join("; ")}`,
    );
  }

  if (!result.data) {
    throw new Error("Resposta do GraphQL sem 'data'.");
  }

  return result.data;
}

export async function githubGraphQL<T>(
  query: string,
  variables?: Record<string, unknown>,
): Promise<T> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error(
      "GITHUB_TOKEN não definido. Crie um .env a partir do .env.example.",
    );
  }

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      return await requestOnce<T>(query, variables, token);
    } catch (error) {
      const status = (error as Error & { status?: number }).status;
      const retryAfterSeconds = (
        error as Error & { retryAfterSeconds?: number }
      ).retryAfterSeconds;

      const isNetworkError =
        (error as Error & { isNetworkError?: boolean }).isNetworkError ===
        true;
      const isTransient =
        status !== undefined && RETRYABLE_STATUS_CODES.has(status);
      const isRateLimited =
        status !== undefined &&
        RATE_LIMIT_STATUS_CODES.has(status) &&
        retryAfterSeconds !== undefined;

      if (
        (!isNetworkError && !isTransient && !isRateLimited) ||
        attempt === MAX_ATTEMPTS
      ) {
        throw error;
      }

      const delayMs = isRateLimited
        ? retryAfterSeconds * 1000
        : RETRY_DELAY_MS * attempt;

      const motivo = isNetworkError ? "falha de rede" : `status ${status}`;
      console.warn(
        `Tentativa ${attempt}/${MAX_ATTEMPTS} falhou (${motivo}), tentando de novo em ${delayMs}ms...`,
      );
      await sleep(delayMs);
    }
  }

  throw new Error("Número máximo de tentativas excedido.");
}
