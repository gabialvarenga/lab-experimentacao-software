export function mediana(valores: number[]): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  if (ordenados.length % 2 === 0) {
    return (ordenados[meio - 1] + ordenados[meio]) / 2;
  }
  return ordenados[meio];
}

function percentil(ordenados: number[], p: number): number {
  const indice = p * (ordenados.length - 1);
  const inferior = Math.floor(indice);
  const superior = Math.ceil(indice);
  if (inferior === superior) {
    return ordenados[inferior];
  }
  const fracao = indice - inferior;
  return ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * fracao;
}

export function quartis(valores: number[]): { q1: number; q3: number } {
  const ordenados = [...valores].sort((a, b) => a - b);
  return {
    q1: percentil(ordenados, 0.25),
    q3: percentil(ordenados, 0.75),
  };
}

export function detectarOutliers(valores: number[]): {
  contagem: number;
  limiteInferior: number;
  limiteSuperior: number;
} {
  const { q1, q3 } = quartis(valores);
  const iqr = q3 - q1;
  const limiteInferior = q1 - 1.5 * iqr;
  const limiteSuperior = q3 + 1.5 * iqr;
  const contagem = valores.filter((valor) => valor < limiteInferior || valor > limiteSuperior).length;

  return { contagem, limiteInferior, limiteSuperior };
}

export function paraNumeroOuNulo(valor: string): number | null {
  if (valor.trim() === "") {
    return null;
  }
  const numero = Number(valor);
  return Number.isNaN(numero) ? null : numero;
}

export interface ResumoNumerico {
  min: number;
  max: number;
  mediana: number;
  q1: number;
  q3: number;
  outliers: number;
  ausentes: number;
  total: number;
}

export function resumoNumerico(valoresBrutos: (number | null)[]): ResumoNumerico {
  const ausentes = valoresBrutos.filter((valor) => valor === null).length;
  const valores = valoresBrutos.filter((valor): valor is number => valor !== null);

  if (valores.length === 0) {
    return {
      min: NaN,
      max: NaN,
      mediana: NaN,
      q1: NaN,
      q3: NaN,
      outliers: 0,
      ausentes,
      total: valoresBrutos.length,
    };
  }

  const { q1, q3 } = quartis(valores);
  const { contagem: outliers } = detectarOutliers(valores);

  return {
    min: Math.min(...valores),
    max: Math.max(...valores),
    mediana: mediana(valores),
    q1,
    q3,
    outliers,
    ausentes,
    total: valoresBrutos.length,
  };
}

export interface CategoriaContagem {
  valor: string;
  contagem: number;
}

export interface ResumoCategorico {
  topCategorias: CategoriaContagem[];
  ausentes: number;
  categoriasUnicas: number;
  total: number;
}

export function resumoCategorico(
  valores: string[],
  valorAusente: string,
  topN = 5,
): ResumoCategorico {
  const contagens = new Map<string, number>();
  let ausentes = 0;

  for (const valor of valores) {
    if (valor === valorAusente) {
      ausentes++;
      continue;
    }
    contagens.set(valor, (contagens.get(valor) ?? 0) + 1);
  }

  const topCategorias = [...contagens.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([valor, contagem]) => ({ valor, contagem }));

  return {
    topCategorias,
    ausentes,
    categoriasUnicas: contagens.size,
    total: valores.length,
  };
}

export interface ResumoBooleano {
  verdadeiro: number;
  falso: number;
  ausentes: number;
  total: number;
}

export function resumoBooleano(valores: string[]): ResumoBooleano {
  let verdadeiro = 0;
  let falso = 0;
  let ausentes = 0;

  for (const valor of valores) {
    if (valor === "true") {
      verdadeiro++;
    } else if (valor === "false") {
      falso++;
    } else {
      ausentes++;
    }
  }

  return { verdadeiro, falso, ausentes, total: valores.length };
}
