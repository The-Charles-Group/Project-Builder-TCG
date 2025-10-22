// step4-sync.js
// Real-time sync integration for Step 4 (Timeline/Gantt)

(function() {
  let ganttChart = null;
  let isUpdatingGantt = false;
  
  // Wait for dependencies
  function initStep4Sync() {
    if (!window.ScenarioManager || !window.ScenarioStore) {
      setTimeout(initStep4Sync, 100);
      return;
    }
    
    console.log('[Step4 Sync] Initializing real-time sync for timeline');
    
    // Subscribe to ScenarioManager changes
    const unsubscribe = window.ScenarioManager.subscribe((state) => {
      console.log('[Step4 Sync] Received state update');
      
      // Check if we're on Step 4
      const step4Element = document.getElementById('step4');
      if (!step4Element || step4Element.style.display === 'none') {
        return; // Step 4 not visible
      }
      
      // Update timeline with new data
      updateTimelineFromSync(state);
    });
    
    // Store unsubscribe for cleanup
    window.step4SyncUnsubscribe = unsubscribe;
    
    // Listen for pricing changes
    document.addEventListener('pricing:changed', (event) => {
      console.log('[Step4 Sync] Pricing changed:', event.detail);
      
      if (isUpdatingGantt) return;
      
      // Update task duration based on new hours
      updateTaskDuration(event.detail);
    });
    
    // Listen for external change events
    document.addEventListener('scenario:external-change', (event) => {
      console.log('[Step4 Sync] External change detected:', event.detail);
      
      if (isUpdatingGantt) return;
      
      // Refresh affected tasks
      refreshTimelineTasks(event.detail.changedElements);
    });
    
    // Listen for Gantt task updates
    document.addEventListener('gantt:task_updated', (event) => {
      console.log('[Step4 Sync] Gantt task updated:', event.detail);
      
      // Sync back to ScenarioManager
      if (window.ScenarioManager && !isUpdatingGantt) {
        const { deliverableId, start_date, duration_days } = event.detail;
        
        // Update ScenarioStore which will propagate to ScenarioManager
        if (window.ScenarioStore) {
          window.ScenarioStore.updateFromGantt({
            deliverableId,
            durationDays: duration_days,
            start: start_date,
            end: calculateEndDate(start_date, duration_days)
          });
        }
      }
    });
    
    // Override renderGanttChart to add sync
    const originalRenderGantt = window.renderGanttChart;
    if (originalRenderGantt) {
      window.renderGanttChart = function(tasks, targetSelector) {
        console.log('[Step4 Sync] Rendering Gantt with sync');
        
        // Store Gantt instance
        ganttChart = originalRenderGantt.call(this, tasks, targetSelector);
        
        // Subscribe to changes after render
        subscribeToGanttChanges();
        
        return ganttChart;
      };
    }
    
    console.log('[Step4 Sync] Initialized successfully');
  }
  
  // Update timeline from sync state
  function updateTimelineFromSync(state) {
    if (!state.deliverables || state.deliverables.length === 0) return;
    if (isUpdatingGantt) return;
    
    console.log('[Step4 Sync] Updating timeline from sync');
    isUpdatingGantt = true;
    
    try {
      // Get current Gantt tasks
      const ganttContainer = document.querySelector('#gantt-chart, .gantt-container');
      if (!ganttContainer || !ganttChart) {
        console.log('[Step4 Sync] Gantt chart not found');
        return;
      }
      
      // Update each deliverable's timeline representation
      state.deliverables.forEach(deliverable => {
        updateGanttTask(deliverable);
      });
      
      // Flash the Gantt container
      ganttContainer.classList.add('sync-flash');
      setTimeout(() => ganttContainer.classList.remove('sync-flash'), 500);
      
      // Show sync notification
      showTimelineSyncNotification();
      
    } finally {
      isUpdatingGantt = false;
    }
  }
  
  // Update individual Gantt task
  function updateGanttTask(deliverable) {
    if (!ganttChart || !ganttChart.tasks) return;
    
    // Find the task in the Gantt chart
    const task = ganttChart.tasks.find(t => 
      t.id === deliverable.id || 
      t.name === deliverable.title ||
      t.deliverable_code === deliverable.id
    );
    
    if (!task) {
      console.log('[Step4 Sync] Task not found for deliverable:', deliverable.id);
      return;
    }
    
    // Calculate new duration based on hours
    const hoursPerDay = window.ScenarioManager?.state?.hoursPerDay || 6;
    const resourceCount = deliverable.resources?.length || 1;
    const newDuration = Math.ceil(deliverable.hours / (hoursPerDay * resourceCount));
    
    // Check if duration changed
    if (task.duration !== newDuration) {
      console.log('[Step4 Sync] Updating task duration:', {
        task: task.name,
        oldDuration: task.duration,
        newDuration: newDuration
      });
      
      // Update task properties
      task.duration = newDuration;
      task.end = calculateEndDate(task.start, newDuration);
      
      // Refresh the specific task in Gantt
      if (ganttChart.refresh_task) {
        ganttChart.refresh_task(task.id);
      } else if (ganttChart.refresh) {
        ganttChart.refresh();
      }
      
      // Flash the task bar
      const taskBar = document.querySelector(`.gantt-task[data-id="${task.id}"]`);
      if (taskBar) {
        taskBar.classList.add('sync-flash');
        setTimeout(() => taskBar.classList.remove('sync-flash'), 500);
      }
    }
  }
  
  // Update task duration from pricing change
  function updateTaskDuration(pricingData) {
    const { deliverableId, hours, hoursPerDay = 6, resources = [] } = pricingData;
    
    if (!deliverableId || !hours) return;
    
    // Find deliverable in ScenarioManager
    const deliverable = window.ScenarioManager?.state?.deliverables?.find(d => d.id === deliverableId);
    if (!deliverable) return;
    
    // Update the deliverable hours
    deliverable.hours = hours;
    
    // Update Gantt task
    updateGanttTask(deliverable);
  }
  
  // Refresh specific timeline tasks
  function refreshTimelineTasks(changedElements) {
    if (!changedElements || !Array.isArray(changedElements)) return;
    if (!ganttChart) return;
    
    changedElements.forEach(element => {
      if (element.type === 'deliverable' && element.id) {
        // Find deliverable
        const deliverable = window.ScenarioManager?.state?.deliverables?.find(d => d.id === element.id);
        if (deliverable) {
          updateGanttTask(deliverable);
        }
      }
    });
  }
  
  // Subscribe to Gantt changes
  function subscribeToGanttChanges() {
    if (!ganttChart) return;
    
    // Listen for drag events
    if (ganttChart.on) {
      ganttChart.on('date_change', (task, start, end) => {
        console.log('[Step4 Sync] Task date changed:', task.name);
        
        if (!isUpdatingGantt) {
          // Calculate duration in days
          const durationDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
          
          // Emit custom event for sync
          document.dispatchEvent(new CustomEvent('gantt:task_updated', {
            detail: {
              deliverableId: task.id,
              start_date: start.toISOString(),
              end_date: end.toISOString(),
              duration_days: durationDays
            }
          }));
        }
      });
      
      ganttChart.on('progress_change', (task, progress) => {
        console.log('[Step4 Sync] Task progress changed:', task.name, progress);
        
        // Could sync progress to ScenarioManager if needed
      });
    }
  }
  
  // Calculate end date from start and duration
  function calculateEndDate(startDate, durationDays) {
    const start = new Date(startDate);
    const end = new Date(start);
    
    // Add business days (skip weekends)
    let daysAdded = 0;
    while (daysAdded < durationDays) {
      end.setDate(end.getDate() + 1);
      // Skip weekends
      if (end.getDay() !== 0 && end.getDay() !== 6) {
        daysAdded++;
      }
    }
    
    return end.toISOString();
  }
  
  // Show timeline sync notification
  function showTimelineSyncNotification() {
    let notification = document.getElementById('timeline-sync-notification');
    if (!notification) {
      notification = document.createElement('div');
      notification.id = 'timeline-sync-notification';
      notification.style.cssText = `
        position: fixed;
        top: 60px;
        right: 20px;
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 14px;
        z-index: 1000;
        display: none;
        animation: slideIn 0.3s ease;
      `;
      document.body.appendChild(notification);
    }
    
    notification.textContent = '✓ Timeline synced';
    notification.style.display = 'block';
    
    // Hide after 2 seconds
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => {
        notification.style.display = 'none';
        notification.style.animation = 'slideIn 0.3s ease';
      }, 300);
    }, 2000);
  }
  
  // Maintain timeline position during updates
  function saveTimelinePosition() {
    const ganttContainer = document.querySelector('#gantt-chart, .gantt-container');
    if (!ganttContainer) return null;
    
    return {
      scrollLeft: ganttContainer.scrollLeft,
      scrollTop: ganttContainer.scrollTop
    };
  }
  
  function restoreTimelinePosition(position) {
    if (!position) return;
    
    const ganttContainer = document.querySelector('#gantt-chart, .gantt-container');
    if (ganttContainer) {
      ganttContainer.scrollLeft = position.scrollLeft;
      ganttContainer.scrollTop = position.scrollTop;
    }
  }
  
  // Initialize when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStep4Sync);
  } else {
    initStep4Sync();
  }
  
  console.log('[Step4 Sync] Module loaded');
})();