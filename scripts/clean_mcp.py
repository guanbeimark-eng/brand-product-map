"""Clean SellerSprite MCP raw output into normalized rows.json for build_excel.py / build_dsl.py.

Usage:
  python clean_mcp.py --raw brand_products.json --out rows.json
  # outputs one rows file per brand key in raw
"""
import argparse, json, re, html
from collections import OrderedDict

def clean_title(t):
    return html.unescape(t or "").strip()

def extract_capacity_pack(title, sku):
    text = " ".join(filter(None, [title or "", sku or ""]))
    cap = ""
    pack = 1
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:Fl\.?\s*Oz\.?|oz)\b", text, re.I)
    if m: cap = f"{m.group(1)} Fl Oz"
    if not cap:
        m2 = re.search(r"(\d+)\s*(?:mL|ml)\b", text)
        if m2: cap = f"{m2.group(1)} mL"
    if not cap:
        m3 = re.search(r"(\d+)\s*(Pairs|Pcs|Pieces|Count|Tablets|Capsules|Bottles)", text, re.I)
        if m3: cap = f"{m3.group(1)} {m3.group(2)}"
    pm = re.search(r"(?:Pack|pack)\s*(?:of|Of)?\s*(\d+)", text)
    if pm: pack = int(pm.group(1))
    else:
        pm2 = re.search(r"\b(\d+)[- ]Pack\b", text, re.I)
        if pm2: pack = int(pm2.group(1))
    return cap, pack

def categorize(title):
    t = (title or "").lower()
    if "disposal" in t or "sink" in t or "garbage" in t: return "其他"
    if "minoxidil" in t:
        if "foam" in t or "aerosol" in t: return "米诺地尔泡沫"
        if "spray" in t: return "米诺地尔喷雾"
        return "米诺地尔溶液"
    if "shampoo" in t and "conditioner" in t: return "洗护套装"
    if "shampoo" in t: return "洗发水"
    if "conditioner" in t: return "护发素"
    if re.search(r"\b(oil|serum|essence|treatment|tonic|scalp)\b", t): return "护发精华/油"
    return "其他"

def short_name(title, brand):
    t = clean_title(title)
    for b in [brand, brand.title(), brand.upper()]:
        t = re.sub(rf"^{re.escape(b)}\s*", "", t, flags=re.I)
    t = re.sub(r"[,\s]+(?:\d+(?:\.\d+)?\s*(?:Fl\.?\s*Oz\.?|oz|mL|ml)).*$", "", t, flags=re.I)
    t = re.sub(r"[,\s]+(?:Pack|pack).*$", "", t, flags=re.I)
    t = re.sub(r"[,\s]+(?:for|with|and).*$", "", t, flags=re.I)
    return t.strip(" -,:")[:60]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    raw = json.load(open(args.raw, encoding="utf-8"))
    result = {}
    for brand, items in raw.items():
        rows = []
        for it in items:
            title = clean_title(it.get("title",""))
            cat = categorize(title)
            # drop obvious off-brand non-hair products
            if cat == "其他" and ("disposal" in title.lower() or "sink" in title.lower() or "cleaner" in title.lower()):
                continue
            sku = it.get("sku") or ""
            cap, pack = extract_capacity_pack(title, sku)
            rows.append({
                "name": short_name(title, brand),
                "full_title": title,
                "capacity": cap,
                "pack": pack,
                "price": it.get("price"),
                "monthly_sales": it.get("units"),
                "monthly_revenue": it.get("revenue"),
                "rating": it.get("rating"),
                "reviews": it.get("ratings"),
                "category": cat,
                "asin": it.get("asin"),
                "parent": it.get("parent"),
                "url": f"https://www.amazon.com/dp/{it.get('asin')}",
                "image_url": it.get("imageUrl"),
            })
        rows.sort(key=lambda r: (r.get("monthly_sales") or 0), reverse=True)
        result[brand] = rows
        print(f"=== {brand}: {len(rows)} rows ===")
    json.dump(result, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}")

if __name__ == "__main__":
    main()
