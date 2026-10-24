# Workflow（插件内完整命令手册）

> 本文命令相对插件根目录执行。插件根目录包含 `plugin.json` 和 `skills/brand-product-map`；业务脚本位于 `skills/brand-product-map/scripts`。

## 0. 初始化目录、代理和 checkpoint

```powershell
$pluginDir = "<插件目录>"
$skillDir = Join-Path $pluginDir "skills\brand-product-map"
$projectDir = "<项目数据目录>"
Set-Location $projectDir
New-Item -ItemType Directory -Force "$projectDir\checkpoints" | Out-Null
$env:HTTP_PROXY=$null;$env:HTTPS_PROXY=$null;$env:ALL_PROXY=$null
$env:http_proxy=$null;$env:https_proxy=$null;$env:all_proxy=$null
```

每完成一步写入 `$projectDir\checkpoints\<step>.done.json`，记录输入、输出、时间和远程资源 ID。任一步出现 `STOP` 就保留现场，不得跳步。

## 1. SellerSprite 拉取产品

凭据只从安全运行时读取，禁止写入文件或日志：

```powershell
if (-not $env:SELLERSPRITE_KEY) { throw "STOP: SELLERSPRITE_KEY is missing" }
python "$skillDir\scripts\sp_fetch.py" --brand "<Brand>" --out "$projectDir\brand_products.json"
```

脚本通过 Streamable HTTP 的 `competitor_lookup` 分页拉全量。认证失败、响应非预期、空页或限流时停止并保留日志。

## 2. 清洗和拆分品牌

```powershell
python "$skillDir\scripts\clean_mcp.py" --raw "$projectDir\brand_products.json" --out "$projectDir\rows_by_brand.json"
```

从 `rows_by_brand.json` 中取目标品牌数组，写成 `$projectDir\rows_<brand>.json`。核对清洗前后行数和被剔除品类。

## 3. 生成 Excel

```powershell
python "$skillDir\scripts\build_excel.py" --rows "$projectDir\rows_<brand>.json" --out "$projectDir\<Brand>在售产品整理.xlsx" --brand "<Brand>"
python "$skillDir\scripts\excel_formula_verify.py" --xlsx "$projectDir\<Brand>在售产品整理.xlsx" --rows "$projectDir\rows_<brand>.json"
```

exit code 4 表示工作簿有效但没有公式；exit code 2 表示文件、行数或明显公式错误。

## 4. 下载产品图

```powershell
python "$skillDir\scripts\download_images.py" --rows "$projectDir\rows_<brand>.json" --out-dir "$projectDir\images_<brand>"
```

检查 `_failed.txt`；失败图片不能静默当作成功。

## 5. 新建独立文档和白板

先准备只包含 `<whiteboard type="blank"></whiteboard>` 的内容文件：

```powershell
Set-Location $projectDir
Set-Content -LiteralPath .\wb_content.xml -Value '<whiteboard type="blank"></whiteboard>' -Encoding utf8
lark-cli docs +create --title "<Brand>在售产品分布图" --content "@.\wb_content.xml" --as user
```

从 `data.new_blocks` 中找到 `block_type=="whiteboard"` 的 `block_token`，记为本次运行的 `BOARD_TOKEN`。已有文档或旧白板 token 立即 `STOP`。

## 6. 上传图片到白板域

```powershell
python "$skillDir\scripts\upload_to_board.py" --images-dir ".\images_<brand>" --board-token "<BOARD_TOKEN>" --out ".\token_map_<brand>.json"
```

每个 token 必须来自本次 `docs +media-upload --parent-type whiteboard --parent-node <BOARD_TOKEN>`。不得把 Amazon URL、Base 附件 token 或其他域 token 写入 `image.src`。

## 7. 生成分组和 DSL

```powershell
python "$skillDir\scripts\make_groups.py" --rows ".\rows_<brand>.json" --out ".\groups_<brand>.json"
python "$skillDir\scripts\build_dsl.py" --rows ".\rows_<brand>.json" --token-map ".\token_map_<brand>.json" --root-label "<BRAND>" --root-sub "在售产品分布 · N款" --groups ".\groups_<brand>.json" --out ".\diagram_<brand>.json"
npx -y "@larksuite/whiteboard-cli@^0.2.13" -i ".\diagram_<brand>.json" --check
npx -y "@larksuite/whiteboard-cli@^0.2.13" -i ".\diagram_<brand>.json" -t openapi -F json -o ".\openapi_<brand>.json"
```

`--check` 非零或有 errors 时 `STOP`。

## 8. 写板和预览

```powershell
lark-cli whiteboard +update --whiteboard-token "<BOARD_TOKEN>" --source "@.\openapi_<brand>.json" --input_format raw --overwrite --idempotent-token "<brand>-v1" --as user
Start-Sleep -Seconds 25
lark-cli whiteboard +export --whiteboard-token "<BOARD_TOKEN>" --output-type preview --output ".\preview_<brand>" --as user
```

`+update` 前再次核对目标是本次新建白板；写入或导出失败保留 `diagram_<brand>.json`、`openapi_<brand>.json` 和 checkpoint。

## 9. Base 备用流程

仅当用户提供真实 Base URL、table ID 和字段 ID 时使用：

```powershell
python "$skillDir\scripts\pull_base.py" --base-url "<base_url>" --brand-field "<brand_field_id>" --brand-value "<品牌>" --status-field "<status_field_id>" --field-id-list "@.\field_ids.json" --out ".\raw.json" --checkpoint ".\checkpoints\base.json"
```

不得凭品牌名猜 Base 或字段；分页失败、响应形状未知或记录数突变时 `STOP`。

## 10. 失败恢复矩阵

| 阶段 | 停止条件 | 保留物 | 恢复动作 |
|---|---|---|---|
| SellerSprite/Base | 凭据、权限、分页或响应错误 | 原始 JSON、日志、checkpoint | 修复输入/凭据后从最近步骤恢复 |
| Docs | create 失败、文档已存在、block 缺失 | 文档 ID、checkpoint | 不重建已有文档，核对输入后重试 |
| Whiteboard | token 域错误、check/update/export 失败 | DSL、OpenAPI、预览 | 核对本次 BOARD_TOKEN 后从失败步骤恢复 |

## 11. 本地自动同步

自动同步脚本位于插件根目录的 `scripts\auto_sync.ps1`。它监听整个 Git 工作区，去抖后提交并推送到 `origin/main`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$pluginDir\scripts\auto_sync.ps1" -InstallTask
```

冲突、凭据失败或远端拒绝时只记录 `STOP`，不会 force-push、reset 或自动解决冲突。日志位于 `$env:LOCALAPPDATA\brand-product-map-auto-sync.log`。卸载登录启动任务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$pluginDir\scripts\auto_sync.ps1" -UninstallTask
```

