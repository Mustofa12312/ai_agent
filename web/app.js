const chatHistory = document.getElementById('chat-history');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const themeToggle = document.getElementById('theme-toggle');
const clearBtn = document.getElementById('clear-btn');

// ==== Konfigurasi Marked.js untuk Markdown parsing ====
marked.setOptions({
    gfm: true,
    breaks: true,
    sanitize: false, // Penting agar formatting tabel/list berjalan
});

// ==== Event Listeners ====

// Auto-resize input text area secara halus
messageInput.addEventListener('input', function() {
    this.style.height = 'auto'; // Reset
    this.style.height = (this.scrollHeight) + 'px'; // Sesuaikan
    if (this.value.trim() === "") {
        this.style.height = 'auto';
    }
    
    // Highlight icon kalau ada teks
    if(this.value.trim() !== "") {
        sendBtn.style.color = 'var(--accent)';
    } else {
        sendBtn.style.color = 'var(--text-muted)';
    }
});

// Shift+Enter untuk baris baru, Enter untuk kirim
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Submit form (komunikasi ke API backend)
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Reset box input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.style.color = 'var(--text-muted)';
    
    // 1. Tampilkan pesan user ke layar
    appendMessage('user', message);
    
    // 2. Tampilkan indikator loading / typing
    appendTypingIndicator();
    
    try {
        // Kirim request ke FastAPI Backend (sinkron ke worker thread)
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Hapus indikator loading
        removeTypingIndicator();
        
        // 3. Tampilkan jawaban AI
        appendMessage('ai', data.reply);
    } catch(err) {
        console.error(err);
        removeTypingIndicator();
        appendMessage('ai', '❌ **Terjadi kesalahan jaringan!** Pastikan backend server `uvicorn` berjalan.');
    }
});

// Toggle Dark/Light Mode
themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // Ganti icon
    const icon = themeToggle.querySelector('i');
    if(newTheme === 'light') {
        icon.classList.replace('fa-moon', 'fa-sun');
    } else {
        icon.classList.replace('fa-sun', 'fa-moon');
    }
});

// Clear layar interaktif
clearBtn.addEventListener('click', () => {
    if(confirm('Apakah Anda yakin ingin menghapus obrolan dari layar ini? (Tidak menghapus memory AI)')) {
        chatHistory.innerHTML = '';
        appendMessage('ai', 'Layar obrolan dibersihkan. Memory saya masih ada kok! Ada yang ingin dilanjutkan? ✨');
    }
});

// ==== Logika Tampilan & Manipulasi DOM ====

function scrollToBottom() {
    chatHistory.scrollTo({
        top: chatHistory.scrollHeight,
        behavior: 'smooth'
    });
}

async function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;
    const iconCls = role === 'ai' ? 'fa-robot' : 'fa-user';
    
    // Pesan User: Langsung muncul (plaintext)
    if (role === 'user') {
        msgDiv.innerHTML = `
            <div class="avatar"><i class="fa-solid ${iconCls}"></i></div>
            <div class="content"><p>${escapeHtml(content)}</p></div>
        `;
        chatHistory.appendChild(msgDiv);
        scrollToBottom();
        return;
    }
    
    // Pesan AI: Animasi mengetik (Markdown streaming)
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    
    msgDiv.innerHTML = `<div class="avatar"><i class="fa-solid ${iconCls}"></i></div>`;
    msgDiv.appendChild(contentDiv);
    chatHistory.appendChild(msgDiv);
    
    // Setup kecepatan animasi
    let currentText = '';
    const chunkSize = 3;  // Jumlah karakter per frame (makin besar makin ngebut)
    const delay = 15;     // Jeda per ketikan (milidetik)
    
    // Matikan smooth scroll sementara animasi berjalan agar tidak laggy
    chatHistory.style.scrollBehavior = 'auto';
    
    for (let i = 0; i < content.length; i += chunkSize) {
        currentText += content.substring(i, i + chunkSize);
        contentDiv.innerHTML = marked.parse(currentText);
        
        // Paksa scroll terus ke bawah mengikuti kursor ketik
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        await new Promise(r => setTimeout(r, delay));
    }
    
    // Kembalikan ke smooth
    chatHistory.style.scrollBehavior = 'smooth';
    scrollToBottom();
}

function appendTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ai-message typing-box`;
    msgDiv.id = 'typing-indicator';
    
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="content" style="padding: 0.8rem 1.5rem; width: auto !important; border-color: rgba(0, 240, 255, 0.4);">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTo({
        top: chatHistory.scrollHeight,
        behavior: 'smooth'
    });
}

function removeTypingIndicator() {
    const target = document.getElementById('typing-indicator');
    if (target) {
        target.remove();
    }
}

// Utilitas untuk escape HTML agar input user tidak rusak layout 
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; }).replace(/\n/g, '<br>');
}

// Inisialisasi awal UI
window.onload = () => {
    // Berikan parse pesan pembuka di layar
    const firstMsg = chatHistory.querySelector('.content');
    if(firstMsg) {
        const rawContent = "Halo, Boss! Saya **Madura AI**, AI Agent interaktif Anda.\n\nApa yang ingin kita kerjakan hari ini? *Cobalah menyuruh saya mencari berita, mengecek cuaca, membuat daftar catatan file, atau apapun!*";
        firstMsg.innerHTML = marked.parse(rawContent);
    }
};

// ==== Settings Logic ====
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeModalBtn = document.querySelector('.close-btn');
const settingsForm = document.getElementById('settings-form');

const aiNameInput = document.getElementById('ai-name-input');
const userNameInput = document.getElementById('user-name-input');
const personalityInput = document.getElementById('personality-input');

if (settingsBtn) {
    settingsBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        settingsModal.style.display = 'flex';
        
        try {
            const res = await fetch('/api/config');
            const cfg = await res.json();
            aiNameInput.value = cfg.ai_name || "Madura Ai";
            userNameInput.value = cfg.user_name || "Boss";
            personalityInput.value = cfg.personality || "santai";
        } catch(err) {
            console.error(err);
        }
    });
}

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });
}

window.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.style.display = 'none';
    }
});

if (settingsForm) {
    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const newConfig = {
            ai_name: aiNameInput.value,
            user_name: userNameInput.value,
            personality: personalityInput.value
        };
        
        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig)
            });
            const data = await res.json();
            alert(data.message);
            settingsModal.style.display = 'none';
            
            // Perbarui header
            const headerTitle = document.querySelector('.agent-info h3');
            if (headerTitle) headerTitle.innerText = newConfig.ai_name;
            
        } catch(err) {
            console.error(err);
            alert("Gagal menyimpan konfigurasi!");
        }
    });
}
