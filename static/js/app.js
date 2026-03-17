// Page Navigation
function navigate(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
        // Give time for transition out before hiding
        setTimeout(() => {
            if(!page.classList.contains('active')) {
                page.classList.add('hidden');
            }
        }, 300);
    });
    
    setTimeout(() => {
        const targetPage = document.getElementById(pageId);
        targetPage.classList.remove('hidden');
        // Force reflow
        void targetPage.offsetWidth; 
        targetPage.classList.add('active');
        window.scrollTo(0, 0);
    }, 300);
}

// Assessment Logic
async function handleAssessmentSubmit(e) {
    e.preventDefault();
    
    // Show loading state (optional polish)
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerText;
    submitBtn.innerText = "Processing...";
    submitBtn.disabled = true;

    // Gather values
    const assessmentData = {
        age: parseInt(document.getElementById('age').value),
        sleep: parseInt(document.getElementById('sleep').value),
        stress: parseInt(document.getElementById('stress').value),
        social: document.getElementById('social').value,
        mood: document.getElementById('mood').checked,
        screen: parseInt(document.getElementById('screen').value)
    };

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(assessmentData)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const result = await response.json();

        // Update Result Page UI
        document.getElementById('risk-label').innerText = result.level;
        const ring = document.getElementById('risk-indicator');
        
        // Clear previous risk classes
        ring.classList.remove('risk-low', 'risk-medium', 'risk-high');
        
        // Add new risk class
        const classToAdd = `risk-${result.level.toLowerCase()}`;
        ring.classList.add(classToAdd);
        
        document.getElementById('risk-explanation').innerText = result.explanation;
        
        const list = document.getElementById('recommendation-list');
        list.innerHTML = '';
        result.tips.forEach(tip => {
            const li = document.createElement('li');
            li.innerText = tip;
            list.appendChild(li);
        });

        // Navigate to results
        navigate('result');

    } catch (error) {
        console.error('Error:', error);
        alert("An error occurred while calculating your risk. Please try again.");
    } finally {
        submitBtn.innerText = originalBtnText;
        submitBtn.disabled = false;
    }
}

// Chatbot functionality
function toggleChat() {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.classList.toggle('hidden');
    if (!chatWindow.classList.contains('hidden')) {
        document.getElementById('chat-input-field').focus();
    }
}

function handleChat(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const inputField = document.getElementById('chat-input-field');
    const msg = inputField.value.trim();
    if (!msg) return;

    // Append user message
    appendMessage(msg, 'user');
    inputField.value = '';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: msg })
        });

        if (!response.ok) {
            throw new Error('Chat API response was not ok');
        }

        const data = await response.json();
        appendMessage(data.reply, 'bot');

    } catch (error) {
        console.error('Chat Error:', error);
        appendMessage("I'm having a little trouble thinking right now. Please try again.", 'bot');
    }
}

function appendMessage(text, sender) {
    const chatBody = document.getElementById('chat-body');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.innerText = text;
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    // Add glowing animation to initial page setup logic if needed.
});
