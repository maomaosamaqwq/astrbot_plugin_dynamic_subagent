$existing = Get-ChildItem 'D:\aibot\openclaw\workspace\astrbot_plugin_dynamic_subagent\translations\' -File | Select-Object -ExpandProperty BaseName
$needed = @(
'hakka','minnan','cantonese','jin','pinghua','hui','danzhouhua','cham','leqi','langsua',
'bola','zaiwa','achang','benglong','bulang','hulanguage','ake','bisu','hani','jino',
'lahu','lisu','nusu','zou','anong','derung','lhoba','cuonamonba','changlo','laga',
'yidu','tawang','geman','sulong','karbi','tangkhul','maring','thado','limbu','rai',
'sunuwar','magar','gurung','tamang','namuyi','muya','qiang','pumi','jiarong','ersu',
'lavrung','ergong','choyo','zhba','guiqiong','shixing','lusu','bai','tujia','jing',
'mang','bugeng','baliu','kemie','pubiao','lai','laji','gelao','oroqen','evenki',
'nanai','manchu2','xibe','korean2','dongxiang','tu','bonan','yugur','salar','iliturki',
'tatar','tuvan','koryak','itelmen','yukaghir','nivkh','ket','sundanese','madurese',
'minangkabau','acehnese','balinese','sasak','buginese','makassarese','toraja','mori',
'banggai','muna','butung','wolio','kina','dayak','iban','kenyah','kayan','modok',
'penan','berawan','dadan','chepang','bahing','kulung','thangmi','baru','assamese',
'manipuri','bodo','dimasa','garo','tripuri','lushai','mizo','kuki','chin','pwo',
'sgaw','karenni','kawthooli','mon','khmu','thaidam','nung','tay','phutai','taidaeng',
'tailue','taineua','shan','ahom','khamti','kashmiri','mundari','kurukh','oraon','ho',
'santali','savara','pariya','kharia','juango','lao2','pali2','sanskrit2','nepali2',
'cherokee2','oldjavanese','chukchi'
)
$missing = $needed | Where-Object { $existing -notcontains $_ }
Write-Host "Missing count: $($missing.Count)"
$missing | ForEach-Object { Write-Host $_ }
