"""Build groups.json (category columns) from cleaned rows.json.

Usage:
  python make_groups.py --rows rows_maravello.json --out groups_maravello.json
"""
import argparse, json
from collections import OrderedDict

COLORS = [
    ("#5178C6","#F0F4FC"),
    ("#8569CB","#EAE2FE"),
    ("#509863","#DFF5E5"),
    ("#D4B45B","#FEF1CE"),
    ("#D25D5A","#FEE3E2"),
    ("#3FA7A0","#DDF3F1"),
    ("#B0763F","#F5E6D8"),
    ("#6B7280","#E5E7EB"),
]
CATEGORY_ORDER = ["米诺地尔喷雾","米诺地尔溶液","米诺地尔泡沫",
                  "洗发水","护发素","洗护套装","护发精华/油","其他"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = json.load(open(args.rows, encoding="utf-8"))
    by_cat = OrderedDict((c, []) for c in CATEGORY_ORDER)
    for r in rows:
        by_cat.setdefault(r.get("category","其他"), []).append(r["asin"])
    groups = []
    ci = 0
    for cat, asins in by_cat.items():
        if not asins: continue
        main_c, bg = COLORS[ci % len(COLORS)]
        groups.append({"title":cat,"color_main":main_c,"color_bg":bg,"asins":asins})
        ci += 1
    json.dump(groups, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: {len(groups)} columns, {sum(len(g['asins']) for g in groups)} products")

if __name__ == "__main__":
    main()
