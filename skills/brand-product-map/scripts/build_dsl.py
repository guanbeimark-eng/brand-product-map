"""Build Lark whiteboard DSL v2 JSON with CORRECT schema (2025-10).

Key schema differences from old:
- rect: fillColor/borderColor/borderWidth/borderRadius (not fill/border/radius)
- text: textColor/textAlign (not color/align), no bold field
- image: {type:'image', image:{src: token}} (not src flat)
- connector: {type:'connector', connector:{from,to,fromAnchor,toAnchor,lineShape,lineColor,lineWidth,endArrow}}
"""
import json, hashlib, argparse

CARD_W = 210
CARD_H = 80
IMG = 64
COL_GAP = 16
COL_PAD = 10
CARD_GAP = 10
ROOT_W = 360
ROOT_H = 90

def nid(prefix):
    return hashlib.md5(prefix.encode()).hexdigest()[:10]

def text_node(text, x, y, w, h, size=11, color="#1F2329", align="left", valign="top"):
    return {
        "type":"text","id":nid(text+str(x)+str(y)+str(size)),
        "x":x,"y":y,"width":w,"height":h,
        "text":text,"fontSize":size,"textColor":color,
        "textAlign":align,"verticalAlign":valign,
    }

def image_node(file_token, x, y, w, h):
    return {"type":"image","id":nid("img"+file_token+str(x)+str(y)),
            "x":x,"y":y,"width":w,"height":h,
            "image":{"src":file_token}}

def rect_node(x,y,w,h, fill, border_color=None, border_w=0, radius=8, node_id=None):
    n = {"type":"rect","id": node_id or nid(f"r{x}{y}{w}{h}{fill}"),
         "x":x,"y":y,"width":w,"height":h,
         "fillColor":fill,"borderRadius":radius}
    if border_color:
        n["borderColor"] = border_color
        n["borderWidth"] = border_w
    return n

def connector(from_id, from_anchor, to_id, to_anchor, color="#BBBFC4"):
    return {"type":"connector","id":nid(f"c{from_id}{to_id}"),
            "connector":{
                "from": from_id, "to": to_id,
                "fromAnchor": from_anchor, "toAnchor": to_anchor,
                "lineShape": "curve", "lineColor": color, "lineWidth": 2,
                "endArrow": "none"
            }}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--token-map", required=True)
    ap.add_argument("--root-label", required=True)
    ap.add_argument("--root-sub", default="")
    ap.add_argument("--groups", required=True)
    ap.add_argument("--out", default="diagram.json")
    args = ap.parse_args()

    rows = {r["asin"]: r for r in json.load(open(args.rows, encoding="utf-8-sig"))}
    token_map = json.load(open(args.token_map, encoding="utf-8-sig"))
    groups = json.load(open(args.groups, encoding="utf-8-sig"))

    # layout
    col_heights = []
    for g in groups:
        n = len(g["asins"])
        h = 40 + n*(CARD_H+CARD_GAP) + COL_PAD*2
        col_heights.append(h)
    total_w = len(groups)*(CARD_W+COL_PAD*2) + (len(groups)-1)*COL_GAP
    max_h = max(col_heights)
    root_y = 40
    cols_y = root_y + ROOT_H + 80

    nodes = []
    # root node (rect with text inside)
    root_id = nid("root")
    root_x = (total_w - ROOT_W)//2
    nodes.append(rect_node(root_x, root_y, ROOT_W, ROOT_H, "#1F2329", radius=16, node_id=root_id))
    nodes.append(text_node(args.root_label, root_x, root_y+16, ROOT_W, 36,
                           size=26, color="#FFFFFF", align="center", valign="middle"))
    if args.root_sub:
        nodes.append(text_node(args.root_sub, root_x, root_y+56, ROOT_W, 24,
                               size=13, color="#D0D7DE", align="center", valign="middle"))

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
        # column background
        nodes.append(rect_node(col_x, col_y, col_w, col_h, col_bg,
                               border_color=col_main, border_w=1, radius=10, node_id=col_id))
        # column title
        nodes.append(text_node(g["title"], col_x+COL_PAD, col_y+8, CARD_W, 24,
                               size=14, color=col_main, align="center", valign="middle"))

        # cards
        cy = col_y + 40 + COL_PAD
        for asin in g["asins"]:
            r = rows.get(asin)
            if not r: continue
            card_x = col_x + COL_PAD
            card_id = nid(f"card{asin}")
            nodes.append(rect_node(card_x, cy, CARD_W, CARD_H, "#FFFFFF",
                                   border_color=col_main, border_w=2, radius=8))
            # image
            tok = token_map.get(asin)
            if tok:
                nodes.append(image_node(tok, card_x+8, cy+8, IMG, IMG))
            # line1: capacity + price
            cap = r.get("capacity") or ""
            pack = r.get("pack")
            if pack and pack>1:
                cap = (cap+" · " if cap else "")+f"{pack} Pack"
            price = r.get("price")
            line1 = f"{cap}  ${price:.2f}" if price else cap
            if not line1: line1 = r.get("name","")[:30]
            nodes.append(text_node(line1, card_x+8+IMG+8, cy+10, CARD_W-IMG-24, 20,
                                   size=11, color="#1F2329", align="left", valign="middle"))
            # line2: sales + rating
            sales = r.get("monthly_sales")
            rating = r.get("rating")
            parts = []
            if sales: parts.append(f"月销{sales}")
            if rating: parts.append(f"★{rating}")
            line2 = "  ".join(parts)
            if line2:
                nodes.append(text_node(line2, card_x+8+IMG+8, cy+38, CARD_W-IMG-24, 18,
                                       size=10, color="#646A73", align="left", valign="middle"))
            cy += CARD_H + CARD_GAP
        x += col_w + COL_GAP

    # connectors root -> columns
    for col_id in col_top_ids:
        connectors.append(connector(root_id, "bottom", col_id, "top"))

    doc = {"version":2, "nodes": nodes + connectors}
    json.dump(doc, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: nodes={len(nodes)} connectors={len(connectors)} size≈{total_w}x{cols_y+max_h}")

if __name__ == "__main__":
    main()
