"""Registro do ambiente da execução: versões e digests das imagens, CPU, memória, SO, Docker e WSL.

`coletar` levanta o ambiente com comandos do sistema (cada item que falha vira "indisponível",
sem interromper a coleta). `escrever_registro` grava `registro-<data>.md` e `anexar_resumo`
acrescenta o resumo da sessão ao fim. Várias sessões no mesmo dia (retomada) vão para o mesmo
arquivo, uma seção por sessão.
"""

import ctypes
import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

INDISPONIVEL = "indisponível"


def decodificar(dados: bytes) -> str:
    """Bytes de um comando em texto. O `wsl.exe` responde em UTF-16, os demais em UTF-8."""
    if not dados:
        return ""
    if b"\x00" in dados:
        return dados.decode("utf-16-le", errors="replace").replace("﻿", "")
    return dados.decode("utf-8", errors="replace")


def _rodar(comando: list[str], cwd=None) -> str:
    """Saída de um comando, sem espaços nas pontas, ou `INDISPONIVEL` se falhar."""
    try:
        resultado = subprocess.run(comando, cwd=cwd, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return INDISPONIVEL
    texto = decodificar(resultado.stdout).strip()
    return texto if resultado.returncode == 0 and texto else INDISPONIVEL


def _memoria_total_bytes(sistema: str):
    if sistema == "win32" and hasattr(ctypes, "windll"):  # pragma: no branch

        class Estado(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (nome, ctypes.c_ulonglong)
                for nome in ("total", "livre", "pag_total", "pag_livre", "virt_total", "virt_livre", "ext")
            ]

        estado = Estado()
        estado.dwLength = ctypes.sizeof(Estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            return estado.total
        return None  # pragma: no cover
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):  # pragma: no cover
        return None


def _processador(sistema: str, rodar) -> str:
    if sistema == "win32":
        return rodar(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
    try:
        for linha in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if linha.startswith("model name"):
                return linha.split(":", 1)[1].strip()
    except OSError:  # pragma: no cover
        pass
    return platform.processor() or INDISPONIVEL


def _wslconfig() -> str:
    """Linhas de limite do `.wslconfig` (memória, processadores, swap), se o arquivo existe."""
    caminho = Path.home() / ".wslconfig"
    if not caminho.exists():
        return "sem .wslconfig (limites padrão do WSL)"
    linhas = [
        linha.strip()
        for linha in caminho.read_text(encoding="utf-8", errors="replace").splitlines()
        if linha.strip().split("=")[0].strip().lower() in {"memory", "processors", "swap"}
    ]
    return "; ".join(linhas) or "sem limites no .wslconfig"


# Modo de energia do Windows 11 (Configurações > Energia), sobreposto ao plano do powercfg
MODOS_ENERGIA = {
    "ded574b5-45a0-4f42-8737-46345c09c238": "Melhor desempenho",
    "00000000-0000-0000-0000-000000000000": "Equilibrado",
    "961cc777-2547-4f9d-8174-7d86181b8a7a": "Melhor eficiência de energia",
    "3af9b8d9-7c97-431d-ad78-34a8bfea439f": "Melhor eficiência de energia",
}
# Win32_Battery.BatteryStatus: 1 = descarregando; 2 e 6 a 9 = ligado na tomada
STATUS_BATERIA = {"1": "bateria (descarregando)", "2": "tomada", "6": "tomada (carregando)",
                  "7": "tomada (carregando)", "8": "tomada (carregando)", "9": "tomada (carregando)"}  # fmt: skip


def _modo_energia(rodar) -> str:
    chave = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes"
    guid = rodar(["powershell", "-NoProfile", "-Command", f"(Get-ItemProperty '{chave}').ActiveOverlayAcPowerScheme"])
    return f"{MODOS_ENERGIA.get(guid.lower(), 'desconhecido')} ({guid})" if guid != INDISPONIVEL else INDISPONIVEL


def _alimentacao(rodar) -> str:
    status = rodar(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"])
    if status == INDISPONIVEL:
        return "sem bateria ou indisponível"
    return f"{STATUS_BATERIA.get(status, 'desconhecida')} (BatteryStatus {status})"


def coletar(pasta, rodar=_rodar, sistema: str = sys.platform) -> dict:
    """Levanta o ambiente da máquina e do Docker. `pasta` é onde está o `compose.yaml`."""
    perfis = ["--profile", "redis", "--profile", "valkey", "--profile", "cliente"]
    imagens = rodar(["docker", "compose", *perfis, "config", "--images"], cwd=pasta)
    linhas_imagens = []
    if imagens != INDISPONIVEL:
        for imagem in sorted(set(imagens.splitlines())):
            id_local = rodar(["docker", "image", "inspect", imagem, "--format", "{{.Id}}"])
            linhas_imagens.append((imagem, id_local))
    memoria = _memoria_total_bytes(sistema)
    compose = Path(pasta) / "compose.yaml"
    return {
        "Sistema operacional": platform.platform(),
        "Processador": _processador(sistema, rodar),
        "CPUs lógicas da máquina": str(os.cpu_count()),
        "Memória da máquina": f"{memoria / 2**30:.1f} GiB ({memoria} bytes)" if memoria else INDISPONIVEL,
        "Plano de energia": rodar(["powercfg", "/getactivescheme"]) if sistema == "win32" else "não se aplica",
        "Modo de energia (na tomada)": _modo_energia(rodar) if sistema == "win32" else "não se aplica",
        "Alimentação": _alimentacao(rodar) if sistema == "win32" else "não se aplica",
        "Python": platform.python_version(),
        "Docker (cliente / servidor)": rodar(["docker", "version", "--format", "{{.Client.Version}} | {{.Server.Version}}"]),
        "Docker Desktop": rodar(["docker", "version", "--format", "{{.Server.Platform.Name}}"]),
        "Docker Compose": rodar(["docker", "compose", "version", "--short"]),
        "Máquina do Docker (CPUs / memória / kernel / SO)": rodar(
            ["docker", "info", "--format", "{{.NCPU}} | {{.MemTotal}} | {{.KernelVersion}} | {{.OperatingSystem}}"]
        ),
        "WSL": " ; ".join(rodar(["wsl", "--version"]).splitlines()) if sistema == "win32" else "não se aplica",
        "Limites do WSL": _wslconfig() if sistema == "win32" else "não se aplica",
        "SHA-256 do compose.yaml": hashlib.sha256(compose.read_bytes()).hexdigest() if compose.exists() else INDISPONIVEL,
        "imagens": linhas_imagens,
    }


def _sha_config(cfg: dict) -> str:
    caminho = Path(cfg["pasta"]) / "config.yaml"
    return hashlib.sha256(caminho.read_bytes()).hexdigest() if caminho.exists() else INDISPONIVEL


def escrever_registro(caminho, amb: dict, cfg: dict, resumo: dict) -> None:
    """Abre a seção da sessão em `registro-<data>.md` com o ambiente e o plano."""
    caminho = Path(caminho)
    plano, cliente = cfg["plano"], cfg["cliente"]
    linhas = [] if caminho.exists() else [f"# Registro da execução do benchmark — {resumo['inicio'][:10]}", ""]
    linhas += [
        f"## Sessão iniciada em {resumo['inicio']}",
        "",
        "### Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
    ]
    linhas += [f"| {item} | {str(valor).replace('|', '/')} |" for item, valor in amb.items() if item != "imagens"]
    linhas += ["", "### Imagens (referência fixada e ID local)", "", "| Imagem | ID local |", "|---|---|"]
    linhas += [f"| `{imagem}` | `{id_local}` |" for imagem, id_local in amb.get("imagens", [])] or ["| indisponível | |"]
    linhas += [
        "",
        "### Plano",
        "",
        f"- Semente: {cfg['semente']}; SHA-256 do config.yaml: `{_sha_config(cfg)}`",
        f"- Servidores: {', '.join(plano['servidores'])}; io_threads: {', '.join(map(str, plano['io_threads']))}; "
        f"cargas: {', '.join(plano['cargas'])}; repetições: {plano['repeticoes']}",
        f"- Cliente: {cliente['threads']} threads × {cliente['clientes_por_thread']} clientes, valor de "
        f"{cliente['tamanho_valor']} bytes, pipeline {cliente['pipeline']}, {cliente['chaves']} chaves",
        f"- Tempos: aquecimento {cliente['aquecimento_s']} s, medição {cliente['medicao_s']} s, pausa {cliente['pausa_s']} s",
        f"- Execuções no plano: {resumo['plano']}; já gravadas antes desta sessão: {resumo['ja_gravadas']}; "
        f"pendentes: {resumo['pendentes']}",
        "",
    ]
    with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


def anexar_resumo(caminho, resumo: dict) -> None:
    """Fecha a seção da sessão com o que foi concluído, as falhas e se foi interrompida."""
    linhas = [
        "### Resumo da sessão",
        "",
        f"- Fim: {resumo['fim']}" + (" (interrompida; retomar com o mesmo comando)" if resumo["interrompida"] else ""),
        f"- Concluídas nesta sessão: {resumo['concluidas']}",
        f"- Falhas nesta sessão: {len(resumo['falhas'])}" + (" (detalhes em `falhas.csv`)" if resumo["falhas"] else ""),
    ]
    linhas += [f"  - `{execucao_id}`, etapa {etapa}: {erro}" for execucao_id, etapa, erro in resumo["falhas"]]
    with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write("\n".join(linhas) + "\n\n")
