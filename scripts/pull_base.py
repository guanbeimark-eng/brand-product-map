"""Pull all on-sale records for one brand from Lark Base, paginated.

Calls `lark-cli base +record-list` in a loop until has_more=false, merges rows,
writes raw.json. Clears proxy env before invoking lark-cli.

Usage:
  python pull_base.py \
    --base-token XHKRb... --table-id tbl... \
    --brand-field fldGObUWsi --brand-value "Enaskin Naturals" \
    --status-field fldQzLFz0c --status-value "在售" \
    --out raw.json

Output raw.json: list of {"row_id":..., "fields":{field_id:value,...}}
"""
import argparse, json, os, subprocess, sys, tempfile

def clear_proxy():
    for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        os.environ.pop(k, None)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 and not r.stdout.strip().startswith("{"):
        print("STDERR:", r.stderr, file=sys.stderr)
        raise RuntimeError(f"cmd failed: {cmd[:3]}... rc={r.returncode}")
    return json.loads(r.stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--brand-field", required=True)
    ap.add_argument("--brand-value", required=True)
    ap.add_argument("--status-field", default=None)
    ap.add_argument("--status-value", default=None)
    ap.add_argument("--field-id-list", default=None,
                    help="comma-separated field ids; if omitted, all fields returned")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--out", default="raw.json")
    args = ap.parse_args()

    clear_proxy()

    conds = [
        {"field_id": args.brand_field, "operator": "is", "value": [args.brand_value]},
    ]
    if args.status_field and args.status_value:
        conds.append({"field_id": args.status_field, "operator": "is", "value": [args.status_value]})
    filter_json = {"conjunction": "and", "conditions": conds}

    all_rows = []
    offset = 0
    while True:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(filter_json, f, ensure_ascii=False)
            fpath = f.name
        cmd = ["lark-cli","base","+record-list",
               "--base-token", args.base_token,
               "--table-id", args.table_id,
               "--filter-json", f"@{fpath}",
               "--limit", str(args.page_size),
               "--offset", str(offset),
               "--as","user"]
        if args.field_id_list:
            cmd += ["--field-id-list", json.dumps(args.field_id_list.split(","))]
        resp = run(cmd)
        os.unlink(fpath)
        data = resp.get("data", {})
        rows = data.get("items") or data.get("records") or data.get("data") or []
        all_rows.extend(rows)
        print(f"page offset={offset} got={len(rows)} total={len(all_rows)} has_more={data.get('has_more')}")
        if not data.get("has_more") or not rows:
            break
        offset += len(rows)

    json.dump(all_rows, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: {len(all_rows)} rows")

if __name__ == "__main__":
    main()
