import json
from . import mspdi_io as io
from .scheduler_engine import (
    remove_same_name_sibling_fs, 
    apply_rules_and_ai, 
    break_cycles, 
    round_durations_and_units, 
    topo_schedule
)

def _build_explanations(tasks, changes):
    reasons_by_succ = {}
    for ch in changes:
        if ch.get("action") in {"removed", "converted_to_ss"}:
            reasons_by_succ.setdefault(ch["succ"], []).append(ch.get("reason", "Adjusted by rules."))
    
    rows = []
    for uid, t in tasks.items():
        if uid == 0 or t.is_summary: continue
        reasons = reasons_by_succ.get(uid, [])
        text = "; ".join(reasons) if reasons else "Placed by PM overlap logic and preserved review gates."
        rows.append({
            "task_uid": uid, 
            "task_name": t.name, 
            "outline_level": t.outline, 
            "ai_reason": text
        })
    
    return rows

def run_pipeline(xml_in, xml_out, gantt_json=None, explanations_json=None, excel_out=None, changes=None, ai_callable=None, round_policy="ceil"):
    tree, root, tasks, assigns = io.load(xml_in)
    notes = []
    notes += remove_same_name_sibling_fs(tasks)
    change_recs = apply_rules_and_ai(tasks, ai_callable)
    
    if changes:
        for ch in changes:
            op = ch.get("op")
            if op == "convert_edge":
                succ = tasks.get(int(ch["succ"]))
                pred = tasks.get(int(ch["pred"]))
                if not succ or not pred: continue
                for i, (p, typ, lag) in enumerate(succ.preds):
                    if p == pred.uid:
                        typ = 2 if (ch.get("type", "SS").upper() == "SS") else 1
                        if "lag_frac" in ch:
                            lf = max(0.0, min(1.0, float(ch["lag_frac"])))
                            lag = int(round(pred.duration_min * lf)) * 10
                        else:
                            lag = int(ch.get("lag_min", 0)) * 10
                        succ.preds[i] = (p, typ, lag)
                        notes.append(f"UI: {pred.uid}->{succ.uid} to {('SS' if typ==2 else 'FS')} lag={lag}tmin.")
                        break
            
            elif op == "remove_edge":
                succ = tasks.get(int(ch["succ"]))
                pid = int(ch["pred"])
                if succ: 
                    succ.preds = [(p, t, lg) for (p, t, lg) in succ.preds if p != pid]
                    notes.append(f"UI: removed {pid}->{succ.uid}.")
            
            elif op == "add_edge":
                succ = tasks.get(int(ch["succ"]))
                pred = tasks.get(int(ch["pred"]))
                if succ and pred:
                    typ = 2 if (ch.get("type", "SS").upper() == "SS") else 1
                    if "lag_frac" in ch:
                        lf = max(0.0, min(1.0, float(ch["lag_frac"])))
                        lag = int(round(pred.duration_min * lf)) * 10
                    else:
                        lag = int(ch.get("lag_min", 0)) * 10
                    succ.preds.append((pred.uid, typ, lag))
                    notes.append(f"UI: added {pred.uid}->{succ.uid} type={('SS' if typ==2 else 'FS')} lag={lag}tmin.")
            
            elif op == "set_duration_days":
                t = tasks.get(int(ch["task"]))
                if t and not t.is_summary:
                    days = max(0.5, float(ch.get("days", 1.0)))
                    t.duration_min = int(round(days * 480.0))
                    notes.append(f"UI: set task {t.uid} to {days}d.")
    
    notes += break_cycles(tasks)
    notes += round_durations_and_units(tasks, assigns, round_policy=round_policy)
    
    io.save(tree, root, tasks, assigns, xml_out, strip_dates=True, force_asap=True, recalc_units=True)
    
    ES, EF, order = topo_schedule(tasks)
    out = {"notes": notes, "xml_out": xml_out}
    
    if gantt_json:
        rows = [
            {
                "uid": u,
                "name": tasks[u].name,
                "outline_level": tasks[u].outline,
                "parent_uid": tasks[u].parent_uid,
                "is_summary": tasks[u].is_summary,
                "start_days": ES.get(u, 0) / 480.0,
                "finish_days": EF.get(u, 0) / 480.0,
                "duration_days": tasks[u].duration_min / 480.0
            } 
            for u in order
        ]
        with open(gantt_json, "w", encoding="utf-8") as f: 
            json.dump({"rows": rows}, f, ensure_ascii=False, indent=2)
        out["gantt_json"] = gantt_json
    
    if explanations_json:
        expl = _build_explanations(tasks, change_recs)
        with open(explanations_json, "w", encoding="utf-8") as f: 
            json.dump({"reasons": expl}, f, ensure_ascii=False, indent=2)
        out["explanations_json"] = explanations_json
    
    if excel_out:
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Tasks"
            ws.append(["UID", "Name", "OutlineLevel", "ParentUID", "Summary", "Duration(Days)", "Predecessors(raw)"])
            for u in order:
                t = tasks[u]
                preds = "; ".join([f"{p}:{typ}:{lag}" for (p, typ, lag) in t.preds])
                ws.append([u, t.name, t.outline, t.parent_uid, int(t.is_summary), t.duration_min / 480.0, preds])
            
            ws2 = wb.create_sheet("Assignments")
            ws2.append(["TaskUID", "ResourceUID", "Work(h)", "Units"])
            for a in assigns: 
                ws2.append([a.task_uid, a.res_uid, a.work_min / 60.0, a.units if a.units is not None else ""])
            
            wb.save(excel_out)
            out["excel_out"] = excel_out
        except Exception:
            import csv
            base = excel_out.rsplit(".", 1)[0]
            tpath = base + "_Tasks.csv"
            apath = base + "_Assignments.csv"
            with open(tpath, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["UID", "Name", "OutlineLevel", "ParentUID", "Summary", "Duration(Days)", "Predecessors(raw)"])
                for u in order:
                    t = tasks[u]
                    preds = "; ".join([f"{p}:{typ}:{lag}" for (p, typ, lag) in t.preds])
                    w.writerow([u, t.name, t.outline, t.parent_uid, int(t.is_summary), t.duration_min / 480.0, preds])
            
            with open(apath, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["TaskUID", "ResourceUID", "Work(h)", "Units"])
                for a in assigns:
                    w.writerow([a.task_uid, a.res_uid, a.work_min / 60.0, a.units if a.units is not None else ""])
            
            out["excel_out"] = tpath + " + " + apath
    
    return out
