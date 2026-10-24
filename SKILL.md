---
name: brand-product-map
description: >
  从一个品牌名出发，自动通过卖家精灵 MCP 拉取 Amazon 在售产品（含销量/销售额/评分/主图），
  整理成标准化 Excel，并新建一篇独立飞书文档 + 内嵌一张自上而下曲线连线的产品分布画板
  （根节点=品牌名居中置顶，按品类分列，每款产品卡片带高清主图+规格+价格+月销+评分）。
  适用于"整理某品牌在售产品""做个产品分布图/产品墙/产品架构图""按品牌出 Excel 并配套在线画板"
  "把 Amazon 品牌可视化"等任务。每个品牌必须新建独立文档+画板，禁止覆写旧画板。
---

# Brand Product Map（品牌产品调研 + 在线分布图）

## 输入与输出

- **输入**：一个 Amazon 品牌名（如 `Rootstim`、`Maravello`、`EnaSkin`）。
- **输出**：
  1. 本地 `.xlsx`：主表（序号/产品名/容量规格/包装/价格/月销量/月销售额/评分/评论数/品类/ASIN/链接）+ 口径说明 sheet；
  2. 一篇新建的独立飞书文档，内嵌一块画板：品牌根节点居中置顶 → 曲线连到各品类列 → 每款产品一张带图卡片。
- **边界**：每个品牌必须 `docs +create` 新建独立文档+画板，绝不复用/覆写任何已有 board_token；非护发品类（如串品牌的家居清洁品）自动剔除并在口径说明里列出。

## 总流程（9 步）

工作目录建议新建 `brand_work/`，所有中间产物落这里。

1. **拉产品**：`python scripts/sp_fetch.py --brand "<Brand>" --out brand_products.json`
   - 自动走卖家精灵 MCP Streamable HTTP 握手，按 `competitor_lookup` 分页拉全量，按月销降序。
   - 认证、endpoint、字段说明见 `references/sellersprite-mcp.md`。
2. **清洗规整**：`python scripts/clean_mcp.py --raw brand_products.json --out rows.json`
   - 自动提取容量（Fl Oz / mL / Pairs）、包装数（Pack of N）、品类（米诺地尔溶液/喷雾/泡沫、洗发水、护发素、洗护套装、护发精华/油、其他）。
   - 串品牌的非目标品类（如 garbage disposal cleaner）自动剔除。
   - `rows.json` 里每个 key 是品牌名，value 是标准化行数组。拆出单品牌：`json.dump(rows["<Brand>"], open("rows_<brand>.json","w",encoding="utf-8"), ensure_ascii=False)`。
3. **生成 Excel**：`python scripts/build_excel.py --rows rows_<brand>.json --out "<Brand>在售产品整理.xlsx" --brand "<Brand>"`
4. **下载高清产品图**：`python scripts/download_images.py --rows rows_<brand>.json --out-dir images_<brand>`
   - Amazon `_AC_US200_/_SS200_/_SY200_` 自动替换成 `_AC_SL1200_` 拉高清。
5. **新建独立文档+空白画板（强制）**：
   - 先写 `wb_content.xml` 内容为 `<whiteboard type="blank"></whiteboard>`；
   - `lark-cli docs +create --title "<Brand>在售产品分布图" --content "@./wb_content.xml" --as user`；
   - 从 `data.new_blocks[0].block_token` 取 `board_token`（block_type=whiteboard）。
   - **禁止复用任何已有 board_token、禁止往旧画板 +update --overwrite**。
6. **图片上传到画板域**：`python scripts/upload_to_board.py --images-dir images_<brand> --board-token <BOARD_TOKEN> --out token_map_<brand>.json`
   - image.src 必须是 whiteboard 域 file_token；用 Amazon URL 或 Base 附件 token 会 500。
7. **生成分组 + DSL**：
   - `python scripts/make_groups.py --rows rows_<brand>.json --out groups_<brand>.json`（按品类自动分列，配色循环）；
   - `python scripts/build_dsl.py --rows rows_<brand>.json --token-map token_map_<brand>.json --root-label "<BRAND>" --root-sub "在售产品分布 · N款" --groups groups_<brand>.json --out diagram_<brand>.json`。
8. **校验 → 转 OpenAPI → 写板**：
   - `npx -y @larksuite/whiteboard-cli@^0.2.13 -i diagram_<brand>.json --check`（必须 0 errors）；
   - `npx -y @larksuite/whiteboard-cli@^0.2.13 -i diagram_<brand>.json -t openapi -F json -o openapi_<brand>.json`；
   - `lark-cli whiteboard +update --whiteboard-token <BOARD_TOKEN> --source "@./openapi_<brand>.json" --input_format raw --overwrite --idempotent-token "<brand>-v1" --as user`。
9. **导出预览核对**：`Start-Sleep 25` 后 `lark-cli whiteboard +export --whiteboard-token <BOARD_TOKEN> --output-type preview --output preview_<brand> --as user`。

## 关键环境硬约束

- **每次调 lark-cli / npx / sp_fetch 前清空代理**：`$env:HTTP_PROXY=$null;$env:HTTPS_PROXY=$null;$env:ALL_PROXY=$null`，否则 dial 127.0.0.1 拒绝。
- **Windows 用 `python` 不是 `python3`**；PowerShell 单命令、`@file` 相对路径、中文/JSON 落文件内联会炸。
- **画板 DSL schema（2025-10 版）**：
  - rect 用 `fillColor/borderColor/borderWidth/borderRadius`（不是 fill/border/radius）；
  - text 用 `textColor/textAlign/verticalAlign`（不是 color/align）；
  - image 是 `{"type":"image","image":{"src":"<file_token>"}}`（不是 src 平级）；
  - connector 是 `{"type":"connector","connector":{"from":id,"to":id,"fromAnchor":"bottom","toAnchor":"top","lineShape":"curve","lineColor":"#BBBFC4","lineWidth":2,"endArrow":"none"}}`，**必须放顶层 nodes 数组**。
- **preview 导出 jpg**，`--output` 只给前缀，不要写扩展名；写入后 sleep 20~30s 再导。
- **mermaid LR/mindmap 在飞书画板会被强制竖向**，别用；直接走 DSL + whiteboard-cli。
- 本地渲染 PNG 拉不到云端图是正常的，真图只能在飞书线上看。

## 脚本一览（scripts/）

| 脚本 | 作用 |
|---|---|
| `sp_fetch.py` | 卖家精灵 MCP 按品牌分页拉全量产品 → `brand_products.json` |
| `clean_mcp.py` | 清洗 MCP 数据 → `rows.json`（含 capacity/pack/category 提取） |
| `make_groups.py` | 按品类自动生成分组配色 `groups.json` |
| `build_excel.py` | 产 `.xlsx`（主表+口径说明） |
| `download_images.py` | Amazon 主图高清化批量下载 |
| `upload_to_board.py` | 逐张 `docs +media-upload` 到目标画板，落 token_map.json |
| `build_dsl.py` | 产 `diagram.json`：根节点居中+品类分列+曲线连线+产品卡片（新 schema） |

## 交付前自检

- [ ] board_token 是本次 `docs +create` 新建出来的，不是从历史对话捞的。
- [ ] Excel 行数 = 清洗后在售条数；口径说明列出被剔除的非目标品类。
- [ ] `whiteboard-cli --check` 报 0 errors / 0 warnings。
- [ ] `whiteboard +update` 返回 ok，created_node_ids 数量与 DSL nodes 数一致。
- [ ] 文档 URL 可访问，预览导出 jpg 正常。
