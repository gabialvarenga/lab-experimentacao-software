# Cria no GitHub o milestone Lab04S02, o rótulo lab04 e as 14 Issues da Sprint 02.
# Requer o GitHub CLI autenticado como integrante do grupo:  winget install GitHub.cli ; gh auth login
# Para adicionar ao Kanban, rode antes:  gh auth refresh -s project
# Uso:  pwsh lab04/docs/issues-s02/criar-issues.ps1 -DryRun   (só lista o que seria criado)
#       pwsh lab04/docs/issues-s02/criar-issues.ps1           (cria de verdade)
param([switch]$DryRun, [switch]$SemKanban)

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$repo = "gabialvarenga/lab-experimentacao-software"
$pasta = $PSScriptRoot
$issues = Get-Content (Join-Path $pasta "issues.json") -Raw -Encoding UTF8 | ConvertFrom-Json

if ($DryRun) {
    foreach ($i in $issues) { Write-Host ("[dry-run] {0}  (rótulos: lab04, {1}; milestone Lab04S02)" -f $i.titulo, $i.label) }
    return
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "GitHub CLI (gh) não encontrado. Instale com: winget install GitHub.cli" }
gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Rode 'gh auth login' antes." }

gh label create lab04 --repo $repo --color 1d76db --description "Lab04" 2>$null
$existe = gh api "repos/$repo/milestones?state=all" --jq '.[] | select(.title=="Lab04S02") | .number'
if (-not $existe) {
    gh api "repos/$repo/milestones" -f title=Lab04S02 -f due_on=2026-11-12T23:59:00Z -f state=open | Out-Null
}

foreach ($i in $issues) {
    $url = gh issue create --repo $repo --title $i.titulo --body-file (Join-Path $pasta "$($i.n).md") `
        --label "lab04,$($i.label)" --milestone Lab04S02
    Write-Host "$($i.titulo) -> $url"
    if (-not $SemKanban) { gh project item-add 9 --owner gabialvarenga --url $url | Out-Null }
}
