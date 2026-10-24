---
name: brand-product-map
description: >
  按品牌从 SellerSprite MCP 或用户提供的飞书 Base 拉取 Amazon 在售产品，整理标准化 Excel，
  并新建独立飞书文档与产品分布画板。适用于品牌产品清单、Base 在售产品、产品墙、产品架构图、
  产品分布图、品牌 Excel、Amazon 品牌可视化和在线画板；不适用于竞品调研、外部爬虫、单纯
  Excel 格式编辑、无来源的臆测清单或无关的已有画板设计修改。
---

# Brand Product Map（品牌产品调研 + 在线分布图）

## 适用范围与边界

- **输入**：Amazon 品牌名（SellerSprite 主流程），或包含字段 ID 的飞书 Base URL（Base 备用流程）。
- **输出**：标准化 `.xlsx`、口径说明，以及一篇新建的独立飞书文档和白板产品分布图。
- 每个品牌必须新建独立文档与白板；不得复用、删除或默认覆写已有 `board_token`。
- 缺失销量、容量、评分或图片时保留空值并记录口径，不臆造或填零。

## Checkpoint 与 STOP 规则

在项目数据目录建立 `checkpoints/`；每步完成后写入 `<step>.done.json`，记录输入、输出、时间和远程资源 ID。外部写入前必须存在可核对的本地产物。

遇到以下任一情况立即输出 **`STOP`**，保留现场并报告最后成功步骤与恢复命令：

- SellerSprite/Base/Docs/Whiteboard 返回错误、认证失败、权限不足、CAPTCHA 或限流；
- 凭据缺失、分页响应形状未知、空页伴随 `has_more=true`、记录数突变或字段无法映射；
- 目标文档/白板已存在、token 域不正确，或 `whiteboard-cli --check` 报错；
- 任一步产物缺失。禁止把失败页、空响应或缺失字段当作成功继续。

修复输入或权限后从最近 checkpoint 恢复；不要删除 checkpoint、扩大重试、force-push 或重置远端。

## 主流程（SellerSprite MCP）

以下脚本路径相对本 skill 目录 `skills/brand-product-map`；详细 PowerShell 模板见 [`references/workflow.md`](references/workflow.md)。

1. **拉取产品**：`python scripts/sp_fetch.py --brand "<Brand>" --out "$projectDir\brand_products.json"`。
   通过 SellerSprite Streamable HTTP 的 `competitor_lookup` 分页拉全量并按月销排序。凭据只从 `SELLERSPRITE_KEY` 或运行时 `--key` 读取，绝不写入仓库或日志。
2. **清洗规整**：`python scripts/clean_mcp.py --raw ... --out ...`，提取容量、包装、品类并剔除明显非目标品类；逐品牌拆出 `rows_<brand>.json`。
3. **生成 Excel**：`python scripts/build_excel.py --rows rows_<brand>.json --out "<Brand>在售产品整理.xlsx" --brand "<Brand>"`。
4. **下载产品图**：`python scripts/download_images.py --rows rows_<brand>.json --out-dir images_<brand>`；失败写入 `_failed.txt`，不得用空图继续。
5. **新建独立文档和空白白板**：在获得本次操作授权后执行 `docs +create`，从返回的 whiteboard block 取得本次 `BOARD_TOKEN`。
6. **上传白板图片**：`python scripts/upload_to_board.py --images-dir images_<brand> --board-token <BOARD_TOKEN> --out token_map_<brand>.json`；`image.src` 只能使用本次 whiteboard media upload 返回的 token。
7. **生成分组和 DSL**：运行 `scripts/make_groups.py`、`scripts/build_dsl.py`，生成品类列、卡片和曲线连接。
8. **校验、写板和预览**：先运行 `whiteboard-cli --check`；确认是本次新建白板后再转换 OpenAPI、`+update` 和 `+export`。写入前的核对失败即 STOP。
9. **交付前校验 Excel**：`python scripts/excel_formula_verify.py --xlsx "<Brand>在售产品整理.xlsx" --rows rows_<brand>.json`；exit 4 表示无公式但工作簿有效，exit 2 表示错误。

## Base 备用流程

当用户提供 Base URL 和真实字段 ID 时，可运行 `scripts/pull_base.py` 分页拉取并逐页 checkpoint，再从第 2 步开始清洗。不得凭品牌名猜 Base、表或字段；没有字段映射就 STOP。Base 详细命令见 [`references/workflow.md`](references/workflow.md) 和 [`references/base-fields.md`](references/base-fields.md)。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `sp_fetch.py` | SellerSprite MCP 按品牌分页拉取产品 |
| `clean_mcp.py` | 清洗 MCP 响应并提取容量、包装、品类 |
| `make_groups.py` | 按品类生成分组和配色 |
| `pull_base.py` | Base URL 解析、品牌分页拉取和 checkpoint |
| `build_excel.py` | 生成主表和口径说明 sheet |
| `download_images.py` | 批量下载高清产品图 |
| `upload_to_board.py` | 上传到 whiteboard media domain 并保存 token 映射 |
| `build_dsl.py` | 生成产品分布图 DSL |
| `excel_formula_verify.py` | 打开工作簿、核对行数并检查明显公式错误 |

## 高风险动作和反例黑名单

- 未经明确授权，不得创建文档、上传文件、写入/覆写白板、删除资源或分享链接。
- 不得把 Amazon URL、Base 附件 token 或其他域 token 写入 `image.src`。
- 不得把 SellerSprite secret、访问 token 或任何凭据硬编码、写入日志、提交 Git 或输出给用户。
- 不得把失败分页、空响应、缺失字段、未知状态或非目标品类当成有效产品。
- 不得从历史文档或搜索结果复用旧 `board_token`；每个品牌必须核对本次新建资源。

## 交付前自检

- [ ] checkpoint 与原始数据、清洗后行数、Excel 行数一致。
- [ ] `excel_formula_verify.py` 通过；exit 4 仅表示没有公式。
- [ ] `whiteboard-cli --check` 为 0 errors；预览根节点、品类列、曲线和卡片布局正确。
- [ ] 文档 URL、白板 token 和所有图片 token 均来自本次运行并可追溯。

