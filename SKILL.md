---
name: brand-product-map
description: >
  从飞书多维表格(Base)按品牌拉取在售产品清单，整理成标准化Excel（含销量/销售额/容量/评分/ASIN/链接），
  并新建一篇独立飞书文档、内嵌一张自上而下曲线连线的产品分布画板（根节点=品牌名居中置顶，按品类分列，
  每款产品卡片带高清主图+规格+价格+月销量+评分）。适用于"整理某品牌在售产品""做个产品分布图/产品墙/
  产品架构图""按品牌出Excel并配套在线画板""把Base里某品牌产品可视化"等任务。
  明确区分同Base内的不同子品牌（如EnaSkin vs Enaskin Naturals）。触发词包括品牌产品清单、Base在售产品、产品墙、产品架构图、产品分布图、品牌Excel和在线画板；不适用于竞品调研、外部爬虫、单纯Excel格式编辑、无Base来源的臆测清单或已有画板的无关设计修改。
---

# Brand Product Map（品牌产品调研 + 在线分布图）

## 适用范围与边界

- **输入**：飞书 Base 链接（含品牌/产品/销量/图片等字段）+ 目标品牌名。
- **输出**：
  1. 本地 `.xlsx`：主表（序号/产品名/容量规格/包装/价格/SS月销量/SS月销售额/评分/评论数/品类/ASIN/链接）+ 口径说明 sheet；
  2. 一篇新建的独立飞书文档，内嵌一块画板：品牌根节点居中置顶 → 曲线连到各品类列 → 每款产品一张带图卡片。
- **不做**：不覆写已有画板；不替用户判断"哪些产品该上画板"（默认全部在售，数量极多时先问）；不做竞品/外部爬取。

## 总流程（8 步，带 checkpoint）

每一步完成后写入 `checkpoints/<step>.done.json`，记录输入、输出和时间；恢复时从最近的未完成步骤继续。任何外部写入前都必须有本地可核对产物。

**STOP 标记**：认证/权限/CAPTCHA/限流、Base/Docs/Whiteboard 返回错误、分页响应形状未知、记录数突变、目标文档或画板已存在、图片 token 域不正确时立即停止；保留产物与 checkpoint，报告最后成功步骤和恢复命令，禁止用空数据继续。

1. **解析 Base**：`lark-cli base +url-resolve --url "<base_url>" --as user`，拿到 `base_token` / `table_id` / `view_id`。
2. **按品牌分页拉全量**：`lark-cli base +record-list`，`--filter-json` 按品牌字段筛，`--limit 200 --offset <n>` 直到 `has_more=false`。投影列用 field_id，**不要凭列位置对齐**。
3. **清洗规整**：状态只收"在售"；"在售(待抽查)/待核实/缺货/已下架"在口径说明里列出但不入主表；同产品不同容量/包装**逐行分开**；容量/包装缺失留空不臆造。
4. **生成 Excel**：用 `scripts/build_excel.py`（openpyxl），列结构固定，附口径说明 sheet。
5. **下载高清产品图**：用 `scripts/download_images.py`，Amazon `_AC_US200_` 替换为 `_AC_SL1200_` 拉高清，失败回退原 URL；每条 >3KB 才算成功。
6. **新建文档+空白画板**：`docs +create --title "<品牌>在售产品分布图" --content '<whiteboard type="blank"></whiteboard>'`，从 `new_blocks[0].block_token` 取 `board_token`。
7. **图片上传到画板域**：`docs +media-upload --file ./xxx.jpg --parent-type whiteboard --parent-node <board_token> --as user` 逐张上传，收集 `file_token` 映射。**非 whiteboard 域 token 会 500 (2891001)**。
8. **生成 DSL → 写板 → 核对**：用 `scripts/build_dsl.py` 产 `diagram.json`；`npx @larksuite/whiteboard-cli --to openapi` 转格式；`whiteboard +update --input_format raw --overwrite` 写入；`+export --output-type preview` 导出 PNG 核对。

## 关键环境硬约束（必读 references/pitfalls.md）

