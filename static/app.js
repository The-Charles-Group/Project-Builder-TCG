let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

async function api(path, opts={}) {
  const res = await fetch(path, {headers:{"Content-Type":"application/json"}, ...opts});
  if(!res.ok){ throw new Error(await res.text()); }
  const ct = res.headers.get("content-type") || "";
  if(ct.includes("application/json")) return res.json();
  return res.text();
}

function el(html){ const t=document.createElement('template'); t.innerHTML=html.trim(); return t.content.firstChild; }

function currency(n){ return `$${Number(n||0).toLocaleString()}`; }

async function boot() {
  await api("/api/load");
  OPTIONS = await api("/api/options");
  // Populate dropdowns
  const pricingMode = document.querySelector("#pricingMode");
  OPTIONS.pricing_modes.forEach(m => pricingMode.append(el(`<option>${m}</option>`)));
  const rateBand = document.querySelector("#rateBand");
  OPTIONS.rate_bands.forEach(b => rateBand.append(el(`<option>${b}</option>`)));
  // Scenario templates
  const sA = document.querySelector("#scenarioA");
  const sB = document.querySelector("#scenarioB");
  OPTIONS.scenario_templates.forEach(s => {
    sA.append(el(`<option value="${s.Scenario_Key}">${s.Scenario_Key} (${s.Complexity}×${s.Tier})</option>`));
    sB.append(el(`<option value="${s.Scenario_Key}">${s.Scenario_Key} (${s.Complexity}×${s.Tier})</option>`));
  });
  // Defaults: MED_LOW / MED_HIGH
  if(OPTIONS.scenario_templates.find(x => x.Scenario_Key==="MED_LOW")) sA.value="MED_LOW";
  if(OPTIONS.scenario_templates.find(x => x.Scenario_Key==="MED_HIGH")) sB.value="MED_HIGH";

  // Deliverables list
  DELIVERABLES = OPTIONS.deliverables;
  renderDeliverableList(DELIVERABLES);

  // Pricing default blended
  const ps = OPTIONS.pricing_settings.find(x => x.Key==="Default_Blended_Rate");
  if(ps) document.querySelector("#blendedRate").value = ps.Default;

  // Slack defaults
  const ss = Object.fromEntries(OPTIONS.slack_settings.map(x => [x.Key, x.Default]));
  document.querySelector("#useSlack").checked = !!ss["Use_Slack"];
  document.querySelector("#slackInternal").value = ss["Slack_After_Internal_Review_Days"] ?? 1;
  document.querySelector("#slackClient").value   = ss["Slack_After_Client_Review_Days"] ?? 2;
  document.querySelector("#slackGlobal").value   = ss["Slack_Global_Percent"] ?? 0.05;

  // UI wiring
  document.querySelector("#btnSuggest").onclick = onSuggest;
  document.querySelector("#btnBuild").onclick   = onBuild;
  document.querySelector("#pricingMode").onchange = onPricingModeChanged;
  document.querySelector("#useTemplates").onchange = onScenarioTypeChanged;
  document.querySelector("#useBundles").onchange   = onScenarioTypeChanged;
  document.querySelector("#btnExportA").onclick = () => onExport('A');
  document.querySelector("#btnExportB").onclick = () => onExport('B');
  onPricingModeChanged();
}

function onPricingModeChanged(){
  const mode = document.querySelector("#pricingMode").value;
  document.querySelector("#blendedWrap").classList.toggle("hidden", mode!=="Flat_Blended");
  document.querySelector("#bandWrap").classList.toggle("hidden", mode!=="Per_Resource");
}

function onScenarioTypeChanged(){
  const useTemplates = document.querySelector("#useTemplates").checked;
  document.querySelector("#templateRow").classList.toggle("hidden", !useTemplates);
  document.querySelector("#bundleRow").classList.toggle("hidden", useTemplates);
}

function renderDeliverableList(items){
  const box = document.querySelector("#deliverableList");
  box.innerHTML = "";
  items.forEach(d => {
    const id = `deliv_${d.Deliverable_Code}`;
    box.append(el(`
      <div class="row">
        <input type="checkbox" id="${id}" data-code="${d.Deliverable_Code}"/>
        <label for="${id}"><strong>${d.Deliverable}</strong> <small class="badge">${d.Category}</small></label>
      </div>
    `));
  });
}

async function onSuggest(){
  const txt = document.querySelector("#rfpText").value || "";
  const data = await api("/api/suggest_by_text", {method:"POST", body:JSON.stringify({rfp_text:txt})});
  const sugg = document.querySelector("#suggestions");
  sugg.innerHTML = "";
  (data.suggested || []).forEach(s => {
    sugg.append(el(`<span class="pill">${s.deliverable}<span class="hit">+${s.confidence}</span></span>`));
    // pre-check matching deliverables
    const elx = document.querySelector(`#deliv_${s.deliverable_code}`);
    if(elx) elx.checked = true;
  });
}

