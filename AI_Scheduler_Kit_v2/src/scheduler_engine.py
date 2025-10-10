import re
from collections import defaultdict, deque
from typing import Dict, List, Optional, Callable
from .mspdi_io import TYPE_FS, TYPE_SS, Task, Assign

MIN_PER_DAY = 480

GATEKEEPERS = [
    (r"\b(internal review|critique)\b", r"\b(client review|approval)\b"),
    (r"\b(client review|approval)\b", r"\b(revision|revise|changes)\b"),
    (r"\b(revision|revise|changes)\b", r"\b(final|handoff|qa|uat|launch|go live|delivery)\b")
]

RULES = [
    dict(pred=r"\b(brief|strategy|discovery|kickoff|requirements)\b", succ=r"\b(concept|ideation|approach|moodboard|art direction|creative)\b", frac=0.25, reason="Concepting can begin once the brief gels (~25%)."),
    dict(pred=r"\b(concept|ideation|approach)\b", succ=r"\b(copy|copywriting|script|art direction|design|visual|ui|ux|layout|comps)\b", frac=0.30, reason="Creative starts on an initial concept (~30%)."),
    dict(pred=r"\b(content plan|cadence|matrix|calendar)\b", succ=r"\b(content|copy|draft|asset production)\b", frac=0.25, reason="Drafting begins once planning has a skeleton (~25%)."),
    dict(pred=r"\b(design|ui|visual|art direction|layout|component library|comps)\b", succ=r"\b(dev|build|engineering|implementation|frontend|front[- ]?end|backend|back[- ]?end)\b", frac=0.60, reason="Engineering starts once key designs stabilize (~60%)."),
    dict(pred=r"\b(dev|build|engineering|implementation)\b", succ=r"\b(qa|test|testing|uat|accessibility|validation)\b", frac=0.80, reason="QA/UAT starts on near-final builds (~80%).")
]

def _n(s): 
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s\-\/&]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _m(txt, pat):
    return bool(re.search(pat, _n(txt)))

def _gate(pred, succ): 
    return any(_m(pred, p) and _m(succ, s) for (p, s) in GATEKEEPERS)

def topo_schedule(tasks: Dict[int, Task]):
    preds = defaultdict(list)
    succs = defaultdict(list)
    indeg = defaultdict(int)
    ids = [u for u in tasks.keys() if u != 0]
    
    for u, t in tasks.items():
        if u == 0: continue
        for (p, _, _) in t.preds:
            preds[u].append(p)
            succs[p].append(u)
        indeg[u] = len(preds[u])
    
    q = deque([u for u in ids if indeg[u] == 0])
    ES = {u: 0 for u in ids}
    EF = {}
    order = []
    
    while q:
        u = q.popleft()
        order.append(u)
        ES[u] = max([EF.get(p, 0) for p in preds.get(u, [])] or [0])
        EF[u] = ES[u] + tasks[u].duration_min
        for v in succs.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0: 
                q.append(v)
    
    return ES, EF, order

def remove_same_name_sibling_fs(tasks: Dict[int, Task]):
    notes = []
    by_name_parent = defaultdict(list)
    for t in tasks.values(): 
        by_name_parent[(_n(t.name), t.parent_uid)].append(t.uid)
    
    for s in tasks.values():
        key = (_n(s.name), s.parent_uid)
        if len(by_name_parent[key]) < 2: continue
        new = []
        for (p, typ, lag) in s.preds:
            P = tasks.get(p)
            if P and typ == TYPE_FS and P.parent_uid == s.parent_uid and _n(P.name) == _n(s.name):
                notes.append(f"Removed FS sibling chain: '{P.name}' → '{s.name}'.")
                continue
            new.append((p, typ, lag))
        s.preds = new
    
    return notes

