/**
 * Test script for CHARLES AGENT chat functionality
 * This will simulate user interaction and test the chat system
 */

function testCharlesChat() {
    console.log('[TEST] Starting CHARLES chat functionality test...');
    
    // 1. Check if ChatGPT sidebar and AI Assistant are loaded
    if (!window.chatgptSidebar) {
        console.error('[TEST] ERROR: ChatGPT sidebar not found!');
        return false;
    }
    
    if (!window.aiAssistant) {
        console.error('[TEST] ERROR: AI Assistant not found!');
        return false;
    }
    
    console.log('[TEST] ✅ Both ChatGPT sidebar and AI Assistant are loaded');
    
    // 2. Open the sidebar if not already open
    if (!window.chatgptSidebar.isExpanded) {
        console.log('[TEST] Opening sidebar...');
        window.chatgptSidebar.expand();
        
        // Wait a moment for animation
        setTimeout(() => {
            console.log('[TEST] ✅ Sidebar opened');
            continueTest();
        }, 500);
    } else {
        console.log('[TEST] Sidebar already open');
        continueTest();
    }
    
    function continueTest() {
        // 3. Check if handleUserMessage exists
        if (typeof window.aiAssistant.handleUserMessage !== 'function') {
            console.error('[TEST] ERROR: handleUserMessage() method not found!');
            return false;
        }
        
        console.log('[TEST] ✅ handleUserMessage() method exists');
        
        // 4. Set up network monitoring
        const originalFetch = window.fetch;
        let requestMade = false;
        let requestData = null;
        let responseData = null;
        
        window.fetch = async function(...args) {
            const [url, options] = args;
            
            // Check if this is our agent chat request
            if (url === '/api/agent/chat' && options?.method === 'POST') {
                requestMade = true;
                requestData = JSON.parse(options.body);
                console.log('[TEST] 📤 POST request to /api/agent/chat detected!');
                console.log('[TEST] Request data:', requestData);
            }
            
            // Call original fetch
            const response = await originalFetch.apply(this, args);
            
            // Clone response to read it
            if (url === '/api/agent/chat') {
                const clonedResponse = response.clone();
                responseData = await clonedResponse.json();
                console.log('[TEST] 📥 Response received:', responseData);
            }
            
            return response;
        };
        
        // 5. Send test message
        const testMessage = "Hello CHARLES, this is a test message. Can you respond?";
        console.log('[TEST] Sending test message:', testMessage);
        
        // Get the current message count
        const messagesContainer = document.getElementById('chatgpt-messages');
        const initialMessageCount = messagesContainer ? messagesContainer.children.length : 0;
        
        // Send the message through handleUserMessage
        window.aiAssistant.handleUserMessage(testMessage);
        
        // 6. Wait and check results
        setTimeout(() => {
            // Restore original fetch
            window.fetch = originalFetch;
            
            console.log('[TEST] === Test Results ===');
            
            // Check if request was made
            if (requestMade) {
                console.log('[TEST] ✅ POST request to /api/agent/chat was made');
                console.log('[TEST] ✅ Request included message:', requestData?.message === testMessage);
                console.log('[TEST] ✅ Request included session_id:', !!requestData?.session_id);
                console.log('[TEST] ✅ Request included context:', !!requestData?.context);
            } else {
                console.error('[TEST] ❌ No POST request to /api/agent/chat was detected');
            }
            
            // Check if response was received
            if (responseData) {
                console.log('[TEST] ✅ Response received from server');
                console.log('[TEST] Response success:', responseData.success);
                console.log('[TEST] Response message:', responseData.message);
            } else {
                console.error('[TEST] ❌ No response received');
            }
            
            // Check if messages were added to UI
            const finalMessageCount = messagesContainer ? messagesContainer.children.length : 0;
            const messagesAdded = finalMessageCount - initialMessageCount;
            
            if (messagesAdded > 0) {
                console.log('[TEST] ✅ Messages added to UI:', messagesAdded);
                
                // Check for user message
                const allMessages = Array.from(messagesContainer.children);
                const hasUserMessage = allMessages.some(msg => 
                    msg.classList.contains('chatgpt-message-user') && 
                    msg.textContent.includes(testMessage)
                );
                
                if (hasUserMessage) {
                    console.log('[TEST] ✅ User message displayed correctly');
                } else {
                    console.error('[TEST] ❌ User message not found in UI');
                }
                
                // Check for assistant response
                const hasAssistantResponse = allMessages.some(msg => 
                    msg.classList.contains('chatgpt-message-assistant')
                );
                
                if (hasAssistantResponse) {
                    console.log('[TEST] ✅ Assistant response displayed');
                } else {
                    console.error('[TEST] ⚠️ No assistant response found yet (may still be processing)');
                }
            } else {
                console.error('[TEST] ❌ No messages added to UI');
            }
            
            console.log('[TEST] === Test Complete ===');
            
            // Return summary
            return {
                success: requestMade && responseData && messagesAdded > 0,
                requestMade,
                responseReceived: !!responseData,
                messagesDisplayed: messagesAdded > 0,
                userMessageShown: messagesAdded > 0
            };
            
        }, 3000); // Wait 3 seconds for response
    }
    
    return true;
}

// Wait for everything to be ready, then run the test
function runTestWhenReady() {
    // Check if both components are loaded
    if (window.chatgptSidebar && window.aiAssistant) {
        console.log('[TEST] Components ready, starting test...');
        testCharlesChat();
    } else {
        console.log('[TEST] Waiting for components to initialize...');
        setTimeout(runTestWhenReady, 500);
    }
}

// Start checking after DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runTestWhenReady);
} else {
    // Give a small delay to ensure everything is initialized
    setTimeout(runTestWhenReady, 1000);
}