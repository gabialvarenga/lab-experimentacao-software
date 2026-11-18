"""Executor do benchmark: plano de execuções, contêineres, cliente de carga e CSV bruto (S01-07).

Único módulo que comanda contêineres; a leitura das saídas fica em `leitura` e roda sem Docker,
inclusive no CI. Segue o procedimento de `docs/protocolo-execucao.md` (seção 6). Para cada
execução do plano:

1. sobe o servidor com o tratamento (`IO_THREADS`) e espera ficar pronto;
2. lê a versão (`INFO server`);
3. pré-carga das chaves, aquecimento (saída descartada) e medição (JSON gravado);
4. lê a memória (`INFO memory`) com o servidor ainda ligado;
5. para e remove o contêiner e espera a pausa.

Saídas, na pasta `saida` do config:

- `execucoes.csv`: uma linha por execução concluída, com as colunas congeladas em `COLUNAS`;
- `falhas.csv`: uma linha por tentativa que falhou (etapa e mensagem), sem valor inventado;
- `saidas/<execucao_id>.json`: a saída bruta do cliente;
- `registro-<data>.md`: o ambiente (módulo `ambiente`) e o resumo de cada sessão.

Retomada: o que já está em `execucoes.csv` não roda de novo. Uma execução que falhou não entra
no CSV e é tentada outra vez na próxima chamada.
"""

import csv
import itertools
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lab05 import ambiente, config, leitura

COLUNAS = [
    "execucao_id",
    "ordem",
    "servidor",
    "versao",
    "io_threads",
    "carga",
    "repeticao",
    "ops_s",
    "lat_p50_ms",
    "lat_p99_ms",
    "memoria_bytes",
    "inicio",
    "fim",
]
COLUNAS_FALHAS = ["execucao_id", "ordem", "servidor", "io_threads", "carga", "repeticao", "etapa", "erro", "inicio", "fim"]
FOLGA_CLIENTE_S = 120  # tempo além da duração da carga antes de desistir do cliente


class ErroExecucao(Exception):
    """Um comando do Docker falhou ou passou do tempo; a execução vira falha."""


class ErroPlano(Exception):
    """O CSV já gravado não corresponde ao plano do config; retomar misturaria planos."""


class Falha(Exception):
    """Uma execução que não terminou: a etapa em que parou, a mensagem e o início."""

    def __init__(self, etapa: str, erro: str, inicio: str):
        super().__init__(f"{etapa}: {erro}")
        self.etapa = etapa
        self.erro = erro
        self.inicio = inicio


@dataclass(frozen=True)
class Execucao:
    execucao_id: str
    ordem: int
    servidor: str
    io_threads: int
    carga: str
    repeticao: int


# --------------------------------------------------------------------------- plano


def gerar_plano(cfg: dict) -> list[Execucao]:
    """Plano completo, em blocos: cada repetição tem uma execução de cada combinação.

    A ordem dentro de cada bloco é sorteada com a semente do config, então o mesmo config
    gera sempre o mesmo plano. O `execucao_id` não depende da ordem.
    """
    plano = cfg["plano"]
    combinacoes = list(itertools.product(plano["servidores"], plano["io_threads"], plano["cargas"]))
    if plano["repeticoes"] < 1:
        raise ValueError("o plano precisa de pelo menos uma repetição")
    rng = config.criar_rng(cfg)
    execucoes = []
    for repeticao in range(1, plano["repeticoes"] + 1):
        for indice in rng.permutation(len(combinacoes)):
            servidor, threads, carga = combinacoes[indice]
            execucoes.append(
                Execucao(
                    execucao_id=f"{servidor}-t{threads}-{carga}-r{repeticao:02d}",
                    ordem=len(execucoes) + 1,
                    servidor=servidor,
                    io_threads=int(threads),
                    carga=carga,
                    repeticao=repeticao,
                )
            )
    return execucoes


# --------------------------------------------------------------------------- Docker


