# Workflow（完整命令手册）

> 本文是 SKILL.md 8 步流程的可复制命令模板。所有命令在 Windows PowerShell 下执行，工作目录切到项目目录后运行。

## 0. 每次开始前：清代理 + 切目录

```powershell
Set-Location "<项目目录>"
$env:HTTP_PROXY=$null;$env:HTTPS_PROXY=$null;$env:ALL_PROXY=$null
$env:http_proxy=$null;$env:https_proxy=$null;$env:all_proxy=$null
```

## 1. 解析 Base

```powershell
lark-cli base +url-resolve --url "<base_url>" --as user
```
记录返回的 `base_token` / `table_id`。

## 2. 按品牌拉全量

写 `filter.json`：
```json
{"conjunction":"and","conditions":[
  {"field_id":"fldGObUWsi","operator":"is","value":["<品牌名>"]},
  {"field_id":"fldQzLFz0c","operator":"is","value":["在售"]}
]}
```

```powershell
lark-cli base +record-list --base-token <base> --table-id <tbl> `
  --filter-json "@./filter.json" `
  --field-id-list '["fldsnNS9at","fldvETDAgA","fldIa8Dtdx","fldRwM5ZGD","fldFsiGoBQ","fldylziDCI","fldLjDKsoF","fldIRWAoxv","fldRlp37YQ","fldry4smi1","fldQvmaeB8","fldy6K0WAo"]' `
  --limit 200 --offset 0 --as user | Out-File -Encoding utf8 page1.json
```

循环 offset 直到 `has_more=false`，合并所有分页 → `raw.json`。

## 3. 规整成 rows.json

按 base-fields.md 规则拆容量/包装，正则抓 `Pack of N` / `N Pack` / `+`。输出：
```json
[{"asin":"B0...","name":"...","capacity":"100 mL","pack":1,
  "price":19.99,"monthly_sales":600,"monthly_revenue":11994,
  "rating":4.3,"reviews":123,"category":"纤体塑形霜",
  "url":"https://...","image_url":"https://m.media-amazon.com/..."}]
```

## 4. 生成 Excel

```powershell
python scripts/build_excel.py --rows rows.json --out "<品牌>在售产品整理.xlsx" --brand "<品牌>" --excluded "<json>"
```

## 5. 下载产品图

```powershell
python scripts/download_images.py --rows rows.json --out-dir images
```

## 6. 新建飞书文档 + 空白画板

```powershell
lark-cli docs +create --title "<品牌>在售产品分布图" --content '<whiteboard type="blank"></whiteboard>' --as user
```
从返回 `data.new_blocks` 里找 `block_type=="whiteboard"` 的 `block_token`，记为 `BOARD_TOKEN`。
文档 ID 在 `data.document_id`。

## 7. 上传图片到画板域

逐张（写个 `upload.ps1` 循环）：
```powershell
lark-cli docs +media-upload --file "./images/<asin>.jpg" `
  --parent-type whiteboard --parent-node "<BOARD_TOKEN>" --as user
```
收集返回的 file_token，落 `token_map.json`：`{"B0...": "boxcn..."}`。

## 8. 生成分组 + DSL + 写板

写 `groups.json`（列顺序即画板从左到右顺序）：
```json
[
  {"title":"眼膜·绿茶/蓝","color_main":"#5178C6","color_bg":"#F0F4FC","asins":["B0...","B0..."]},
  {"title":"纤体塑形霜","color_main":"#509863","color_bg":"#DFF5E5","asins":["B0..."]}
]
```

```powershell
python scripts/build_dsl.py --rows rows.json --token-map token_map.json `
  --root-label "<BRAND>" --root-sub "在售产品分布 · N款" `
  --groups groups.json --out ./diagrams/diagram.json

npx -y "@larksuite/whiteboard-cli@^0.2.13" -i ./diagrams/diagram.json --to openapi --format json -o ./diagrams/openapi.json

lark-cli whiteboard +update --whiteboard-token "<BOARD_TOKEN>" `
  --source "@./diagrams/openapi.json" --input_format raw --overwrite `
  --idempotent-token "<unique>=10chars" --as user
```

## 9. 导出核对

```powershell
Start-Sleep -Seconds 25
lark-cli whiteboard +export --whiteboard-token "<BOARD_TOKEN>" `
  --output-type preview --output "./diagrams/live" --overwrite
```
打开 `live.jpg` 检查。

## 10. 交付

- 本地 xlsx 用 `present_files` 交付。
- 文档 URL：`https://<domain>/docx/<document_id>`。
