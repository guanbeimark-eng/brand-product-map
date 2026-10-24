# 卖家精灵 MCP 接入说明

## Endpoint & Auth

- URL: `https://mcp.sellersprite.com/mcp`
- Method: POST, Content-Type: application/json, Accept: application/json, text/event-stream
- 认证 header: `secret-key: 0b75c9d94aa84918b07e10b96ac9c32e`
- **不要用** `Authorization: Bearer ...` —— Bearer 会返回 `secret_invalid`
- **不要用** `https://api.sellersprite.com/v1/...` 这个 REST 域名 —— 同一 key 会返回 `ERROR_UNAUTHORIZED`

## MCP 协议顺序（Streamable HTTP，无状态）

1. `initialize`（protocolVersion 2025-06-18）→ 返回 capabilities，但**不返回 `Mcp-Session-Id` header**（该 endpoint 是无状态的）
2. `notifications/initialized` 通知（fire and forget）
3. `tools/call` 直接调，不需要带 session id

响应是 SSE：找 `data:` 开头的行，parse JSON。

## 拉品牌全量产品

工具名：`competitor_lookup`

arguments:
```json
{
  "request": {
    "marketplace": "US",
    "brand": "Rootstim",
    "variation": "Y",
    "page": 1,
    "size": 100,
    "order": {"field": "total_units", "desc": true}
  }
}
```

返回 `result.content[0].text` 是 JSON string，parse 后：
- `data.data.items` — 产品数组
- `data.data.total` — 总数

## 产品字段

- asin, brand, title, imageUrl, parent
- price, units（月销件数）, revenue（月销售额 USD）
- rating（评分 0-5）, ratings（评论数）
- sku（变体属性，如 `Size: 2 Fl Oz (Pack of 2)`）
- variations（变体总数）
- nodeLabelPath（品类路径）, bsr

## 脚本

- `scripts/sp_fetch.py --brand "<Brand>" --out brand_products.json` — 自动 initialize + 分页拉全量
- key 默认硬编码在脚本里，可用 `--key` 或环境变量 `SELLERSPRITE_KEY` 覆盖
