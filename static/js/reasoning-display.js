/**
 * AI Reasoning Display Component
 * Shows detailed AI thinking steps in real-time with black font styling
 */

class ReasoningDisplay {
    constructor() {
        this.container = null;
        this.reasoningText = null;
        this.progressBar = null;
        this.stageIndicator = null;
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;

        // Create reasoning display container
        this.container = document.createElement('div');
        this.container.id = 'ai-reasoning-display';
        this.container.className = 'reasoning-display';
        this.container.style.cssText = `
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            width: 90%;
            max-width: 800px;
            background: white;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        // Stage indicator
        this.stageIndicator = document.createElement('div');
        this.stageIndicator.className = 'reasoning-stage';
        this.stageIndicator.style.cssText = `
            color: #000;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
        `;

        // Progress bar
        const progressContainer = document.createElement('div');
        progressContainer.style.cssText = `
            width: 100%;
            height: 4px;
            background: #e0e0e0;
            border-radius: 2px;
            margin-bottom: 12px;
            overflow: hidden;
        `;

        this.progressBar = document.createElement('div');
        this.progressBar.style.cssText = `
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #2196F3);
            width: 0%;
            transition: width 0.3s ease;
        `;
        progressContainer.appendChild(this.progressBar);

        // Reasoning text with thinking animation
        this.reasoningText = document.createElement('div');
        this.reasoningText.className = 'reasoning-text';
        this.reasoningText.style.cssText = `
            color: #000;
            font-size: 14px;
            line-height: 1.6;
            min-height: 40px;
        `;

        // Thinking dots animation
        const thinkingDots = document.createElement('span');
        thinkingDots.className = 'thinking-dots';
        thinkingDots.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        thinkingDots.style.cssText = `
            display: inline-block;
            margin-left: 4px;
        `;

        // Add pulsing animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes thinking-pulse {
                0%, 20% { opacity: 0; }
                50% { opacity: 1; }
                100% { opacity: 0; }
            }
            .thinking-dots span {
                animation: thinking-pulse 1.4s infinite;
                color: #000;
                font-weight: bold;
            }
            .thinking-dots span:nth-child(2) {
                animation-delay: 0.2s;
            }
            .thinking-dots span:nth-child(3) {
                animation-delay: 0.4s;
            }
            .reasoning-display.active {
                display: block !important;
                animation: slideDown 0.3s ease;
            }
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateX(-50%) translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }
            }
        `;
        document.head.appendChild(style);

        // Assemble components
        this.container.appendChild(this.stageIndicator);
        this.container.appendChild(progressContainer);
        this.container.appendChild(this.reasoningText);
        this.reasoningText.appendChild(thinkingDots);

        // Add to page
        document.body.appendChild(this.container);
        this.initialized = true;

        console.log('[REASONING] Display component initialized');
    }

    show(stage, reasoning, progress = 0) {
        if (!this.initialized) this.init();

        // Update content
        this.stageIndicator.textContent = stage || 'Processing...';
        
        if (reasoning) {
            this.reasoningText.innerHTML = reasoning;
        }

        // Update progress bar
        this.progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;

        // Show container
        this.container.classList.add('active');
        this.container.style.display = 'block';

        console.log(`[REASONING] ${stage} - ${reasoning || 'Processing'} (${progress}%)`);
    }

    hide() {
        if (this.container) {
            this.container.classList.remove('active');
            setTimeout(() => {
                this.container.style.display = 'none';
            }, 300);
        }
    }

    showMultiPhase(phases, currentPhaseIndex, reasoning, progress) {
        if (!this.initialized) this.init();

        // Create phase indicator
        const phaseIndicator = phases.map((phase, idx) => {
            const active = idx === currentPhaseIndex;
            const completed = idx < currentPhaseIndex;
            const icon = completed ? '✓' : (active ? '▶' : '○');
            const color = completed ? '#4CAF50' : (active ? '#2196F3' : '#999');
            return `<span style="color: ${color}; margin: 0 8px;">${icon} ${phase}</span>`;
        }).join('');

        const fullStage = `<div style="margin-bottom: 8px;">${phaseIndicator}</div>`;
        
        this.stageIndicator.innerHTML = fullStage;
        this.reasoningText.textContent = reasoning || 'Processing...';
        this.progressBar.style.width = `${progress}%`;
        this.container.classList.add('active');
        this.container.style.display = 'block';
    }
}

// Global instance
window.reasoningDisplay = new ReasoningDisplay();

// Auto-show reasoning when any button is clicked
document.addEventListener('DOMContentLoaded', () => {
    // Intercept all button clicks
    document.addEventListener('click', (e) => {
        const button = e.target.closest('button');
        if (button && !button.disabled) {
            const action = button.textContent.trim() || 'Processing';
            window.reasoningDisplay.show(
                `${action}...`,
                'Preparing request and initializing AI analysis',
                5
            );
        }
    });

    console.log('[REASONING] Auto-display enabled for all buttons');
});

// Export for use in other scripts
export { ReasoningDisplay };
