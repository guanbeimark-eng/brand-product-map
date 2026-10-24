"""Batch-upload product images to a Lark whiteboard via `docs +media-upload`.

For each <asin>.jpg in images_dir, uploads with --parent-type whiteboard
--parent-node <board_token>, collects the returned file_token, writes token_map.json
{asin: file_token}.

Usage:
  python upload_to_board.py --images-dir images --board-token <BOARD_TOKEN> --out token_map.json
"""
import argparse, json, os, subprocess, sys, time

def clear_proxy():
    for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        os.environ.pop(k, None)

def upload(path, board_token):
    cmd = ["lark-cli","docs","+media-upload",
           "--file", path,
           "--parent-type","whiteboard",
           "--parent-node", board_token,
           "--as","user"]
    for attempt in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            data = json.loads(r.stdout)
            if data.get("ok"):
                d = data.get("data",{})
                tok = d.get("file_token") or d.get("token") or (d.get("file") or {}).get("file_token")
                if tok: return tok
        except Exception:
            pass
        print(f"  retry {attempt+1}: {r.stdout[:200]} {r.stderr[:200]}", file=sys.stderr)
        time.sleep(2)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", default="images")
    ap.add_argument("--board-token", required=True)
    ap.add_argument("--out", default="token_map.json")
    args = ap.parse_args()

    clear_proxy()
    files = sorted(f for f in os.listdir(args.images_dir)
                   if f.lower().endswith((".jpg",".jpeg",".png")) and not f.startswith("_"))
    token_map = {}
    fail = []
    for i, fn in enumerate(files, 1):
        asin = os.path.splitext(fn)[0]
        path = os.path.join(args.images_dir, fn)
        print(f"[{i}/{len(files)}] upload {asin} ...", flush=True)
        tok = upload(path, args.board_token)
        if tok:
            token_map[asin] = tok
        else:
            fail.append(asin)

    json.dump(token_map, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"done: uploaded={len(token_map)} fail={len(fail)} -> {args.out}")
    if fail:
        print("failed:", fail, file=sys.stderr)

if __name__ == "__main__":
    main()
