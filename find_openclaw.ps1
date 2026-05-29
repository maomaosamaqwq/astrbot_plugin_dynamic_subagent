$dir = 'D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations\'
$files = Get-ChildItem $dir -File
$wrong = @()
foreach ($f in $files) {
    $line = Get-Content $f.FullName -First 3
    $text = $line -join ' '
    if ($text -like '*OpenClaw*') {
        $wrong += $f.Name
    }
}
Write-Host "Files still mentioning OpenClaw: $($wrong.Count)"
if ($wrong.Count -gt 0) {
    $wrong | ForEach-Object { Write-Host $_ }
}
