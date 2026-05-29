$dir = "D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations"
$files = Get-ChildItem $dir -File | Sort-Object Name
$links = @()
foreach ($f in $files) {
    $name = $f.BaseName
    $ext = $f.Extension
    $links += "[$name](translations/$f)"
}
$links -join " | "
