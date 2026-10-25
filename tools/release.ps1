# Saturn release gate: run every test; deploy ONLY if all pass.
#   powershell -File C:\dev\tools\release.ps1            -> test + deploy
#   powershell -File C:\dev\tools\release.ps1 -TestOnly  -> test only
#   -Team ai-team-saturn                                 -> which squad folder to test/deploy
param([switch]$TestOnly, [string]$Team = 'ai-team-strands-balanced')
$ErrorActionPreference = 'Stop'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$env:PYTHONIOENCODING = 'utf-8'
$root = 'C:\dev\sample-ai-possibilities\agentic-football-sample-agents'
$py = "$root\.venv\Scripts\python.exe"
$failed = @()
if (-not (Test-Path "$root\$Team\deploy_all.py")) { Write-Host "Unknown team folder: $Team" -ForegroundColor Red; exit 1 }
$env:SATURN_TEAM = $Team
Write-Host "Team: $Team"

function Run($name, $file, $dir) {
    # A failing test writes a traceback to stderr; under 'Stop' PowerShell 5.1
    # would abort the whole gate instead of reporting FAIL. Judge by exit code.
    $ErrorActionPreference = 'Continue'
    Push-Location $dir
    try { $out = & $py $file 2>&1 | Out-String } finally { Pop-Location }
    $bad = ([regex]::Matches($out, '\[FAIL\]|Traceback|AssertionError|SOME FAILED')).Count
    if ($LASTEXITCODE -ne 0 -or $bad -gt 0) { $script:failed += $name; Write-Host "FAIL  $name" -ForegroundColor Red; Write-Host $out }
    else { Write-Host "pass  $name" -ForegroundColor Green }
}

if (Test-Path "$root\lib\frame.py") {
    Run 'saturn rules/coach/guard/possession/stamina/frame' 'C:\dev\tools\test_v11.py' 'C:\dev\tools'
    Run 'replay: real match ticks through all 5 handlers' 'C:\dev\tools\test_replay.py' 'C:\dev\tools'
} else {
    Write-Host "(stock code: Saturn-only suites skipped)"
}
Run 'prompt check: every agent prompt builds and names its player' 'C:\dev\tools\test_prompts.py' 'C:\dev\tools'
foreach ($t in Get-ChildItem "$root\lib\test_*.py" | Where-Object { $_.Name -ne 'test_helpers.py' }) { Run "lib: $($t.Name)" $t.Name "$root\lib" }
foreach ($a in 'ai-gk','ai-def','ai-mid','ai-fwd1','ai-fwd2') { Run "agent tests: $Team/$a" "$a\test_local.py" "$root\$Team" }

if ($failed.Count -gt 0) { Write-Host "`nRELEASE BLOCKED: $($failed -join ', ')" -ForegroundColor Red; exit 1 }
Write-Host "`nALL TESTS PASS" -ForegroundColor Green
if ($TestOnly) { exit 0 }

$sha = (git -C C:\dev\sample-ai-possibilities rev-parse --short HEAD)
$dirty = (git -C C:\dev\sample-ai-possibilities status --porcelain)
if ($dirty) { Write-Host "RELEASE BLOCKED: uncommitted changes - commit first so the deploy is traceable" -ForegroundColor Red; exit 1 }
Write-Host "Deploying $Team at commit $sha ..."
Push-Location "$root\$Team"
# The AgentCore CLI writes informational lines (e.g. "AI agent detected") to
# stderr; judge the deploy by its exit code, not by stderr output.
$ErrorActionPreference = 'Continue'
try { & $py deploy_all.py *> "C:\dev\deploy_$sha.log" } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { Write-Host "DEPLOY FAILED - see C:\dev\deploy_$sha.log" -ForegroundColor Red; exit 1 }
Add-Content C:\dev\RELEASES.md "- $(Get-Date -Format 'yyyy-MM-dd HH:mm') deployed $Team @ $sha"
Write-Host "DEPLOYED $sha - warm up with 'Test your agents' before playing" -ForegroundColor Green