function selectedDeliverables(){
  return Array.from(document.querySelectorAll("#deliverableList input[type=checkbox]:checked"))
    .map(x => x.dataset.code);
}

async function onBuild(){
  const codes = selectedDeliverables();
  if(codes.length===0){ alert("Select at least one deliverable."); return; }

  const pricingMode = document.querySelector("#pricingMode").value;
  const blendedRate = Number(document.querySelector("#blendedRate").value || 0) || null;
  const rateBand    = document.querySelector("#rateBand").value;

  const useSlack    = document.querySelector("#useSlack").checked;
  const slackInternal = Number(document.querySelector("#slackInternal").value || 0);
  const slackClient   = Number(document.querySelector("#slackClient").value || 0);
  const slackGlobal   = Number(document.querySelector("#slackGlobal").value || 0);
  const projectStart  = document.querySelector("#projectStart").value || null;

  // Scenario specs
  const useTemplates = document.querySelector("#useTemplates").checked;
  let specA, specB;
  if(useTemplates){
    specA = {mode:"template", scenario_key: document.querySelector("#scenarioA").value};
    specB = {mode:"template", scenario_key: document.querySelector("#scenarioB").value};
  } else {
    specA = {mode:"bundle", bundle: document.querySelector("#bundleA").value};
    specB = {mode:"bundle", bundle: document.querySelector("#bundleB").value};
  }

  const payload = {
    selected_deliverable_codes: codes,
    scenario_a: specA,
    scenario_b: specB,
    pricing_mode: pricingMode,
    blended_rate: blendedRate,
    rate_band: rateBand,
    use_slack: useSlack,
    slack_after_internal: slackInternal,
    slack_after_client: slackClient,
    slack_global_pct: slackGlobal,
    project_start: projectStart
  };

  const res = await api("/api/build", {method:"POST", body:JSON.stringify(payload)});
  SCENARIOS = res;
  renderScenarios(res);
}

function renderScenarios(data){
  const box = document.querySelector("#scenarios");
  box.innerHTML = "";
  ["A","B"].forEach(key => {
    const scn = data[key];
    const head = `
      <h3>Scenario ${key} <span class="badge">${scn.pricing_mode}${scn.pricing_mode==='Per_Resource' ? ' · ' + scn.rate_band : ''}</span>
        ${scn.pricing_mode==='Flat_Blended' ? `<span class="badge">${Number(scn.blended_rate||0).toFixed(0)}/hr</span>`:''}
      </h3>
      <div><strong>Total Hours:</strong> ${Number(scn.totals.hours).toFixed(2)} &nbsp; <strong>Total Price:</strong> ${currency(scn.totals.price)}</div>
    `;
    const wrap = el(`<div class="scenario">${head}<div></div></div>`);

    scn.items.forEach(d => {
      const tgPills = d.included_task_groups.map(tg => `<span class="pill">${tg}</span>`).join(" ");
      const rows = (d.hours_by_role||[]).map(r => `
        <tr><td>${r.Resource_Title} <small class="badge">${r.Seniority}</small></td><td>${Number(r.Hours).toFixed(2)}</td></tr>
      `).join("");
      const sched = (d.schedule||[]).map(s => `
        <tr><td>${s.task_group}</td><td>${s.start_date}</td><td>${s.end_date}</td><td>${s.duration_days}</td></tr>
      `).join("");
      const card = el(`
        <div class="card" style="background:#0f141d;">
          <h4>${d.deliverable} <span class="badge">${d.category}</span> <span class="badge">${d.complexity}×${d.tier}</span></h4>
          <div class="inline">${tgPills}</div>
          <table class="tbl"><thead><tr><th>Role</th><th>Hours</th></tr></thead><tbody>${rows || '<tr><td colspan="2">No hours</td></tr>'}</tbody></table>
          <div class="inline"><strong>Deliverable Total Hours:</strong> ${Number(d.total_hours).toFixed(2)} &nbsp; <strong>Price:</strong> ${currency(d.price)}</div>
          <details>
            <summary>Timeline (auto)</summary>
            <table class="tbl"><thead><tr><th>Task Group</th><th>Start</th><th>End</th><th>Days</th></tr></thead><tbody>${sched || '<tr><td colspan="4">No schedule</td></tr>'}</tbody></table>
          </details>
        </div>
      `);
      wrap.append(card);
    });

    box.append(wrap);
  });

  document.querySelector("#totA").innerText = currency(data.A.totals.price);
  document.querySelector("#totB").innerText = currency(data.B.totals.price);
}

async function onExport(which){
  if(!SCENARIOS){ alert("Build scenarios first."); return; }
  const res = await fetch("/api/export", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({scenario: SCENARIOS[which]})
  });
  if(!res.ok){ alert("Export failed"); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `workfront_export_${which}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

window.addEventListener("load", boot);