"""Fetch all products for a brand from SellerSprite MCP (Streamable HTTP).

Endpoint: https://mcp.sellersprite.com/mcp
Auth header: secret-key: <KEY>  (NOT Bearer; Bearer returns secret_invalid)
Protocol: initialize (2025-06-18) -> notifications/initialized -> tools/call

Usage:
  python sp_fetch.py --brand "Rootstim" --out brand_products.json
  # key read from env SELLERSPRITE_KEY or fallback default
"""
import argparse, json, os, ssl, sys, urllib.request

DEFAULT_KEY = "0b75c9d94aa84918b07e10b96ac9c32e"
ENDPOINT = "https://mcp.sellersprite.com/mcp"

def clear_proxy():
    for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        os.environ.pop(k, None)

def post(payload, key, session_id=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "secret-key": key,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    data = json.dumps(payload).encode("utf-8")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(ENDPOINT, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        sid = resp.headers.get("Mcp-Session-Id")
    # SSE: lines starting with "data:"
    if body.startswith("event:") or "\ndata:" in body or body.startswith("data:"):
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip()), sid
        return {}, sid
    return json.loads(body), sid

def call_tool(name, args, key):
    payload = {
        "jsonrpc":"2.0","id":1,"method":"tools/call",
        "params":{"name":name,"arguments":args}
    }
    return post(payload, key)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--marketplace", default="US")
    ap.add_argument("--out", default="brand_products.json")
    ap.add_argument("--key", default=os.environ.get("SELLERSPRITE_KEY", DEFAULT_KEY))
    args = ap.parse_args()

    clear_proxy()

    # 1. initialize (stateless endpoint: no Mcp-Session-Id returned)
    init = {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18",
        "capabilities":{},
        "clientInfo":{"name":"brand-product-map","version":"1.0"}
    }}
    post(init, args.key)

    # 2. initialized notification (fire and forget)
    notif = {"jsonrpc":"2.0","method":"notifications/initialized"}
    try:
        post(notif, args.key)
    except Exception:
        pass

    # 3. call competitor_lookup paginated
    all_items = []
    page = 1
    total = None
    while True:
        result, _ = call_tool("competitor_lookup", {
            "request":{
                "marketplace": args.marketplace,
                "brand": args.brand,
                "variation": "Y",
                "page": page,
                "size": 100,
                "order": {"field":"total_units","desc": True}
            }
        }, args.key)
        text = ""
        if "result" in result:
            content = result["result"].get("content", [])
            for c in content:
                if c.get("type") == "text":
                    text = c["text"]
                    break
        try:
            data = json.loads(text)
        except Exception:
            print(f"ERROR: cannot parse: {text[:300]}", file=sys.stderr); sys.exit(1)

        inner = data.get("data") or {}
        items = inner.get("items") or []
        if total is None:
            total = inner.get("total", 0)
        all_items.extend(items)
        print(f"  page {page}: got {len(items)}, cumulative {len(all_items)}/{total}", flush=True)
        if len(all_items) >= total or not items:
            break
        page += 1

    json.dump({args.brand: all_items}, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: {len(all_items)} products for {args.brand}")

if __name__ == "__main__":
    main()
