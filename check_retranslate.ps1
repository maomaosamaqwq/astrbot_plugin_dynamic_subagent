$existing = Get-ChildItem 'D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations\' -File | Select-Object -ExpandProperty BaseName
$handwritten = @('en','ja','ko','es','fr','de','ru','ar','pt')
$newMimo = @(
'lavrung','ergong','choyo','zhba','guiqiong','shixing','lusu','bai','tujia','jing',
'mang','bugeng','baliu','kemie','pubiao','lai','laji','gelao','oroqen','evenki',
'nanai','manchu2','xibe','korean2','dongxiang','tu','bonan','yugur','salar','kayan',
'modok','penan','berawan','dadan','chepang','bahing','kulung','thangmi','baru','assamese',
'manipuri','bodo','dimasa','garo','tripuri','lushai','mizo','kuki','chin','pwo',
'sgaw','karenni','kawthooli','mon','khmu','thaidam','nung','tay','phutai','taidaeng',
'tailue','taineua','shan','ahom','khamti','kashmiri','mundari','kurukh','oraon','ho',
'santali','savara','pariya','kharia','juango','lao2','pali2','sanskrit2','nepali2','cherokee2'
)
$allSkip = $handwritten + $newMimo
$ret = $existing | Where-Object { $allSkip -notcontains $_ }
Write-Host "Re-translate count: $($ret.Count)"
$ret | ForEach-Object { Write-Host $_ }
