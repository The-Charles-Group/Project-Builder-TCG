
# PATCH_INSTRUCTIONS: Add an opt‑in “LEARN” button (frontend)

1) In your Step 2 UI (e.g., `static/index.html`) add:
```html
<button id="learnBtn" type="button">LEARN (opt‑in)</button>
```

2) In `static/app.js`, add:
```js
(function attachLearn(){
  const btn = document.getElementById('learnBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const rfpText = (window.APB?.step2?.rfpText) || "";
    const selected = Array.from(window.APB?.step2?.selectedCodes || []);
    const components = (window.APB?.selectionStore?.componentsByDeliv)
      ? Object.fromEntries(window.APB.selectionStore.componentsByDeliv) : {};
    try {
      const res = await fetch("/api/brain/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rfp_text: rfpText,
          selected_deliverables: selected,
          components_by_deliv: components,
          outcome: "accepted",
          notes: "learn-from-ui"
        })
      });
      const data = await res.json();
      alert("Learning event: " + (data?.message || res.status));
    } catch (e) {
      alert("Learn call failed: " + e);
    }
  });
})();
```

This **only** updates **draft** learning. To make it influence live results, use `/admin/brain` → **Publish**.