- **每次调 lark-cli / npx 前清空代理**：`HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`（含大小写）全设 `$null`，否则 dial 127.0.0.1:10808 拒绝。
- **Windows 用 `python` 不是 `python3`**；PowerShell 单命令、`@file` 相对路径、中文/JSON 落文件内联会炸。
- **画板 image.src 必须是 whiteboard 域 media token**（`docs +media-upload --parent-type whiteboard --parent-node <board>`），不能直接用 Amazon URL 或 Base 附件 file_token。
- **connector 必须放在顶层 `nodes` 数组**，不能嵌在 frame.children 里。
- **本地渲染 PNG 拉不到云端图是正常的**（图片裂成占位块），布局/文字对就行；真图只能在飞书线上看。
- **`+export --output-type preview` 返回 jpg，`--output` 不要写 .png**（会报 extension mismatch），只给前缀让 CLI 自己加扩展名。
- **preview 有 CDN 缓存**：写入后 sleep 20~30s 再导，`size_bytes` 变了才是新图。
- **mermaid LR/mindmap 在飞书画板会被强制竖向**，别用；直接走 DSL + whiteboard-cli。

## 脚本一览（scripts/）

| 脚本 | 作用 | 关键参数 |
|---|---|---|
| `pull_base.py` | 按品牌从 Base 分页拉全量在售记录，落 `raw.json` 并逐页 checkpoint | base-url, brand-field, brand-value, status-field, field-id-list |
| `build_excel.py` | 规整后产 `.xlsx`（主表+口径说明），列结构固定 | input_rows.json, output.xlsx, brand_name |
| `download_images.py` | Amazon URL 高清化批量下载到 `images/` | rows.json, out_dir |
| `upload_to_board.py` | 逐张 `docs +media-upload` 到目标画板，落 `token_map.json`，可断点续传 | images-dir, board-token |
| `build_dsl.py` | 产 `diagram.json`：根节点居中+品类分列+曲线连线+产品卡片 | rows.json, token_map.json, groups, root_label |

详细字段映射、分组配色、踩坑清单见 `references/`。

## 分组与配色约定（可覆写）

- 经典 5 色循环：蓝 `#5178C6/#F0F4FC`、紫 `#8569CB/#EAE2FE`、绿 `#509863/#DFF5E5`、黄 `#D4B45B/#FEF1CE`、红 `#D25D5A/#FEE3E2`。
- 根节点：深色 `#1F2329` 底 + 白字，居中置顶，高度 fit-content。
- 连线：`lineShape:"curve"`、`lineColor:"#BBBFC4"`、`lineWidth:2`、`endArrow:"none"`，`fromAnchor:"bottom"` → `toAnchor:"top"`。
- 产品卡片：白底 + 品类色边框 2px + 圆角 8；左 60×60 图，右两行文字（规格+价格 / 月销+评分）。
- 一列产品 >10 款时按品类再拆列，保证整图扁宽（横:高 ≈ 1.3:1，方便塞进 PPT）。

## 交付前自检

- [ ] Excel 行数 = 在售条数；缺失销量/容量留空而非 0；口径说明列出被剔除的状态。
- [ ] 画板导出预览：根节点居中、6 列（或自定义列）对齐、曲线不穿卡片、每张产品图都真图。
- [ ] 文档 URL 可访问，board_token 写入成功（`+update` 返回 ok）。
- [ ] 若环境提供 `excel_formula_verify.py` 则运行；本仓库未内置该脚本。否则用 `python -c` 之外的独立检查确认文件可被 openpyxl 打开、主表行数与 rows.json 一致。

## 高风险动作与反例黑名单

- 未经明确授权，不得用 `--overwrite` 覆写已有画板，不得删除/移动已有文档，不得批量发送或分享链接。
- 不得把 Amazon URL、Base 附件 token 或其他域 token 写入 `image.src`；必须先上传到 whiteboard media domain 并核验。
- 不得把分页失败、空响应、缺失字段当作零值或成功；不得凭品牌名猜测 Base 字段、产品列表或历史销量。
- 遇到登录/CAPTCHA/限流时 STOP，不得重试放大请求；修复后从 checkpoint 恢复。
