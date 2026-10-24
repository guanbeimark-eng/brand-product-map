"""Download high-res product images from rows.json (Amazon URLs).

Usage:
  python download_images.py --rows rows.json --out-dir images

rows.json: list of {"asin": "...", "image_url": "https://..."}
Output: images/<asin>.jpg ; writes images/_failed.txt on misses.
"""
import argparse, json, os, re, sys, urllib.request, ssl

def hi_resize(url: str) -> str:
    """Upgrade Amazon thumbnail suffix to SL1200 hi-res."""
    if not url:
        return url
    # common thumb suffixes -> hi-res
    for pat in [r"_AC_US\d+_", r"_SY\d+_", r"_SS\d+_", r"_QL\d+_", r"_UL\d+_", r"_SR\d+_\d+_"]:
        if re.search(pat, url):
            return re.sub(pat, "_AC_SL1200_", url)
    if "_AC_SL" not in url and "_US" not in url:
        # no known suffix, try appending before extension
        url = re.sub(r"\.(jpg|jpeg|png)$", r"_AC_SL1200_\1", url, flags=re.I)
    return url

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out-dir", default="images")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    rows = json.load(open(args.rows, encoding="utf-8-sig"))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ok, fail = [], []
    for r in rows:
        asin = r.get("asin") or "unknown"
        url = r.get("image_url") or ""
        if not url:
            fail.append((asin, "no url")); continue
        target = hi_resize(url)
        dest = os.path.join(args.out_dir, f"{asin}.jpg")
        if os.path.exists(dest) and os.path.getsize(dest) > 3000:
            ok.append(asin); continue
        try:
            req = urllib.request.Request(target, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = resp.read()
            if len(data) < 3000:
                # fallback to original
                req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    data = resp.read()
            open(dest, "wb").write(data)
            ok.append(asin)
        except Exception as e:
            fail.append((asin, str(e)[:120]))

    with open(os.path.join(args.out_dir, "_failed.txt"), "w", encoding="utf-8") as f:
        for a, e in fail: f.write(f"{a}\t{e}\n")
    print(f"done ok={len(ok)} fail={len(fail)} -> {args.out_dir}")

if __name__ == "__main__":
    main()
