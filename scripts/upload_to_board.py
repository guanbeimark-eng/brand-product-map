"""Upload local images to a whiteboard media domain via lark-cli."""
import argparse, json, os, subprocess, sys

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--images-dir", required=True); ap.add_argument("--board-token", required=True); ap.add_argument("--out", default="token_map.json"); args=ap.parse_args()
    out = json.load(open(args.out, encoding="utf-8")) if os.path.exists(args.out) else {}
    env=os.environ.copy()
    for k in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"): env.pop(k,None)
    for name in sorted(os.listdir(args.images_dir)):
        if not name.lower().endswith((".jpg",".jpeg",".png",".webp")): continue
        asin=os.path.splitext(name)[0]
        if asin in out: continue
        cmd=["lark-cli","docs","+media-upload","--file",os.path.join(args.images_dir,name),"--parent-type","whiteboard","--parent-node",args.board_token,"--as","user"]
        p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",env=env)
        if p.returncode: raise RuntimeError(f"STOP upload {name}: {p.stderr[-1000:]}")
        try: data=json.loads(p.stdout)
        except json.JSONDecodeError: raise RuntimeError(f"STOP upload {name}: non-JSON output")
        d=data.get("data",data); tok=d.get("file_token") or d.get("token")
        if not tok: raise RuntimeError(f"STOP upload {name}: no file_token in response")
        out[asin]=tok; json.dump(out,open(args.out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"wrote {args.out}: tokens={len(out)}")
if __name__ == "__main__":
    try: main()
    except Exception as e: print(str(e),file=sys.stderr); sys.exit(2)
