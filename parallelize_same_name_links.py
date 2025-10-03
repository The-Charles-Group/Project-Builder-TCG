import xml.etree.ElementTree as ET
from collections import defaultdict, Counter, deque
import re, sys, os

NS = "http://schemas.microsoft.com/project"
ET.register_namespace("", NS)

def parse_minutes(d):
    if not d: return 0
    m = re.match(r"PT(\d+)M$", d)
    if m: return int(m.group(1))
    m = re.match(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", d)
    if m:
        days = int(m.group(1) or 0)
        hours = int(m.group(2) or 0)
        minutes = int(m.group(3) or 0)
        seconds = int(m.group(4) or 0)
        return days*1440 + hours*60 + minutes + seconds//60
    return 0

def makespan_days(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    tasks_el = root.find(f"{{{NS}}}Tasks")
    dur = {}; preds = defaultdict(list); uids = []
    for t in tasks_el.findall(f"{{{NS}}}Task"):
        uid_el = t.find(f"{{{NS}}}UID")
        if uid_el is None: continue
        uid = int(uid_el.text)
        if uid == 0: continue
        d_el = t.find(f"{{{NS}}}Duration")
        dur[uid] = parse_minutes(d_el.text) if d_el is not None else 0
        uids.append(uid)
        for pl in t.findall(f"{{{NS}}}PredecessorLink"):
            puid_el = pl.find(f"{{{NS}}}PredecessorUID")
            if puid_el is not None and (puid_el.text or "").isdigit():
                preds[uid].append(int(puid_el.text))

    in_deg = {u:0 for u in uids}
    for v in uids:
        for p in preds.get(v, []):
            if p in in_deg:
                in_deg[v] += 1
    q = deque([u for u in uids if in_deg[u] == 0])
    ES = {u:0 for u in uids}; EF = {}
    while q:
        u = q.popleft()
        ES[u] = max([EF.get(p,0) for p in preds.get(u,[])] or [0])
        EF[u] = ES[u] + dur.get(u,0)
        for v in uids:
            if u in preds.get(v, []):
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    q.append(v)
    return (max(EF.values())/480.0) if EF else 0.0

def parallelize_same_name_links(src_path, out_path):
    tree = ET.parse(src_path)
    root = tree.getroot()
    tasks_el = root.find(f"{{{NS}}}Tasks")

    uid_to_name = {}
    for t in tasks_el.findall(f"{{{NS}}}Task"):
        uid_el = t.find(f"{{{NS}}}UID")
        name_el = t.find(f"{{{NS}}}Name")
        if uid_el is None: continue
        uid = int(uid_el.text)
        uid_to_name[uid] = (name_el.text or "").strip() if name_el is not None else ""

    name_counts = Counter(uid_to_name.values())
    parallel_names = {n for n,c in name_counts.items() if c > 1 and n != ""}

    removed = 0
    for t in tasks_el.findall(f"{{{NS}}}Task"):
        uid_el = t.find(f"{{{NS}}}UID")
        if uid_el is None: 
            continue
        uid = int(uid_el.text)
        succ_name = uid_to_name.get(uid, "")
        if succ_name not in parallel_names:
            continue
        to_remove = []
        for pl in t.findall(f"{{{NS}}}PredecessorLink"):
            puid_el = pl.find(f"{{{NS}}}PredecessorUID")
            if puid_el is None: 
                continue
            if not (puid_el.text or "").isdigit():
                continue
            puid = int(puid_el.text)
            if uid_to_name.get(puid, "") == succ_name:
                to_remove.append(pl)
        for pl in to_remove:
            t.remove(pl)
            removed += 1

    ET.indent(tree, space="  ", level=0)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return removed

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parallelize_same_name_links.py <INPUT.xml> <OUTPUT.xml>")
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    before = makespan_days(src)
    removed = parallelize_same_name_links(src, out)
    after = makespan_days(out)
    print({
        "input": os.path.basename(src),
        "output": os.path.basename(out),
        "same_name_links_removed": removed,
        "makespan_days_before": before,
        "makespan_days_after": after
    })
