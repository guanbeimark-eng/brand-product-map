"""Build Lark whiteboard DSL v2 JSON: brand root node centered on top,
curved connectors down to category columns, each column a vertical stack
of product cards (left image 60x60, right two-line text).

Usage:
  python build_dsl.py \
    --rows rows.json --token-map token_map.json \
    --root-label "ENASKIN NATURALS" --root-sub "在售产品分布 · 44款" \
    --groups groups.json --out diagram.json

groups.json: list of {"title": "眼膜·绿茶/蓝", "color_main":"#5178C6", "color_bg":"#F0F4FC", "asins":["B0...","B0..."]}
order asins determines order inside column.
"""
import argparse, json, hashlib

CARD_W = 200
CARD_H = 78
IMG = 60
COL_GAP = 20
COL_PAD = 12
CARD_GAP = 10
ROOT_W = 360
ROOT_H = 90

def nid(prefix):
    return hashlib.md5(prefix.encode()).hexdigest()[:10]

def text_node(text, x, y, w, h, size=11, color="#1F2329", bold=False, align="left"):
    return {
        "type":"text","id":nid(text+str(x)+str(y)+str(size)),
        "x":x,"y":y,"width":w,"height":h,
        "text":text,"fontSize":size,"color":color,
        "bold":bold,"align":align,
    }

def image_node(file_token, x, y, w, h):
    return {"type":"image","id":nid("img"+file_token+str(x)+str(y)),
            "x":x,"y":y,"width":w,"height":h,
            "src":file_token,"fit":"cover"}

def rect_node(x,y,w,h, fill, border=None, radius=8):
    n = {"type":"rect","id":nid(f"r{x}{y}{w}{h}{fill}"),
         "x":x,"y":y,"width":w,"height":h,
         "fill":fill,"radius":radius}
    if border: n["border"] = border
    return n

def connector(from_id, from_side, to_id, to_side, color="#BBBFC4"):
    return {"type":"connector","id":nid(f"c{from_id}{to_id}"),
            "from":{"node":from_id,"side":from_side},
            "to":{"node":to_id,"side":to_side},
            "style":"curve","color":color,"width":2,"endArrow":"none"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--token-map", required=True, help="asin -> whiteboard file_token")
    ap.add_argument("--root-label", required=True)
    ap.add_argument("--root-sub", default="")
    ap.add_argument("--groups", required=True)
    ap.add_argument("--out", default="diagram.json")
    args = ap.parse_args()

    rows = {r["asin"]: r for r in json.load(open(args.rows, encoding="utf-8-sig"))}
    token_map = json.load(open(args.token_map, encoding="utf-8-sig"))
    groups = json.load(open(args.groups, encoding="utf-8-sig"))

    # layout: left-aligned columns; root centered above them
    # first pass: compute column heights
    col_heights = []
    for g in groups:
        n = len(g["asins"])
        h = 36 + n*(CARD_H+CARD_GAP) + COL_PAD*2  # title bar 36 + cards
        col_heights.append(h)
    total_w = len(groups)*(CARD_W+COL_PAD*2) + (len(groups)-1)*COL_GAP
    max_h = max(col_heights)
    root_y = 30
    cols_y = root_y + ROOT_H + 60  # gap for connectors

    nodes = []
    # root node
    root_id = nid("root")
    root_x = (total_w - ROOT_W)//2
    nodes.append({"type":"rect","id":root_id,"x":root_x,"y":root_y,
                  "width":ROOT_W,"height":ROOT_H,"fill":"#1F2329","radius":14})
    nodes.append(text_node(args.root_label, root_x, root_y+18, ROOT_W, 34,
                           size=24, color="#FFFFFF", bold=True, align="center"))
    if args.root_sub:
        nodes.append(text_node(args.root_sub, root_x, root_y+56, ROOT_W, 22,
                               size=13, color="#D0D7DE", align="center"))

    connectors = []
    x = 0
    col_top_ids = []
    for gi, g in enumerate(groups):
        col_w = CARD_W + COL_PAD*2
        col_x = x
        col_y = cols_y
        col_h = col_heights[gi]
        col_bg = g.get("color_bg","#F5F6F7")
        col_main = g.get("color_main","#5178C6")

        col_id = nid(f"col{gi}")
        col_top_ids.append(col_id)
        nodes.append({"type":"rect","id":col_id,"x":col_x,"y":col_y,
                      "width":col_w,"height":col_h,"fill":col_bg,"radius":10,
                      "border":{"color":col_main,"width":1}})
        # title bar
        nodes.append(text_node(g["title"], col_x+COL_PAD, col_y+10, CARD_W, 22,
                               size=13, color=col_main, bold=True, align="center"))

        # cards
        cy = col_y + 36 + COL_PAD
        for asin in g["asins"]:
            r = rows.get(asin)
            if not r: continue
            card_x = col_x + COL_PAD
            card_id = nid(f"card{asin}")
            nodes.append({"type":"rect","id":card_id,"x":card_x,"y":cy,
                          "width":CARD_W,"height":CARD_H,"fill":"#FFFFFF","radius":8,
                          "border":{"color":col_main,"width":2}})
            # image
            tok = token_map.get(asin)
            if tok:
                nodes.append(image_node(tok, card_x+8, cy+9, IMG, IMG))
            # text line 1: capacity · price
            cap = r.get("capacity") or ""
            pack = r.get("pack")
            if pack and pack>1: cap = (cap+" · " if cap else "")+f"{pack} Pack"
            price = r.get("price")
            line1 = f"{cap}  ${price:.2f}" if price else cap
            nodes.append(text_node(line1, card_x+8+IMG+8, cy+10, CARD_W-IMG-24, 18,
                                   size=11, color="#1F2329"))
            # text line 2: monthly sales · rating
            sales = r.get("monthly_sales")
            rating = r.get("rating")
            line2_parts = []
            if sales: line2_parts.append(f"月销{sales}")
            if rating: line2_parts.append(f"★{rating}")
            line2 = "  ".join(line2_parts)
            if line2:
                nodes.append(text_node(line2, card_x+8+IMG+8, cy+38, CARD_W-IMG-24, 18,
                                       size=10, color="#646A73"))
            cy += CARD_H + CARD_GAP
        x += col_w + COL_GAP

    # connectors root bottom -> each column top
    root_cx = root_x + ROOT_W//2
    root_bottom_y = root_y + ROOT_H
    for col_id in col_top_ids:
        connectors.append(connector(root_id, "bottom", col_id, "top"))

    doc = {"version":2, "nodes": nodes + connectors}
    json.dump(doc, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: nodes={len(nodes)} connectors={len(connectors)} size≈{total_w}x{cols_y+max_h}")

if __name__ == "__main__":
    main()
