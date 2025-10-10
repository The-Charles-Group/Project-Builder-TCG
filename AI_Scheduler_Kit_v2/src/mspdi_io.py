import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional

NS = "http://schemas.microsoft.com/project"
ET.register_namespace("", NS)

TYPE_FS, TYPE_SS, TYPE_FF, TYPE_SF = 1, 2, 3, 4

def tag(x): 
    return f"{{{NS}}}{x}"

def parse_ptm(x): 
    if not x: return 0
    m = re.match(r"PT(\d+)M$", x)
    if m: return int(m.group(1))
    m2 = re.match(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", x)
    if m2:
        d = int(m2.group(1) or 0)
        h = int(m2.group(2) or 0)
        m = int(m2.group(3) or 0)
        s = int(m2.group(4) or 0)
        return d * 1440 + h * 60 + m + s // 60
    return 0

def ptm(m): 
    return f"PT{int(max(0, m))}M"

class Task:
    __slots__ = ("uid", "name", "outline", "is_summary", "duration_min", "parent_uid", "preds", "elem")
    
    def __init__(self, uid: int, name: str, outline: int, is_summary: bool, duration_min: int, elem):
        self.uid = uid
        self.name = name
        self.outline = outline
        self.is_summary = is_summary
        self.duration_min = duration_min
        self.parent_uid = None
        self.preds = []
        self.elem = elem

class Assign:
    __slots__ = ("elem", "task_uid", "res_uid", "work_min", "units")
    
    def __init__(self, elem, task_uid: Optional[int], res_uid: Optional[int], work_min: int, units: Optional[float]):
        self.elem = elem
        self.task_uid = task_uid
        self.res_uid = res_uid
        self.work_min = work_min
        self.units = units

def load(xml_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    tasks_el = root.find(tag("Tasks"))
    assigns_el = root.find(tag("Assignments"))
    
    items = []
    for t in tasks_el.findall(tag("Task")):
        uid_el = t.find(tag("UID"))
        if uid_el is None: continue
        uid = int(uid_el.text)
        name = (t.find(tag("Name")).text if t.find(tag("Name")) is not None else "")
        ol = int((t.find(tag("OutlineLevel")).text or "1")) if t.find(tag("OutlineLevel")) is not None else 1
        is_sum = (t.find(tag("Summary")).text == "1") if t.find(tag("Summary")) is not None else False
        dur = parse_ptm(t.find(tag("Duration")).text) if t.find(tag("Duration")) is not None else 0
        items.append((uid, ol, Task(uid, name, ol, is_sum, dur, t)))
    
    items.sort()
    stack = []
    by_uid = {}
    
    for uid, ol, task in items:
        while stack and stack[-1][0] >= ol: 
            stack.pop()
        task.parent_uid = stack[-1][1] if stack else None
        stack.append((ol, uid))
        by_uid[uid] = task
    
    for t in by_uid.values():
        for pl in t.elem.findall(tag("PredecessorLink")):
            puid_el = pl.find(tag("PredecessorUID"))
            if puid_el is None or not (puid_el.text or "").lstrip("-").isdigit(): continue
            puid = int(puid_el.text)
            typ_el = pl.find(tag("Type"))
            typ = int(typ_el.text) if (typ_el is not None and (typ_el.text or "").isdigit()) else 1
            lag_el = pl.find(tag("LinkLag"))
            lag = int(lag_el.text) if (lag_el is not None and (lag_el.text or "").lstrip("-").isdigit()) else 0
            t.preds.append((puid, typ, lag))
    
    assigns = []
    if assigns_el is not None:
        for a in assigns_el.findall(tag("Assignment")):
            tu = a.find(tag("TaskUID"))
            ru = a.find(tag("ResourceUID"))
            wu = a.find(tag("Units"))
            wk = a.find(tag("Work"))
            task_uid = int(tu.text) if tu is not None and (tu.text or "").isdigit() else None
            res_uid = int(ru.text) if ru is not None and (ru.text or "").isdigit() else None
            units = float(wu.text) if wu is not None and (wu.text or "") != "" else None
            work_min = parse_ptm(wk.text) if wk is not None else 0
            if task_uid is not None: 
                assigns.append(Assign(a, task_uid, res_uid, work_min, units))
    
    return tree, root, by_uid, assigns

def save(tree, root, tasks, assignments, xml_out, strip_dates=True, force_asap=True, recalc_units=True):
    tasks_el = root.find(tag("Tasks"))
    
    for t_el in tasks_el.findall(tag("Task")):
        uid_el = t_el.find(tag("UID"))
        if uid_el is None: continue
        uid = int(uid_el.text)
        if uid not in tasks: continue
        t = tasks[uid]
        
        dur_el = t_el.find(tag("Duration"))
        if dur_el is None: 
            dur_el = ET.SubElement(t_el, tag("Duration"))
        dur_el.text = ptm(t.duration_min)
        
        for pl in list(t_el.findall(tag("PredecessorLink"))): 
            t_el.remove(pl)
        
        for (puid, typ, lag) in t.preds:
            pl = ET.Element(tag("PredecessorLink"))
            ET.SubElement(pl, tag("PredecessorUID")).text = str(puid)
            ET.SubElement(pl, tag("Type")).text = str(typ)
            if lag: 
                ET.SubElement(pl, tag("LinkLag")).text = str(int(lag))
            t_el.append(pl)
        
        if strip_dates:
            for tg in ["Start", "Finish", "ActualStart", "ActualFinish", "ConstraintDate"]:
                el = t_el.find(tag(tg))
                if el is not None: 
                    t_el.remove(el)
        
        if force_asap:
            ct = t_el.find(tag("ConstraintType"))
            if ct is None: 
                ct = ET.SubElement(t_el, tag("ConstraintType"))
            ct.text = "0"
    
    if recalc_units and assignments:
        dur_map = {u: t.duration_min for u, t in tasks.items()}
        for a in assignments:
            dmin = dur_map.get(a.task_uid, 0)
            if dmin > 0 and a.work_min > 0:
                new_units = a.work_min / dmin
                if 0 < new_units <= 1.0:
                    wu = a.elem.find(tag("Units"))
                    if wu is None: 
                        wu = ET.SubElement(a.elem, tag("Units"))
                    wu.text = f"{new_units:.6f}"
    
    ET.indent(tree, space="  ", level=0)
    tree.write(xml_out, encoding="utf-8", xml_declaration=True)
