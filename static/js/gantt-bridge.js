// gantt-bridge.js
// The Gantt calls this to push timeline edits into the Scenario store.
(function(){
  function emitChange(payload) {
    document.dispatchEvent(new CustomEvent("gantt:changed", { detail: payload || {} }));
  }
  window.GanttBridge = { emitChange };
})();
