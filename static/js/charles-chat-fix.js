// CHARLES Chat Fix - Direct message sending
console.log('[CHARLES FIX] Loading chat fix...');

window.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        // Override the sendMessage function in ChatGPTSidebar
        if (window.chatgptSidebar && window.chatgptSidebar.sendMessage) {
            const originalSendMessage = window.chatgptSidebar.sendMessage.bind(window.chatgptSidebar);
            
            window.chatgptSidebar.sendMessage = function() {
                console.log('[CHARLES FIX] sendMessage called');
                const input = document.getElementById('chatgpt-input');
                
                if (!input || !input.value.trim()) {
                    console.log('[CHARLES FIX] No input value');
                    return;
                }
                
                const message = input.value.trim();
                console.log('[CHARLES FIX] Message to send:', message);
                input.value = '';
                
                // Add message to UI
                const messagesDiv = document.getElementById('chatgpt-messages');
                if (messagesDiv) {
                    const msgEl = document.createElement('div');
                    msgEl.className = 'chatgpt-message chatgpt-message-user';
                    msgEl.textContent = message;
                    messagesDiv.appendChild(msgEl);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
                
                // Send directly to API
                console.log('[CHARLES FIX] Sending to API...');
                fetch('/api/agent/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        context: {},
                        session_id: window.aiAssistant?.sessionId || 'default',
                        gpt5_tier: 'auto'
                    })
                })
                .then(response => {
                    console.log('[CHARLES FIX] Response status:', response.status);
                    return response.json();
                })
                .then(result => {
                    console.log('[CHARLES FIX] Response data:', result);
                    
                    // Add response to UI
                    if (messagesDiv && result.message) {
                        const respEl = document.createElement('div');
                        respEl.className = 'chatgpt-message chatgpt-message-assistant';
                        respEl.textContent = result.message;
                        messagesDiv.appendChild(respEl);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                })
                .catch(error => {
                    console.error('[CHARLES FIX] Error:', error);
                    if (messagesDiv) {
                        const errEl = document.createElement('div');
                        errEl.className = 'chatgpt-message chatgpt-message-assistant';
                        errEl.textContent = '❌ Error: ' + error.message;
                        messagesDiv.appendChild(errEl);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                });
            };
            
            console.log('[CHARLES FIX] ✅ sendMessage override installed');
        }
    }, 2000);
});