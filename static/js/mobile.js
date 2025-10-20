/* ================================================================================
   Agency Project Builder - Mobile JavaScript Enhancements
   Handles mobile menu, view toggle, and touch interactions
   ================================================================================ */

(function() {
  'use strict';

  // Mobile Detection
  const MobileDetector = {
    isMobile: function() {
      return window.innerWidth < 768;
    },
    isTablet: function() {
      return window.innerWidth >= 768 && window.innerWidth <= 1024;
    },
    isDesktop: function() {
      return window.innerWidth > 1024;
    },
    isTouchDevice: function() {
      return ('ontouchstart' in window) || 
             (navigator.maxTouchPoints > 0) || 
             (navigator.msMaxTouchPoints > 0);
    }
  };

  // Mobile Menu Controller
  const MobileMenu = {
    menuElement: null,
    overlayElement: null,
    toggleButton: null,
    isOpen: false,

    init: function() {
      this.menuElement = document.getElementById('mobile-menu');
      this.overlayElement = document.getElementById('mobile-menu-overlay');
      this.toggleButton = document.getElementById('mobile-menu-toggle');
      
      if (!this.menuElement || !this.overlayElement || !this.toggleButton) {
        console.warn('[MobileMenu] Required elements not found');
        return;
      }

      this.bindEvents();
      this.checkViewMode();
    },

    bindEvents: function() {
      // Escape key to close menu
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      // Handle swipe gestures
      if (MobileDetector.isTouchDevice()) {
        this.initSwipeGestures();
      }

      // Handle resize events
      window.addEventListener('resize', () => {
        if (!MobileDetector.isMobile() && this.isOpen) {
          this.close();
        }
      });
    },

    initSwipeGestures: function() {
      let touchStartX = 0;
      let touchEndX = 0;
      const threshold = 100; // Minimum swipe distance

      document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
      });

      document.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        this.handleSwipe(touchStartX, touchEndX, threshold);
      });
    },

    handleSwipe: function(startX, endX, threshold) {
      const swipeDistance = startX - endX;
      
      // Swipe left to open menu (from right edge)
      if (swipeDistance < -threshold && startX > window.innerWidth - 50) {
        this.open();
      }
      
      // Swipe right to close menu (when menu is open)
      if (swipeDistance > threshold && this.isOpen) {
        this.close();
      }
    },

    toggle: function() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    },

    open: function() {
      if (!this.menuElement || !this.overlayElement) return;
      
      this.isOpen = true;
      this.menuElement.classList.add('open');
      this.overlayElement.classList.add('visible');
      this.toggleButton.classList.add('active');
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
      
      // Sync Auto-Fix checkbox with current state
      this.syncAutoFixCheckbox();
      
      // Analytics
      console.log('[MobileMenu] Opened');
    },
    
    syncAutoFixCheckbox: function() {
      const checkbox = document.getElementById('mobile-auto-fix');
      if (checkbox && window.aiAssistant) {
        checkbox.checked = window.aiAssistant.autoFixEnabled || false;
      }
    },

    close: function() {
      if (!this.menuElement || !this.overlayElement) return;
      
      this.isOpen = false;
      this.menuElement.classList.remove('open');
      this.overlayElement.classList.remove('visible');
      this.toggleButton.classList.remove('active');
      document.body.style.overflow = ''; // Restore scrolling
      
      // Analytics
      console.log('[MobileMenu] Closed');
    },

    checkViewMode: function() {
      const savedMode = localStorage.getItem('apb.viewMode');
      if (savedMode === 'desktop') {
        document.body.classList.add('force-desktop-view');
        const toggle = document.getElementById('view-toggle');
        if (toggle) toggle.checked = true;
      }
    }
  };

  // View Mode Controller
  const ViewModeController = {
    init: function() {
      this.loadSavedPreference();
    },

    toggle: function(checkbox) {
      if (checkbox.checked) {
        this.setDesktopView();
      } else {
        this.setMobileView();
      }
    },

    setMobileView: function() {
      document.body.classList.remove('force-desktop-view');
      localStorage.setItem('apb.viewMode', 'mobile');
      console.log('[ViewMode] Switched to mobile view');
      
      // Trigger resize event for components that need to update
      window.dispatchEvent(new Event('resize'));
    },

    setDesktopView: function() {
      document.body.classList.add('force-desktop-view');
      localStorage.setItem('apb.viewMode', 'desktop');
      console.log('[ViewMode] Switched to desktop view');
      
      // Close mobile menu if open
      MobileMenu.close();
      
      // Trigger resize event for components that need to update
      window.dispatchEvent(new Event('resize'));
    },

    loadSavedPreference: function() {
      const savedMode = localStorage.getItem('apb.viewMode');
      const toggle = document.getElementById('view-toggle');
      
      if (savedMode === 'desktop') {
        document.body.classList.add('force-desktop-view');
        if (toggle) toggle.checked = true;
      } else {
        document.body.classList.remove('force-desktop-view');
        if (toggle) toggle.checked = false;
      }
    }
  };

  // Touch-friendly Enhancements
  const TouchEnhancements = {
    init: function() {
      if (!MobileDetector.isTouchDevice()) return;

      this.enhanceButtons();
      this.enhanceInputs();
      this.addFastClick();
    },

    enhanceButtons: function() {
      // Add active states to all buttons for better feedback
      document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('touchstart', function() {
          this.classList.add('touch-active');
        });
        
        button.addEventListener('touchend', function() {
          setTimeout(() => {
            this.classList.remove('touch-active');
          }, 100);
        });
      });
    },

    enhanceInputs: function() {
      // Prevent zoom on input focus on iOS
      document.querySelectorAll('input, textarea, select').forEach(input => {
        input.addEventListener('focus', function() {
          if (MobileDetector.isMobile()) {
            document.querySelector('meta[name="viewport"]').setAttribute('content', 
              'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no');
          }
        });
        
        input.addEventListener('blur', function() {
          if (MobileDetector.isMobile()) {
            document.querySelector('meta[name="viewport"]').setAttribute('content', 
              'width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes');
          }
        });
      });
    },

    addFastClick: function() {
      // Remove 300ms delay on touch devices
      let lastTouchEnd = 0;
      document.addEventListener('touchend', function(event) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
          event.preventDefault();
        }
        lastTouchEnd = now;
      }, false);
    }
  };

  // Responsive Layout Manager
  const ResponsiveLayoutManager = {
    init: function() {
      this.adjustLayouts();
      this.bindResizeHandler();
    },

    bindResizeHandler: function() {
      let resizeTimeout;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
          this.adjustLayouts();
        }, 250);
      });
    },

    adjustLayouts: function() {
      const isMobile = MobileDetector.isMobile();
      const isTablet = MobileDetector.isTablet();
      const isDesktop = MobileDetector.isDesktop();

      // Add body classes for CSS targeting
      document.body.classList.toggle('is-mobile', isMobile);
      document.body.classList.toggle('is-tablet', isTablet);
      document.body.classList.toggle('is-desktop', isDesktop);

      // Adjust Step 2 selection grid
      this.adjustSelectionGrid(isMobile);
      
      // Adjust pricing tables
      this.adjustPricingTables(isMobile);
      
      console.log(`[Layout] Adjusted for ${isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'}`);
    },

    adjustSelectionGrid: function(isMobile) {
      const selectionGrid = document.querySelector('.selection-grid');
      if (!selectionGrid) return;

      if (isMobile) {
        // Stack panels vertically on mobile
        selectionGrid.style.gridTemplateColumns = '1fr';
        
        // Adjust panel heights for mobile
        document.querySelectorAll('#s2-deliv-list, #s2-comp-list, #s2-l2-list').forEach(list => {
          list.style.height = '250px';
        });
      } else {
        // Restore desktop layout
        selectionGrid.style.gridTemplateColumns = '1fr 1fr 350px';
        
        // Restore desktop heights
        document.querySelectorAll('#s2-deliv-list, #s2-comp-list, #s2-l2-list').forEach(list => {
          list.style.height = '400px';
        });
      }
    },

    adjustPricingTables: function(isMobile) {
      const pricingTable = document.getElementById('pricing-details-table');
      if (!pricingTable) return;

      if (isMobile) {
        // Make table scrollable horizontally on mobile
        const wrapper = pricingTable.closest('.table-wrapper');
        if (!wrapper) {
          const newWrapper = document.createElement('div');
          newWrapper.className = 'table-wrapper';
          newWrapper.style.overflowX = 'auto';
          newWrapper.style.WebkitOverflowScrolling = 'touch';
          pricingTable.parentNode.insertBefore(newWrapper, pricingTable);
          newWrapper.appendChild(pricingTable);
        }
      }
    }
  };

  // Auto-Fix Controller for Mobile Menu
  const AutoFixController = {
    init: function() {
      const checkbox = document.getElementById('mobile-auto-fix');
      if (!checkbox) return;
      
      // Wire up the checkbox to toggle Auto-Fix
      checkbox.addEventListener('change', (e) => {
        if (window.aiAssistant && typeof window.aiAssistant.toggleAutoFix === 'function') {
          // Only toggle if the state doesn't match
          if (e.target.checked !== window.aiAssistant.autoFixEnabled) {
            window.aiAssistant.toggleAutoFix();
          }
        } else {
          console.warn('[AutoFix] AI Assistant not available');
        }
      });
      
      console.log('[AutoFix] Mobile checkbox wired up');
    }
  };
  
  // Global Functions (exposed for onclick handlers)
  window.toggleMobileMenu = function() {
    MobileMenu.toggle();
  };

  window.toggleViewMode = function(checkbox) {
    ViewModeController.toggle(checkbox);
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      MobileMenu.init();
      ViewModeController.init();
      TouchEnhancements.init();
      ResponsiveLayoutManager.init();
      AutoFixController.init();
      console.log('[Mobile] All mobile enhancements initialized');
    });
  } else {
    // DOM already loaded
    MobileMenu.init();
    ViewModeController.init();
    TouchEnhancements.init();
    ResponsiveLayoutManager.init();
    AutoFixController.init();
    console.log('[Mobile] All mobile enhancements initialized');
  }

  // Expose for debugging
  window.MobileUtils = {
    detector: MobileDetector,
    menu: MobileMenu,
    viewMode: ViewModeController,
    layout: ResponsiveLayoutManager
  };

})();