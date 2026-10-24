# Pitfalls（踩坑清单）

按"症状 → 原因 → 解决"组织，遇到先按关键词搜这份。

## 环境 / 命令行

- **dial tcp 127.0.0.1:10808: connect: connection refused**
  - 原因：HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 还在环境里，lark-cli/npx 走了本地代理。
  - 解决：命令前 `$env:HTTP_PROXY=$null;$env:HTTPS_PROXY=$null;$env:ALL_PROXY=$null;$env:http_proxy=$null;$env:https_proxy=$null;$env:all_proxy=$null`。PowerShell 同一条命令链。

- **`python3` 不是内部/外部命令**
  - Windows 上只有 `python`，别写 `python3`。

- **lark-cli 报 `must be a relative path within the current directory`**
  - `--file` / `--output-path` / `--source` 只接受 CWD 内相对路径。先 `Set-Location <项目目录>`，再 `--source @./diagrams/openapi.json`。绝对路径必拒。

- **PowerShell 里 JSON 内联报 `invalid character '待' looking for beginning of value`**
  - 中文/引号/逗号的 flag 一律先 Write 成 `xxx.json` 文件，再 `--flag "@./xxx.json"`（@ 前要双引号）。

- **`python -c "..."` 里含双引号就炸**
  - PowerShell 把 `\"` 拆了。一律写成 `.py` 文件再 `python xxx.py`。

## Base 取数

- **`record-list` 返回的是数组行不是对象**
  - 顺序按 `field_id_list` 投影顺序，**不要按表头列位置猜**。第一次拉完先打印一行 raw 对照 field_id。
- **分页**：`--limit 200 --offset <上一次 data 长度>`，直到 `has_more=false`。47 条这种小表也别信"就一页"。

## 产品图下载

- **Amazon 图模糊 / 小图**
  - URL 里 `_AC_US200_` 改成 `_AC_SL1200_` 就是高清；其他后缀（`_SY300_`/`_SS400_`）同理换大尺寸。
- **下载失败 / 0 字节**
  - 清代理后用 `python urllib.request.urlretrieve` 直连；不要 curl，PowerShell 别名走的是 `Invoke-WebRequest` 行为不同。
- **没 PIL / pillow**
  - 宿主无 PIL，别写依赖 PIL 的脚本。

## 画板 DSL / 写入

- **`image.src` 填了 Amazon URL / Base 附件 file_token → 500 (code 2891001)**
  - 必须先 `docs +media-upload --parent-type whiteboard --parent-node <board_token> --file ./x.jpg`，拿到 whiteboard 域 file_token，DSL 里 `image.src` 用它。
- **connector 嵌在 frame.children 里 → 线不显示 / 位置错乱**
  - connector 必须放顶层 `nodes` 数组，和 frame 平级。
- **`fontWeight:"bold"` 写在 text 节点里无效**
  - 飞书 DSL v2 的 text 节点不认 fontWeight（本地渲染会被吞）。要粗体用富文本（`textType:"rich"` + `<b>`），或者接受默认 regular。
- **mermaid `graph LR` / `mindmap` 被强制竖向**
  - 飞书画板对 mermaid 有 layout 强制。要横向长图必须 DSL 手写 frame/connector。
- **本地渲染 PNG 图片全裂成占位块**
  - 正常。云端 token 本地拉不到。只看布局/文字/连线/间距。
- **`+update --input_format raw` 整板重建**
  - 已经有内容的板要 `--overwrite`；只想追加新元素别用 raw，走 append 路径。
- **`--idempotent-token` 最少 10 字符**
  - 用 `<brand><date><seq>`，如 `natboard20261022a`。

## 导出核对

- **`+export --output-type preview --output ./live.png` 报 `extension mismatch`**
  - 返回是 jpg。`--output` 只给前缀 `./live`，让 CLI 自己加扩展名。
- **导出的图还是旧版 / 产品图没更新**
  - CDN 缓存。写完 sleep 20~30s 再导；看返回的 `size_bytes` 是否变了。
- **导出图里图片位置空白但布局对**
  - 同上，缓存没刷新。

## Excel

- **`excel_formula_verify.py` 退出码 4**
  - 宿主没装 LibreOffice，重算跑不了。**无公式表这是正常终态**，别反复修。
- **金额被 Excel 识别成文本**
  - openpyxl 写 `cell.number_format = '"$"#,##0.00'`；空值留 None 不要写 0。
