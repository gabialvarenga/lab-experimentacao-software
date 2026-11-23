# Cria no GitHub o milestone Lab05S03, o rótulo lab05 e as 9 Issues da Sprint 03, adiciona cada uma ao Kanban
# e registra as dependências ("bloqueada por") do campo depende_de do issues.json.
# Em depende_de, "S03-xx" é uma Issue deste arquivo e "#300" é uma Issue que já existe (de outra sprint).
# Requer o GitHub CLI autenticado como integrante do grupo, com o escopo de projetos:
#   winget install GitHub.cli ; gh auth login ; gh auth refresh -s project
# Uso:  pwsh lab05/docs/issues-s03/criar-issues.ps1 -DryRun                    (só lista o que seria criado)
#       pwsh lab05/docs/issues-s03/criar-issues.ps1 -Prazo 2026-12-03        (cria de verdade)
param([switch]$DryRun, [switch]$SemKanban, [string]$Prazo)

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$repo = "gabialvarenga/lab-experimentacao-software"
$milestone = "Lab05S03"
$pasta = $PSScriptRoot
$issues = Get-Content (Join-Path $pasta "issues.json") -Raw -Encoding UTF8 | ConvertFrom-Json

foreach ($i in $issues) {
    if (-not (Test-Path (Join-Path $pasta "$($i.n).md"))) { throw "Falta o corpo da Issue: $($i.n).md" }
}

# Toda dependência aponta para uma Issue deste arquivo ou para uma Issue existente no formato "#número".
$nomes = $issues | ForEach-Object { $_.n }
foreach ($i in $issues) {
    foreach ($d in $i.depende_de) {
        if ($d -notmatch '^#\d+$' -and $nomes -notcontains $d) { throw "$($i.n) depende de $d, que não existe no issues.json" }
    }
}

if ($DryRun) {
    foreach ($i in $issues) {
        $dep = if ($i.depende_de.Count) { "bloqueada por " + ($i.depende_de -join ", ") } else { "sem dependências" }
        Write-Host ("[dry-run] {0}  (rótulos: lab05, {1}; milestone {2}; {3})" -f $i.titulo, $i.label, $milestone, $dep)
    }
    return
}

if (-not $Prazo) { throw "Informe o fim da sprint: -Prazo AAAA-MM-DD" }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "GitHub CLI (gh) não encontrado. Instale com: winget install GitHub.cli" }
gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Rode 'gh auth login' antes." }

gh label create lab05 --repo $repo --color 0e8a16 --description "Lab05" 2>$null
$existe = (gh api "repos/$repo/milestones?state=all&per_page=100" | ConvertFrom-Json) | Where-Object { $_.title -eq $milestone }
if (-not $existe) {
    gh api "repos/$repo/milestones" -f title=$milestone -f due_on="$($Prazo)T23:59:00Z" -f state=open | Out-Null
}

$nodeId = @{}
# Issues de outras sprints: buscar antes de criar qualquer coisa, para falhar cedo se alguma não existir.
$externas = $issues | ForEach-Object { $_.depende_de } | Where-Object { $_ -match '^#\d+$' } | Sort-Object -Unique
foreach ($d in $externas) {
    $id = (gh api "repos/$repo/issues/$($d.TrimStart('#'))" | ConvertFrom-Json).node_id
    if (-not $id) { throw "A Issue $d não foi encontrada no repositório." }
    $nodeId[$d] = $id
}

foreach ($i in $issues) {
    $url = gh issue create --repo $repo --title $i.titulo --body-file (Join-Path $pasta "$($i.n).md") `
        --label "lab05,$($i.label)" --milestone $milestone
    Write-Host "$($i.titulo) -> $url"
    # O projeto 9 já adiciona Issues novas sozinho; o item-add cobre o caso de a automação estar desligada.
    if (-not $SemKanban) { gh project item-add 9 --owner gabialvarenga --url $url 2>$null | Out-Null }
    $numero = ($url -split "/")[-1]
    $nodeId[$i.n] = (gh api "repos/$repo/issues/$numero" | ConvertFrom-Json).node_id
}

# Dependências: a Issue fica "bloqueada por" cada predecessora até ela ser fechada.
$mutacao = 'mutation($i:ID!,$b:ID!){addBlockedBy(input:{issueId:$i,blockingIssueId:$b}){issue{number}}}'
foreach ($i in $issues) {
    foreach ($d in $i.depende_de) {
        gh api graphql -f "query=$mutacao" -f "i=$($nodeId[$i.n])" -f "b=$($nodeId[$d])" | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Não foi possível registrar: $($i.n) bloqueada por $d" }
        else { Write-Host "$($i.n) bloqueada por $d" }
    }
}
