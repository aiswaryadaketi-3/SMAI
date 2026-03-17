// --- AUTHENTICATION STATE ---
let currentUser = null;

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    checkUserStatus();
});

async function checkUserStatus() {
    try {
        const response = await fetch('/user_status');
        const data = await response.json();
        if (data.logged_in) {
            updateAuthUI(data.username);
        } else {
            updateAuthUI(null);
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
    }
}

function updateAuthUI(username) {
    const loginBtn = document.getElementById('login-nav-btn');
    const userInfo = document.getElementById('user-info');
    const displayUser = document.getElementById('display-username');

    if (username) {
        currentUser = username;
        if (loginBtn) loginBtn.classList.add('hidden');
        if (userInfo) userInfo.classList.remove('hidden');
        if (displayUser) displayUser.textContent = username;
    } else {
        currentUser = null;
        if (loginBtn) loginBtn.classList.remove('hidden');
        if (userInfo) userInfo.classList.add('hidden');
    }
}

// Modal Control
function openAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.classList.remove('hidden');
}

function closeAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');

    if (tab === 'login') {
        if (loginForm) loginForm.classList.remove('hidden');
        if (registerForm) registerForm.classList.add('hidden');
        if (tabLogin) tabLogin.classList.add('active');
        if (tabRegister) tabRegister.classList.remove('active');
    } else {
        if (loginForm) loginForm.classList.add('hidden');
        if (registerForm) registerForm.classList.remove('hidden');
        if (tabLogin) tabLogin.classList.remove('active');
        if (tabRegister) tabRegister.classList.add('active');
    }
}

// Auth Handlers
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-user').value;
    const password = document.getElementById('login-pass').value;

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            updateAuthUI(data.username);
            closeAuthModal();
            alert('Login successful!');
        } else {
            alert(data.error || 'Login failed');
        }
    } catch (error) {
        alert('Error connecting to server');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-user').value;
    const password = document.getElementById('reg-pass').value;

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            alert('Registration successful! Please login.');
            switchAuthTab('login');
        } else {
            alert(data.error || 'Registration failed');
        }
    } catch (error) {
        alert('Error connecting to server');
    }
}

async function handleLogout() {
    try {
        await fetch('/logout');
        updateAuthUI(null);
        navigate('landing');
        alert('Logged out');
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Page Navigation
function navigate(pageId) {
    // Auth gate for protected sections
    const protectedPages = ['dashboard', 'assessment'];
    if (protectedPages.includes(pageId) && !currentUser) {
        alert('Please login to access this feature');
        openAuthModal();
        return;
    }

    // Refresh Dashboard stats if navigating there
    if (pageId === 'dashboard') {
        fetchCommunityStats();
    }

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
        if (targetPage) {
            targetPage.classList.remove('hidden');
            // Force reflow
            void targetPage.offsetWidth; 
            targetPage.classList.add('active');
        }
        window.scrollTo(0, 0);
    }, 300);
}

// --- DASHBOARD RENDERING ---
async function fetchCommunityStats() {
    try {
        const response = await fetch('/api/community_stats');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function updateDashboard(stats) {
    if (!stats || stats.total === 0) return;

    // 1. Risk Distribution (Pie Chart)
    const pie = document.getElementById('risk-pie-chart');
    if (pie) {
        const low = stats.distribution.Low;
        const med = stats.distribution.Medium;
        const high = stats.distribution.High;
        
        pie.style.background = `conic-gradient(
            var(--neon-green) 0% ${low}%, 
            var(--neon-yellow) ${low}% ${low + med}%, 
            var(--neon-red) ${low + med}% 100%
        )`;
        
        document.getElementById('low-pct').innerText = low;
        document.getElementById('med-pct').innerText = med;
        document.getElementById('high-pct').innerText = high;
    }

    // 2. Community Metrics (Bars)
    const stressBar = document.getElementById('stress-bar');
    const sleepBar = document.getElementById('sleep-bar');
    
    if (stressBar) stressBar.style.height = `${stats.averages.stress * 10}%`;
    if (sleepBar) sleepBar.style.height = `${(stats.averages.sleep / 12) * 100}%`;

    // 3. Trend Chart (SVG Path)
    const path = document.getElementById('trend-path');
    const svg = document.getElementById('trend-svg');
    if (path && stats.trend && stats.trend.length > 0) {
        let pathD = "M0,30";
        const step = 100 / (stats.trend.length - 1 || 1);
        
        // Clear old dots
        svg.querySelectorAll('circle').forEach(c => c.remove());

        stats.trend.forEach((point, i) => {
            const x = i * step;
            const y = 30 - point.value; // Map risk_val (10, 20, 30) to y
            pathD += ` L${x},${y}`;
            
            // Add pulse dots for each point
            const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            dot.setAttribute("cx", x);
            dot.setAttribute("cy", y);
            dot.setAttribute("r", "1.5");
            dot.setAttribute("fill", "#38bdf8");
            dot.classList.add("pulse-dot");
            svg.appendChild(dot);
        });
        path.setAttribute('d', pathD);
    }
}

// Assessment Logic
async function handleAssessmentSubmit(e) {
    e.preventDefault();
    
    if (!currentUser) {
        alert('Please login to save your assessment');
        openAuthModal();
        return;
    }

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

        if (response.status === 401) {
            alert('Your session has expired. Please login again.');
            updateAuthUI(null);
            openAuthModal();
            return;
        }

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const result = await response.json();

        // Update Result Page UI
        const riskLabel = document.getElementById('risk-label');
        if (riskLabel) riskLabel.innerText = result.level;
        
        const ring = document.getElementById('risk-indicator');
        if (ring) {
            ring.classList.remove('risk-low', 'risk-medium', 'risk-high');
            const classToAdd = `risk-${result.level.toLowerCase()}`;
            ring.classList.add(classToAdd);
        }
        
        const explanation = document.getElementById('risk-explanation');
        if (explanation) explanation.innerText = result.explanation;
        
        const list = document.getElementById('recommendation-list');
        if (list) {
            list.innerHTML = '';
            result.tips.forEach(tip => {
                const li = document.createElement('li');
                li.innerText = tip;
                list.appendChild(li);
            });
        }

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
    if (chatWindow) {
        chatWindow.classList.toggle('hidden');
        if (!chatWindow.classList.contains('hidden')) {
            const input = document.getElementById('chat-input-field');
            if (input) input.focus();
        }
    }
}

function handleChat(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    if (!currentUser) {
        alert('Please login to chat with SafeMind AI');
        openAuthModal();
        return;
    }

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

        if (response.status === 401) {
            appendMessage("Please login to continue our conversation.", 'bot');
            updateAuthUI(null);
            openAuthModal();
            return;
        }

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
    if (chatBody) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);
        msgDiv.innerText = text;
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }
}
