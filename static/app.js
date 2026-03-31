const chatStream = document.getElementById('chat-stream');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

// State
let isTyping = false;
let messageHistory = [];

// Initialize
function init() {
    // We already have the initial generic welcome message in the HTML
    messageHistory.push({
        role: "assistant", 
        content: "Hi, I'm Quinn! How can I help you today?"
    });

    sendBtn.addEventListener('click', handleSend);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });
}

// Convert links in text to actual HTML anchors
function formatText(text) {
    // Regex to match URLs
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
}

function scrollToBottom() {
    chatStream.scrollTop = chatStream.scrollHeight;
}

function addMessage(text, isUser = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${isUser ? 'user-message' : 'ai-message'}`;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Format text and convert links
    const formattedText = formatText(text)
        .replace(/\n/g, '<br/>'); // Handle line breaks
    
    wrapper.innerHTML = `
        <div class="message-bubble">
            <p>${formattedText}</p>
        </div>
        <span class="message-time">${time}</span>
    `;
    
    chatStream.appendChild(wrapper);
    scrollToBottom();
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    `;
    chatStream.appendChild(indicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.className = 'typing-indicator fade-out';
        setTimeout(() => indicator.remove(), 300);
    }
}

async function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isTyping) return;
    
    // UI Update User
    chatInput.value = '';
    addMessage(text, true);
    messageHistory.push({ role: "user", content: text });
    
    // UI Update Typing Status
    isTyping = true;
    showTypingIndicator();
    
    try {
        // Send to FastAPI
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ messages: messageHistory })
        });
        
        if (!response.ok) throw new Error('API Error');
        
        const data = await response.json();
        const aiText = data.response;
        
        hideTypingIndicator();
        addMessage(aiText, false);
        messageHistory.push({ role: "assistant", content: aiText });
        
    } catch (error) {
        console.error(error);
        hideTypingIndicator();
        addMessage("Sorry, I'm having trouble connecting to the server. Please try again later.", false);
    } finally {
        isTyping = false;
        chatInput.focus();
    }
}

// Start app
document.addEventListener('DOMContentLoaded', init);
