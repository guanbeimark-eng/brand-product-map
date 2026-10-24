# Base 字段映射参考

> 本表是 ytbdtrade 子体表的真实字段。新品牌/新表先用 `base +field-list` 重新拉一遍，别硬套这里的 ID。

## 表结构

- base_token: `XHKRb6WyTaDLuFsSDmzlsHeXgxh`
- table_id: `tblSM9v2SV8b2PQp`（表名"子体表"）
- view_id: `vews8VSHhs`

## 字段 ID → 含义

| field_id | 字段名 | 类型 | 说明 |
|---|---|---|---|
| fldGObUWsi | 品牌 | 单选 | EnaSkin / Enaskin Naturals |
| fldQzLFz0c | 状态 | 单选 | 在售 / 在售(待抽查) / 待核实 / 缺货 / 已下架 |
| fldsnNS9at | 产品名 | 文本 | |
| fldvETDAgA | 图片原始链接 | URL | Amazon 图 URL |
| fldIa8Dtdx | SS子体月销量 | 数字 | |
| fldRwM5ZGD | 价格 | 数字 | USD |
| fldFsiGoBQ | SS子体月销售额 | 数字 | USD |
| fldylziDCI | 评分 | 数字 | 0~5 |
| fldLjDKsoF | ASIN | 文本 | |
| fldIRWAoxv | 规格 | 文本 | 容量/数量，如 `120 Pairs/Pcs` `100 mL` `1.8 Oz` |
| fldRlp37YQ | 品类 | 文本 | 用于画板分列 |
| fldry4smi1 | 变体属性 | 文本 | 含 `Pack of N` / `N Pack` / `+` 组合套装 |
| fldQvmaeB8 | 评论数 | 数字 | |
| fldy6K0WAo | 链接 | URL | 商品详情页 |
| fldTsHyhWA | 主图附件 | 附件 | 备用，优先用 fldvETDAgA 高清化 |

## 拉数命令模板

```powershell
# 1. 解析
lark-cli base +url-resolve --url "<base_url>" --as user

# 2. 分页拉（--filter-json 落文件避免引号问题）
# filter.json:
#   {"conjunction":"and","conditions":[
#     {"field_id":"fldGObUWsi","operator":"is","value":["Enaskin Naturals"]},
#     {"field_id":"fldQzLFz0c","operator":"is","value":["在售"]}
#   ]}
lark-cli base +record-list \
  --base-token XHKRb6WyTaDLuFsSDmzlsHeXgxh \
  --table-id tblSM9v2SV8b2PQp \
  --filter-json "@./filter.json" \
  --field-id-list '["fldsnNS9at","fldvETDAgA","fldIa8Dtdx","fldRwM5ZGD","fldFsiGoBQ","fldylziDCI","fldLjDKsoF","fldIRWAoxv","fldRlp37YQ","fldry4smi1","fldQvmaeB8","fldy6K0WAo"]' \
  --limit 200 --offset 0 --as user
```

## 规整规则

- 同产品不同容量/包装**逐行拆开**，不要合并；评分取子体自身值。
- 包装数从 `变体属性` 正则抓 `Pack of (\d+)` / `(\d+) Pack`；含 `+` 判为 2 Pack 组合套装。
- 无估算销量/销售额的格子留空（None），**不要填 0**。
- 状态过滤：只收"在售"；"在售(待抽查)"、"待核实"等在 Excel 口径说明 sheet 里列出。