def apply_rules_and_ai(tasks: Dict[int, Task], ai: Optional[Callable] = None):
    changes = []
    
    for s in tasks.values():
        if s.is_summary: continue
        new = []
        for (p, typ, lag) in s.preds:
            P = tasks.get(p)
            if not P: 
                new.append((p, typ, lag))
                continue
            if _gate(P.name, s.name): 
                new.append((p, typ, lag))
                continue
            
            decided = False
            if ai:
                try: 
                    adv = ai({
                        "pred": P.name, 
                        "succ": s.name, 
                        "pred_duration_d": P.duration_min / 480.0, 
                        "succ_duration_d": s.duration_min / 480.0, 
                        "siblings": P.parent_uid == s.parent_uid
                    })
                except Exception: 
                    adv = None
                
                if isinstance(adv, dict) and adv.get("action") in {"keep", "remove", "convert_to_ss"}:
                    if adv["action"] == "remove":
                        changes.append({"succ": s.uid, "pred": P.uid, "action": "removed", "reason": adv.get("reason", "AI removed")})
                        decided = True
                    elif adv["action"] == "convert_to_ss":
                        frac = max(0.05, min(0.9, float(adv.get("start_frac", 0.3))))
                        lag_min = int(round(P.duration_min * frac))
                        new.append((p, 2, lag_min * 10))
                        changes.append({"succ": s.uid, "pred": P.uid, "action": "converted_to_ss", "lag_min": lag_min, "reason": adv.get("reason", "AI overlap")})
                        decided = True
                    else: 
                        new.append((p, typ, lag))
                        decided = True
            
            if decided: continue
            
            applied = False
            for r in RULES:
                if _m(P.name, r["pred"]) and _m(s.name, r["succ"]):
                    frac = max(0.05, min(0.9, float(r["frac"])))
                    lag_min = int(round(P.duration_min * frac))
                    new.append((p, 2, lag_min * 10))
                    changes.append({"succ": s.uid, "pred": P.uid, "action": "converted_to_ss", "lag_min": lag_min, "reason": r["reason"]})
                    applied = True
                    break
            
            if not applied and not decided: 
                new.append((p, typ, lag))
        
        s.preds = new
    
    return changes

def break_cycles(tasks: Dict[int, Task]):
    notes = []
    ids = [u for u in tasks.keys() if u != 0]
    preds = {u: [p for (p, _, _) in tasks[u].preds] for u in ids}
    indeg = {u: len(preds[u]) for u in ids}
    q = deque([u for u in ids if indeg[u] == 0])
    seen = []
    
    while q:
        u = q.popleft()
        seen.append(u)
        for v in ids:
            if u in preds.get(v, []): 
                indeg[v] -= 1
            if indeg[v] == 0 and v not in seen and v not in q: 
                q.append(v)
    
    if len(seen) == len(ids): 
        return notes
    
    for u in ids:
        if u in seen: continue
        if not tasks[u].preds: continue
        tasks[u].preds.pop(0)
        notes.append(f"Cycle fix removed one edge into {u}.")
        break
    
    return notes

def round_durations_and_units(tasks: Dict[int, Task], assigns: List[Assign], round_policy="ceil"):
    notes = []
    ch = 0
    
    for t in tasks.values():
        if t.uid == 0 or t.is_summary: continue
        d = t.duration_min
        if d <= 0 or d % MIN_PER_DAY == 0: continue
        new = (round(d / MIN_PER_DAY) * MIN_PER_DAY) if round_policy == "nearest" else ((d + MIN_PER_DAY - 1) // MIN_PER_DAY) * MIN_PER_DAY
        if new != d: 
            t.duration_min = int(new)
            ch += 1
    
    if ch: 
        notes.append(f"Rounded {ch} durations to whole days.")
    
    if assigns:
        for a in assigns:
            d = tasks.get(a.task_uid).duration_min if tasks.get(a.task_uid) else 0
            if d > 0 and a.work_min > 0:
                u = a.work_min / d
                if 0 < u <= 1.0: 
                    a.units = u
        notes.append("Recalculated Units.")
    
    return notes
