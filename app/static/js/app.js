/**
 * Embroidery Lead Finder Pro — Premium Frontend JS
 */

// ============ TOAST NOTIFICATIONS ============
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const styles = {
        success: { gradient: 'from-[#43e97b]/20 to-[#38f9d7]/10', border: 'border-[#43e97b]/20', text: 'text-[#43e97b]', icon: 'check-circle' },
        error:   { gradient: 'from-[#f5576c]/20 to-[#f093fb]/10', border: 'border-[#f5576c]/20', text: 'text-[#f5576c]', icon: 'x-circle' },
        warning: { gradient: 'from-[#fee140]/20 to-[#fa709a]/10', border: 'border-[#fee140]/20', text: 'text-[#fee140]', icon: 'alert-triangle' },
        info:    { gradient: 'from-[#667eea]/20 to-[#764ba2]/10', border: 'border-[#667eea]/20', text: 'text-[#667eea]', icon: 'info' },
    };

    const s = styles[type] || styles.info;

    const toast = document.createElement('div');
    toast.className = `toast-enter flex items-center gap-3 px-5 py-4 rounded-2xl bg-gradient-to-r ${s.gradient} border ${s.border} shadow-2xl max-w-sm`;
    toast.style.backdropFilter = 'blur(20px)';
    toast.innerHTML = `
        <i data-lucide="${s.icon}" class="w-5 h-5 ${s.text} flex-shrink-0"></i>
        <span class="text-[13px] text-white/90 font-medium flex-1">${message}</span>
        <button onclick="this.parentElement.classList.add('toast-exit'); setTimeout(() => this.parentElement.remove(), 300)" class="p-1 hover:bg-white/10 rounded-lg transition-colors flex-shrink-0">
            <i data-lucide="x" class="w-3 h-3 text-white/30"></i>
        </button>
    `;

    container.appendChild(toast);
    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [toast] });

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ============ LOADING OVERLAY ============
function showLoading(text = 'Processing...') {
    const overlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    if (overlay) { overlay.classList.remove('hidden'); overlay.classList.add('flex'); }
    if (loadingText) loadingText.textContent = text;
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) { overlay.classList.add('hidden'); overlay.classList.remove('flex'); }
}


// ============ SIDEBAR TOGGLE ============
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('hidden');
}


// ============ CLIPBOARD ============
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success', 2000);
    } catch (err) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;opacity:0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copied to clipboard!', 'success', 2000);
    }
}


// ============ API HELPERS ============
async function apiGet(url) {
    const r = await fetch(url);
    if (!r.ok) { const e = await r.json().catch(() => ({ error: 'Request failed' })); throw new Error(e.error || 'Request failed'); }
    return r.json();
}

async function apiPost(url, data = {}) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!r.ok) { const e = await r.json().catch(() => ({ error: 'Request failed' })); throw new Error(e.error || 'Request failed'); }
    return r.json();
}

async function apiDelete(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok) { const e = await r.json().catch(() => ({ error: 'Request failed' })); throw new Error(e.error || 'Request failed'); }
    return r.json();
}


// ============ UTILITIES ============
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function truncate(str, len = 30) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '…' : str;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function confirmAction(message) {
    return new Promise(resolve => resolve(confirm(message)));
}
