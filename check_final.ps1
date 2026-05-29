$dir = "D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations"
$wrong = @()
$correct = @()
Get-ChildItem $dir -File | ForEach-Object {
    $content = Get-Content $_.FullName -Head 2 -ErrorAction SilentlyContinue
    if ($content -match 'OpenClaw') {
        $wrong += $_.Name
    } else {
        $correct += $_.Name
    }
}
Write-Host "=== Still OpenClaw (WRONG): $($wrong.Count) ==="
$wrong | ForEach-Object { Write-Host "  - $_" }
Write-Host ""
Write-Host "=== Correct (Dynamic SubAgent): $($correct.Count) ==="
