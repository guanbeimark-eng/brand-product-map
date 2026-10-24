# Workflow（完整命令手册）

> 本文是 SKILL.md 8 步流程的可复制命令模板。所有命令在 Windows PowerShell 下执行，工作目录切到项目目录后运行。

## 0. 每次开始前：清代理 + 切目录

```powershell
Set-Location "<项目目录>"
$env:HTTP_PROXY=$null;$env:HTTPS_PROXY=$null;$env:ALL_PROXY=$null
$env:http_proxy=$null;$env:https_proxy=$null;$env:all_proxy=$null
```

建立 `checkpoints/` 与 `run-manifest.json`。每完成一步写 `<step>.done.json`；任一步出现 `STOP` 就保留现场，不得跳步。

## 1. 解析 Base

```powershell
lark-cli base +url-resolve --url "<base_url>" --as user
```
记录返回的 `base_token` / `table_id`。

## 2. 按品牌拉全量

推荐使用可恢复脚本：
```powershell
python scripts/pull_base.py --base-url "<base_url>" --brand-field "<brand_field_id>" --brand-value "<品牌>" --status-field "<status_field_id>" --field-id-list '@./field_ids.json' --out raw.json --checkpoint checkpoints/base.json
```

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

脚本循环 offset 直到 `has_more=false`，合并所有分页 → `raw.json`。失败或响应形状未知时 STOP，修复输入后重跑同一命令，不删除 checkpoint。

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

推荐使用可断点续传脚本：
```powershell
python scripts/upload_to_board.py --images-dir images --board-token "<BOARD_TOKEN>" --out token_map.json
```

逐张（写个 `upload.ps1` 循环）：
```powershell
lark-cli docs +media-upload --file "./images/<asin>.jpg" `
  --parent-type whiteboard --parent-node "<BOARD_TOKEN>" --as user
```
收集返回的 file_token，落 `token_map.json`：`{"B0...": "boxcn..."}`。

## 8. 生成分组 + DSL + 写板

**CHECKPOINT / STOP**：`+update` 前确认每个 ASIN 都有本次白板上传的 token，且目标是新建空白画板；已有画板或 token 冲突立即 STOP。

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

交付前运行工作簿校验：
```powershell
python scripts/excel_formula_verify.py --xlsx "<品牌>在售产品整理.xlsx" --rows rows.json
```
无公式时退出码 4 是正常终态；退出码 2 表示工作簿、行数或明显公式错误，需要 STOP。

### 失败恢复矩阵

| 阶段 | 停止条件 | 保留物 | 恢复动作 |
|---|---|---|---|
| Base | resolve/分页失败、权限/登录/CAPTCHA | `checkpoints/base.json`、日志 | 修复凭据/字段后重跑 `pull_base.py` |
| Docs | create 或 media-upload 失败、非 whiteboard token | 文档 ID、`token_map.json` | 不重建文档，从未上传文件继续并核验 parent-node |
| Whiteboard | DSL/update/export 失败、目标已存在 | `diagram.json`、`openapi.json`、预览 | 人工核对 board 后从失败步骤恢复 |

### 本地技能自动同步

已配置 `scripts/auto_sync.ps1` 监听本仓库，并在文件保存后自动提交、推送到 `origin/main`。安装或恢复登录启动任务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\auto_sync.ps1 -InstallTask
```

日志位于 `$env:LOCALAPPDATA\brand-product-map-auto-sync.log`。发生冲突、凭据失败或远端拒绝时，脚本只记录 `STOP`，不会 force-push、reset 或自动解决冲突；需要人工修复后再运行 `-Once`。卸载登录启动任务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\auto_sync.ps1 -UninstallTask
```