def rodar_comando(comando: list[str], cwd=None, env=None, timeout=None) -> tuple[int, str]:
    """Roda um comando e devolve (código de saída, stdout + stderr). Tempo esgotado -> código 124."""
    try:
        resultado = subprocess.run(comando, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"tempo esgotado ({timeout} s)"
    except FileNotFoundError:
        return 127, f"comando não encontrado: {comando[0]}"
    return resultado.returncode, ambiente.decodificar(resultado.stdout) + ambiente.decodificar(resultado.stderr)


class Docker:
    """Comandos do `docker compose` do Lab05, a partir da pasta do `compose.yaml`.

    `rodar` é injetável: nos testes, um falso registra os comandos e devolve saídas gravadas.
    """

    def __init__(self, pasta, pasta_saidas, servidores: dict, rodar=rodar_comando):
        self.pasta = str(pasta)
        self.pasta_saidas = str(Path(pasta_saidas).resolve())
        self.servidores = servidores
        self._rodar = rodar

    def _compose(self, perfis, argumentos, io_threads=1, timeout=None) -> str:
        comando = ["docker", "compose"]
        for perfil in perfis:
            comando += ["--profile", perfil]
        env = dict(os.environ, IO_THREADS=str(io_threads), SAIDAS=self.pasta_saidas)
        codigo, saida = self._rodar(comando + argumentos, cwd=self.pasta, env=env, timeout=timeout)
        if codigo != 0:
            linhas = saida.strip().splitlines()
            raise ErroExecucao(f"código {codigo} em 'docker compose {argumentos[0]}': {linhas[-1] if linhas else 'sem saída'}")
        return saida

    def limpar(self) -> None:
        """Remove contêineres que tenham ficado de uma execução interrompida."""
        perfis = [s["servico"] for s in self.servidores.values()] + ["cliente"]
        self._compose(perfis, ["down", "--remove-orphans"], timeout=120)

    def subir(self, servidor: str, io_threads: int, limite_s: int) -> None:
        servico = self.servidores[servidor]["servico"]
        argumentos = ["up", "-d", "--wait", "--wait-timeout", str(limite_s), servico]
        self._compose([servico], argumentos, io_threads, timeout=limite_s + 60)

    def info(self, servidor: str, secao: str) -> dict:
        s = self.servidores[servidor]
        argumentos = ["exec", "-T", s["servico"], s["cli"], "INFO", secao]
        return leitura.ler_info(self._compose([s["servico"]], argumentos, timeout=60))

    def cliente(self, argumentos: list[str], timeout: int) -> str:
        return self._compose(["cliente"], ["run", "--rm", "cliente", *argumentos], timeout=timeout)

    def parar(self, servidor: str) -> None:
        servico = self.servidores[servidor]["servico"]
        self._compose([servico], ["down"], timeout=120)


# --------------------------------------------------------------------------- cliente de carga


def argumentos_precarga(cfg: dict, servico: str) -> list[str]:
    """Grava todas as chaves uma vez, com uma conexão e acesso sequencial (passo 2)."""
    c = cfg["cliente"]
    return [
        f"--server={servico}", "--port=6379", "--protocol=redis",
        "-t", "1", "-c", "1", "-d", str(c["tamanho_valor"]), "--ratio=1:0",
        "--key-pattern=P:P", "--key-minimum=1", f"--key-maximum={c['chaves']}",
        "-n", "allkeys", "--hide-histogram",
    ]  # fmt: skip


def argumentos_carga(cfg: dict, servico: str, carga: str, segundos: int, json_out: str | None = None) -> list[str]:
    """Carga do aquecimento (sem JSON) e da medição (com JSON e percentis 50 e 99)."""
    c = cfg["cliente"]
    argumentos = [
        f"--server={servico}", "--port=6379", "--protocol=redis",
        "-t", str(c["threads"]), "-c", str(c["clientes_por_thread"]), "-d", str(c["tamanho_valor"]),
        f"--pipeline={c['pipeline']}", f"--ratio={cfg['plano']['cargas'][carga]}",
        "--key-pattern=R:R", "--key-minimum=1", f"--key-maximum={c['chaves']}",
        f"--test-time={segundos}", "--hide-histogram",
    ]  # fmt: skip
    if json_out:
        argumentos += ["--print-percentiles=50,99", f"--json-out-file={json_out}"]
    return argumentos


# --------------------------------------------------------------------------- uma execução


def executar_uma(ex: Execucao, cfg: dict, docker: Docker, pasta_saidas: Path, agora) -> dict:
    """Roda uma execução e devolve a linha do CSV; qualquer erro vira `Falha` com a etapa."""
    c = cfg["cliente"]
    s = cfg["plano"]["servidores"][ex.servidor]
    servico = s["servico"]
    arquivo_json = Path(pasta_saidas) / f"{ex.execucao_id}.json"
    inicio = agora()
    etapa = "subida"
    try:
        docker.subir(ex.servidor, ex.io_threads, c["limite_subida_s"])
        etapa = "versao"
        versao = leitura.versao(docker.info(ex.servidor, "server"), s["campo_versao"])
        etapa = "precarga"
        docker.cliente(argumentos_precarga(cfg, servico), timeout=FOLGA_CLIENTE_S * 5)
        etapa = "aquecimento"
        docker.cliente(argumentos_carga(cfg, servico, ex.carga, c["aquecimento_s"]), c["aquecimento_s"] + FOLGA_CLIENTE_S)
        etapa = "medicao"
        arquivo_json.unlink(missing_ok=True)  # sobra de uma tentativa anterior que falhou
        json_out = f"/saidas/{arquivo_json.name}"
        docker.cliente(argumentos_carga(cfg, servico, ex.carga, c["medicao_s"], json_out), c["medicao_s"] + FOLGA_CLIENTE_S)
        etapa = "leitura"
        if not arquivo_json.exists():
            raise leitura.ErroLeitura(f"o cliente não gravou {arquivo_json.name}")
        metricas = leitura.ler_memtier(arquivo_json.read_text(encoding="utf-8"))
        etapa = "memoria"
        memoria = leitura.memoria_bytes(docker.info(ex.servidor, "memory"))
    except (ErroExecucao, leitura.ErroLeitura) as erro:
        raise Falha(etapa, str(erro), inicio) from None
    return {
        "execucao_id": ex.execucao_id,
        "ordem": ex.ordem,
        "servidor": ex.servidor,
        "versao": versao,
        "io_threads": ex.io_threads,
        "carga": ex.carga,
        "repeticao": ex.repeticao,
        **metricas,
        "memoria_bytes": memoria,
        "inicio": inicio,
        "fim": agora(),
    }


# --------------------------------------------------------------------------- CSV e retomada


def ler_gravadas(caminho: Path) -> dict:
    """`execucao_id` -> `ordem` das execuções já gravadas (vazio se o CSV não existe)."""
    if not caminho.exists():
        return {}
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames != COLUNAS:
            raise ErroPlano(f"{caminho}: colunas diferentes das congeladas ({leitor.fieldnames})")
        return {linha["execucao_id"]: int(linha["ordem"]) for linha in leitor}


def conferir_retomada(plano: list[Execucao], gravadas: dict) -> None:
    """Exige que o CSV gravado seja do mesmo plano (mesmos ids nas mesmas posições)."""
    por_id = {ex.execucao_id: ex.ordem for ex in plano}
    for execucao_id, ordem in gravadas.items():
        if por_id.get(execucao_id) != ordem:
            raise ErroPlano(
                f"'{execucao_id}' (ordem {ordem}) não está nessa posição no plano atual: "
                "o config mudou desde a coleta gravada; use outra pasta de saída"
            )


def anexar(caminho: Path, colunas: list[str], linha: dict) -> None:
    """Acrescenta uma linha (e o cabeçalho, se o arquivo é novo) e grava no disco na hora."""
    novo = not caminho.exists()
    with open(caminho, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)
        arquivo.flush()
        os.fsync(arquivo.fileno())


# --------------------------------------------------------------------------- plano inteiro


def agora_local() -> str:
    """Instante atual com o fuso, em ISO 8601 (ex.: 2026-11-18T22:10:05-03:00)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def aplicar_ajustes(cfg: dict, repeticoes=None, aquecimento_s=None, medicao_s=None, pausa_s=None, saida=None) -> dict:
    """Cópia do config com repetições, tempos ou pasta de saída trocados (exemplo e piloto)."""
    novo = {**cfg, "cliente": dict(cfg["cliente"]), "plano": dict(cfg["plano"])}
    for chave, valor in (("aquecimento_s", aquecimento_s), ("medicao_s", medicao_s), ("pausa_s", pausa_s)):
        if valor is not None:
            novo["cliente"][chave] = valor
    if repeticoes is not None:
        novo["plano"]["repeticoes"] = repeticoes
    if saida is not None:
        novo["saida"] = saida
    return novo


def executar(cfg: dict, docker: Docker | None = None, agora=agora_local, dormir=time.sleep, coletar_ambiente=None, log=print) -> dict:
    """Roda o plano inteiro, pulando o que já foi gravado. Devolve o resumo da sessão."""
    pasta = Path(cfg["pasta"])
    saida = (pasta / cfg["saida"]).resolve()
    pasta_saidas = saida / "saidas"
    pasta_saidas.mkdir(parents=True, exist_ok=True)
    csv_execucoes = saida / "execucoes.csv"
    csv_falhas = saida / "falhas.csv"

    plano = gerar_plano(cfg)
    gravadas = ler_gravadas(csv_execucoes)
    conferir_retomada(plano, gravadas)
    pendentes = [ex for ex in plano if ex.execucao_id not in gravadas]

    docker = docker or Docker(pasta, pasta_saidas, cfg["plano"]["servidores"])
    coletar_ambiente = coletar_ambiente or (lambda: ambiente.coletar(pasta))
    resumo = {
        "inicio": agora(),
        "fim": None,
        "plano": len(plano),
        "ja_gravadas": len(gravadas),
        "pendentes": len(pendentes),
        "concluidas": 0,
        "falhas": [],
        "interrompida": False,
    }
    registro = saida / f"registro-{resumo['inicio'][:10]}.md"
    ambiente.escrever_registro(registro, coletar_ambiente(), cfg, resumo)
    log(f"plano: {len(plano)} execuções; já gravadas: {len(gravadas)}; pendentes: {len(pendentes)}")

    try:
        if pendentes:
            docker.limpar()
        for posicao, ex in enumerate(pendentes, start=1):
            log(f"[{posicao}/{len(pendentes)}] ordem {ex.ordem}: {ex.execucao_id}")
            try:
                anexar(csv_execucoes, COLUNAS, executar_uma(ex, cfg, docker, pasta_saidas, agora))
                resumo["concluidas"] += 1
            except Falha as falha:
                resumo["falhas"].append((ex.execucao_id, falha.etapa, falha.erro))
                anexar(csv_falhas, COLUNAS_FALHAS, {
                    "execucao_id": ex.execucao_id, "ordem": ex.ordem, "servidor": ex.servidor,
                    "io_threads": ex.io_threads, "carga": ex.carga, "repeticao": ex.repeticao,
                    "etapa": falha.etapa, "erro": falha.erro, "inicio": falha.inicio, "fim": agora(),
                })  # fmt: skip
                log(f"    falha na etapa {falha.etapa}: {falha.erro}")
            finally:
                try:
                    docker.parar(ex.servidor)
                except ErroExecucao as erro:
                    log(f"    aviso: o servidor não parou: {erro}")
            if posicao < len(pendentes):
                dormir(cfg["cliente"]["pausa_s"])
    except KeyboardInterrupt:
        resumo["interrompida"] = True
        log("interrompida: rode o mesmo comando para retomar de onde parou")
    finally:
        resumo["fim"] = agora()
        ambiente.anexar_resumo(registro, resumo)
    log(f"concluídas nesta sessão: {resumo['concluidas']}; falhas: {len(resumo['falhas'])}; CSV: {csv_execucoes}")
    return resumo
