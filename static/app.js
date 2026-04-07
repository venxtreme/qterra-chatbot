const chatStream = document.getElementById('chat-stream');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const REQUEST_TIMEOUT_MS = 20000;

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
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleSend();
    });
}

function normalizeMessageText(text) {
    return typeof text === 'string' ? text : '';
}

// Safely render text content and turn URLs into clickable anchors without innerHTML.
function buildMessageParagraph(text) {
    const paragraph = document.createElement('p');
    const safeText = normalizeMessageText(text);
    const lines = safeText.split('\n');
    const urlRegex = /(https?:\/\/[^\s]+)/g;

    lines.forEach((line, lineIndex) => {
        let lastIndex = 0;
        let match;
        while ((match = urlRegex.exec(line)) !== null) {
            const url = match[0];
            const matchStart = match.index;

            if (matchStart > lastIndex) {
                paragraph.appendChild(document.createTextNode(line.slice(lastIndex, matchStart)));
            }

            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.target = '_blank';
            anchor.rel = 'noopener noreferrer';
            anchor.textContent = url;
            paragraph.appendChild(anchor);
            lastIndex = matchStart + url.length;
        }

        if (lastIndex < line.length) {
            paragraph.appendChild(document.createTextNode(line.slice(lastIndex)));
        }

        if (lineIndex < lines.length - 1) {
            paragraph.appendChild(document.createElement('br'));
        }
    });

    return paragraph;
}

function scrollToBottom() {
    chatStream.scrollTop = chatStream.scrollHeight;
}

function addMessage(text, isUser = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${isUser ? 'user-message' : 'ai-message'}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.appendChild(buildMessageParagraph(text));

    const timeElement = document.createElement('span');
    timeElement.className = 'message-time';
    timeElement.textContent = time;

    wrapper.appendChild(bubble);
    wrapper.appendChild(timeElement);

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
    
    let timeoutId = null;
    try {
        const controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        // Send to FastAPI
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ messages: messageHistory }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        timeoutId = null;

        let data = null;
        try {
            data = await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {
            const apiDetail = typeof data.detail === 'string' ? data.detail : 'API Error';
            throw new Error(apiDetail);
        }

        const aiText = typeof data.response === 'string'
            ? data.response
            : "Sorry, I couldn't read the server response. Please try again.";
        
        hideTypingIndicator();
        addMessage(aiText, false);
        messageHistory.push({ role: "assistant", content: aiText });
        
    } catch (error) {
        console.error(error);
        hideTypingIndicator();
        const isTimeout = error && error.name === 'AbortError';
        addMessage(
            isTimeout
                ? "Sorry, the request timed out. Please try again."
                : "Sorry, I'm having trouble connecting to the server. Please try again later.",
            false
        );
    } finally {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
        }
        isTyping = false;
        chatInput.focus();
    }
}

// Start app
document.addEventListener('DOMContentLoaded', init);
