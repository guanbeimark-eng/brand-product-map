"""Resolve a Lark Base URL and page records for one brand.

This is a thin, resumable wrapper around lark-cli. It writes a checkpoint after
each page and never silently treats a failed page as an empty page.
"""
import argparse, json, os, subprocess, sys

def run(cmd):
    env = os.environ.copy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(k, None)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr[-2000:]}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"lark-cli returned non-JSON output: {p.stdout[-1000:]}") from e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--brand-field", required=True)
    ap.add_argument("--brand-value", required=True)
    ap.add_argument("--status-field", required=True)
    ap.add_argument("--status-filter", default="在售")
    ap.add_argument("--field-id-list", required=True, help="JSON array or @file.json")
    ap.add_argument("--out", default="raw.json")
    ap.add_argument("--checkpoint", default="raw.checkpoint.json")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    fields = json.load(open(args.field_id_list[1:], encoding="utf-8")) if args.field_id_list.startswith("@") else json.loads(args.field_id_list)
    resolved = run(["lark-cli", "base", "+url-resolve", "--url", args.base_url, "--as", "user"])
    d = resolved.get("data", resolved)
    base = d.get("base_token") or d.get("app_token")
    table = d.get("table_id") or d.get("table_token")
    if not base or not table:
        raise RuntimeError("url-resolve did not return base_token/app_token and table_id/table_token")
    filt = {"conjunction":"and", "conditions":[
        {"field_id":args.brand_field,"operator":"is","value":[args.brand_value]},
        {"field_id":args.status_field,"operator":"is","value":[args.status_filter]}]}
    all_rows, offset = [], 0
    while True:
        page = run(["lark-cli", "base", "+record-list", "--base-token", base, "--table-id", table,
                    "--filter-json", json.dumps(filt, ensure_ascii=False), "--field-id-list", json.dumps(fields),
                    "--limit", str(args.limit), "--offset", str(offset), "--as", "user"])
        pd = page.get("data", page)
        rows = pd.get("items", pd.get("records", pd if isinstance(pd, list) else []))
        if not isinstance(rows, list):
            raise RuntimeError("record-list response has no list of items/records")
        all_rows.extend(rows)
        more = bool(pd.get("has_more", False)) if isinstance(pd, dict) else False
        offset += len(rows)
        json.dump({"base_token":base,"table_id":table,"offset":offset,"rows":all_rows}, open(args.checkpoint,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        if not more: break
        if not rows: raise RuntimeError("has_more=true with empty page; stopped to avoid infinite loop")
    json.dump(all_rows, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: rows={len(all_rows)} checkpoint={args.checkpoint}")

if __name__ == "__main__":
    try: main()
    except Exception as e: print(f"STOP: {e}", file=sys.stderr); sys.exit(2)
