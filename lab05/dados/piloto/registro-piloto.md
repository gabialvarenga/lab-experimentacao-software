# Registro da execução do benchmark — 2026-11-18

## Sessão iniciada em 2026-11-18T20:09:05-03:00

### Ambiente

| Item | Valor |
|---|---|
| Sistema operacional | Windows-11-10.0.26200-SP0 |
| Processador | 13th Gen Intel(R) Core(TM) i7-13620H |
| CPUs lógicas da máquina | 16 |
| Memória da máquina | 23.7 GiB (25414197248 bytes) |
| Plano de energia | GUID do Esquema de Energia: 381b4222-f694-41f0-9685-ff5bb260df2e  (Equilibrado) |
| Modo de energia (na tomada) | Melhor desempenho (ded574b5-45a0-4f42-8737-46345c09c238) |
| Alimentação | tomada (BatteryStatus 2) |
| Python | 3.14.3 |
| Docker (cliente / servidor) | 29.3.1 / 29.3.1 |
| Docker Desktop | Docker Desktop 4.67.0 (222858) |
| Docker Compose | 5.1.1 |
| Máquina do Docker (CPUs / memória / kernel / SO) | 16 / 12364996608 / 6.6.87.2-microsoft-standard-WSL2 / Docker Desktop |
| WSL | Versão do WSL: 2.6.3.0 ; Versão do kernel: 6.6.87.2-1 ; Versão do WSLg: 1.0.71 ; Versão do MSRDC: 1.2.6353 ; Versão do Direct3D: 1.611.1-81528511 ; Versão do DXCore: 10.0.26100.1-240331-1435.ge-release ; Versão do Windows: 10.0.26200.9974 |
| Limites do WSL | sem .wslconfig (limites padrão do WSL) |
| SHA-256 do compose.yaml | da02a59624f7810b0940807913a714badf49335fb9cd6a40f472fffd043a5f96 |

### Imagens (referência fixada e ID local)

| Imagem | ID local |
|---|---|
| `redis:8.10.3@sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53` | `sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53` |
| `redislabs/memtier_benchmark:2.6.1@sha256:41849040f6ea0b335c31ae532b1488ce47ea6e8c48a086d661f3d6953d3b599d` | `sha256:41849040f6ea0b335c31ae532b1488ce47ea6e8c48a086d661f3d6953d3b599d` |
| `valkey/valkey:9.1.3@sha256:3add1a336a920ea54770a001ab6feb3da5fceea96a40373a3a2cd469b815f0b7` | `sha256:3add1a336a920ea54770a001ab6feb3da5fceea96a40373a3a2cd469b815f0b7` |

### Plano

- Semente: 42; SHA-256 do config.yaml: `46c31504b69ab857743046bffccda6c05c9c388efe79aef1178d9141678e3ac3`
- Servidores: redis, valkey; io_threads: 1, 4; cargas: set, get, misto; repetições: 5
- Cliente: 4 threads × 12 clientes, valor de 100 bytes, pipeline 1, 100000 chaves
- Tempos: aquecimento 10 s, medição 30 s, pausa 5 s
- Execuções no plano: 60; já gravadas antes desta sessão: 0; pendentes: 60

### Resumo da sessão

- Fim: 2026-11-18T21:08:34-03:00
- Concluídas nesta sessão: 60
- Falhas nesta sessão: 0

