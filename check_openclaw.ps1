$dir = 'D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations\'
$files = Get-ChildItem $dir -File
$wrong = @()
$right = @()
foreach ($f in $files) {
    $content = Get-Content $f.FullName -Head 3 -Raw
    if ($content -match 'OpenClaw') {
        $wrong += $f.Name
    } else {
        $right += $f.Name
    }
}
Write-Host "Still wrong (OpenClaw): $($wrong.Count)"
Write-Host "Correct (Dynamic SubAgent): $($right.Count)"
Write-Host "--- Wrong files ---"
$wrong | ForEach-Object { Write-Host $_ }
