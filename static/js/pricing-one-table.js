// pricing-one-table.js
// Builds ONE unified editable Pricing table (deliverables + components).
(function () {
  const CADENCE_OPTIONS = ["One-Time", "Monthly", "Quarterly"];

  function h(tag, attrs={}, ...children) {
    const el = document.createElement(tag);
    for (const [k,v] of Object.entries(attrs || {})) {
      if (k === "class") el.className = v;
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.substring(2).toLowerCase(), v);
      else if (k === "dataset") Object.assign(el.dataset, v);
      else if (v != null) el.setAttribute(k, v);
    }
    for (const c of children) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    return el;
  }

  const money = (n) => (isFinite(n) ? `$${Number(n).toLocaleString()}` : "-");

  const numberInput = (value, onChange, attrs={}) => {
    const input = h("input", Object.assign({ type:"number", value:String(value ?? ""), class:"apb-input apb-num" }, attrs));
    input.addEventListener("change", e => onChange(Number(e.target.value)));
    input.addEventListener("blur",    e => onChange(Number(e.target.value)));
    return input;
  };
  const cadenceSelect = (value, onChange) => {
    const sel = h("select", { class:"apb-input apb-sel" });
    for (const opt of CADENCE_OPTIONS) sel.appendChild(h("option", { value:opt, selected:opt===value }, opt));
    sel.addEventListener("change", e => onChange(e.target.value));
    return sel;
  };

  function rowDeliverable(d) {
    const tr = h("tr", { class:"apb-row-deliv", dataset:{ id:d.id }});
    const toggle = h("button", { class:"apb-exp" }, "▸");
    toggle.addEventListener("click", () => {
      const open = tr.classList.toggle("open");
      toggle.textContent = open ? "▾" : "▸";
      for (const r of document.querySelectorAll(`tr[data-parent='${d.id}']`)) r.style.display = open ? "" : "none";
    });

    tr.appendChild(h("td", { class:"apb-cell-title" }, toggle, " ", h("strong", {}, d.title)));
    tr.appendChild(h("td", {}, cadenceSelect(d.cadence || "One-Time", (val)=> ScenarioStore.updateDeliverable(d.id, { cadence: val })) ));
    tr.appendChild(h("td", {}, numberInput(d.months || (d.cadence==="Monthly"?12:(d.cadence==="Quarterly"?4:0)), (val)=> ScenarioStore.updateDeliverable(d.id, { months: val }), { min:"0" })));
    tr.appendChild(h("td", {}, numberInput(d.hours   || 0, (val)=> ScenarioStore.updateDeliverable(d.id, { hours: val }),    { min:"0", step:"0.1" })));
    tr.appendChild(h("td", {}, numberInput(d.rate    || ScenarioStore.state.blendedRate || 210, (val)=> ScenarioStore.updateDeliverable(d.id, { rate: val }), { min:"0", step:"1" })));
    tr.appendChild(h("td", { class:"apb-right" }, money(d.price)));
    const resInput = h("input", { type:"text", class:"apb-input apb-txt", value:(d.resources||[]).join(", ") });
    resInput.addEventListener("change", (e)=> {
      const list = String(e.target.value||"").split(",").map(s=>s.trim()).filter(Boolean);
      ScenarioStore.updateDeliverable(d.id, { resources: list });
    });
    tr.appendChild(h("td", {}, resInput));

    const saveBtn = h("button", { class:"apb-btn apb-sm", onclick: ()=> ScenarioStore.save() }, "Save");
    tr.appendChild(h("td", { class:"apb-right" }, saveBtn));
    return tr;
  }

  function rowComponent(d, c) {
    const tr = h("tr", { class:"apb-row-comp", dataset:{ id:c.id, parent:d.id }});
    tr.appendChild(h("td", { class:"apb-cell-title" }, h("span", { class:"apb-spacer" }, "└─ "), c.title));
    tr.appendChild(h("td", {}, cadenceSelect(c.cadence || d.cadence || "One-Time", (val)=> ScenarioStore.updateComponent(d.id, c.id, { cadence: val })) ));
    tr.appendChild(h("td", {}, numberInput(c.months || d.months || 0, (val)=> ScenarioStore.updateComponent(d.id, c.id, { months: val }), { min:"0" })));
    tr.appendChild(h("td", {}, numberInput(c.hours   || 0, (val)=> ScenarioStore.updateComponent(d.id, c.id, { hours: val      }), { min:"0", step:"0.1" })));
    tr.appendChild(h("td", {}, numberInput(c.rate    || d.rate || ScenarioStore.state.blendedRate || 210, (val)=> ScenarioStore.updateComponent(d.id, c.id, { rate: val }), { min:"0", step:"1" })));
    tr.appendChild(h("td", { class:"apb-right" }, money(c.price)));

    const tasksInput = h("input", { type:"text", class:"apb-input apb-txt", value:(c.tasks||[]).join(", ") });
    tasksInput.addEventListener("change", (e)=> {
      const list = String(e.target.value||"").split(",").map(s=>s.trim()).filter(Boolean);
      ScenarioStore.updateComponent(d.id, c.id, { tasks: list });
    });
    tr.appendChild(h("td", {}, tasksInput));
    tr.appendChild(h("td", { class:"apb-right" }, ""));
    return tr;
  }

  function totalsRow(state) {
    const tot = state.totals || {};
    const tr = h("tr", { class:"apb-row-totals" });
    tr.appendChild(h("td", { colspan:"3" }, h("strong", {}, "Totals")));
    tr.appendChild(h("td", {}, String(tot.hours || 0)));
    tr.appendChild(h("td", {}, ""));
    tr.appendChild(h("td", { class:"apb-right" }, money((tot.oneTimeCost||0) + (tot.monthlyCost||0))));
    tr.appendChild(h("td", {}, ""));
    
    const btnGroup = h("div", { class:"apb-btn-group" });
    
    const rebuildBtn = h("button", { class:"apb-btn apb-blue", onclick: async ()=> { 
      rebuildBtn.disabled = true;
      rebuildBtn.textContent = "Rebuilding...";
      await ScenarioStore.rebuildBreakdown();
      rebuildBtn.disabled = false;
      rebuildBtn.textContent = "Re-build Scenario";
    }}, "Re-build Scenario");
    
    const resetBtn = h("button", { class:"apb-btn apb-orange", onclick: async ()=> {
      if (!confirm("Reset all Step 3 changes to the original Step 2 baseline?")) return;
      resetBtn.disabled = true;
      resetBtn.textContent = "Resetting...";
      await ScenarioStore.resetFromStep2();
      resetBtn.disabled = false;
      resetBtn.textContent = "Reset from Step 2";
    }}, "Reset from Step 2");
    
    btnGroup.appendChild(rebuildBtn);
    btnGroup.appendChild(resetBtn);
    tr.appendChild(h("td", { class:"apb-right" }, btnGroup));
    return tr;
  }

  function render(tableId="apb-one-table") {
    const mount = document.getElementById(tableId);
    if (!mount) return;
    mount.innerHTML = "";

    const tbl = h("table", { class:"apb-table" });
    tbl.appendChild(
      h("thead", {},
        h("tr", {},
          h("th", {}, "Deliverable / Component"),
          h("th", {}, "Cadence"),
          h("th", {}, "Months"),
          h("th", {}, "Hours"),
          h("th", {}, "Rate"),
          h("th", {}, "Cost"),
          h("th", {}, "Tasks / Resources"),
          h("th", {}, "Actions")
        )
      )
    );
    const tb = h("tbody");
    const state = ScenarioStore.state;

    for (const d of state.deliverables) {
      tb.appendChild(rowDeliverable(d));
      for (const c of (d.components || [])) {
        const r = rowComponent(d, c);
        r.style.display = "none"; // shown when user expands deliverable
        tb.appendChild(r);
      }
    }
    tb.appendChild(totalsRow(state));
    tbl.appendChild(tb);
    mount.appendChild(tbl);
  }

  document.addEventListener("DOMContentLoaded", ()=> render());
  ScenarioStore.subscribe(()=> render());

  // Public helper to hydrate from your existing selection object
  window.APBOneTable = {
    mount: render,
    hydrateFrom(raw) {
      if (!raw) return;
      ScenarioStore.upsertMany(raw.deliverables || []);
    }
  };
})();
