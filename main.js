// Smart Campus Electronics Rental - Main JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // 1. Booking Price Calculator
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const totalDaysSpan = document.getElementById('totalDays');
    const totalAmountSpan = document.getElementById('totalAmount');
    const rentalChargesSpan = document.getElementById('rentalCharges');
    const pricePerDay = parseFloat(document.getElementById('pricePerDay')?.value || '0');
    const depositAmount = parseFloat(document.getElementById('depositAmount')?.value || '0');

    function calculateBooking() {
        if (!startDateInput || !endDateInput || !startDateInput.value || !endDateInput.value) return;
        
        const start = new Date(startDateInput.value);
        const end = new Date(endDateInput.value);

        if (end < start) {
            endDateInput.setCustomValidity("End date cannot be earlier than start date.");
            return;
        } else {
            endDateInput.setCustomValidity("");
        }

        const diffTime = Math.abs(end - start);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // inclusive
        const rentalFee = diffDays * pricePerDay;
        const totalFee = rentalFee + depositAmount;
        
        if (totalDaysSpan) totalDaysSpan.textContent = diffDays;
        if (rentalChargesSpan) rentalChargesSpan.textContent = '₹' + rentalFee.toFixed(0);
        if (totalAmountSpan) totalAmountSpan.textContent = '₹' + totalFee.toFixed(0);
    }

    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', calculateBooking);
        endDateInput.addEventListener('change', calculateBooking);
        calculateBooking();
    }

    // 2. Alert Dismissal
    document.querySelectorAll('.alert-dismiss-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const alertBox = e.target.closest('.alert-box');
            if (alertBox) alertBox.remove();
        });
    });
});

// QR Modal Helper Functions
function showQrModal(deviceCode, qrUrl, deviceName, serial) {
    const modal = document.getElementById('qrModal');
    if (!modal) return;

    document.getElementById('qrModalCode').textContent = deviceCode;
    document.getElementById('qrModalName').textContent = deviceName;
    document.getElementById('qrModalSerial').textContent = 'S/N: ' + serial;
    document.getElementById('qrModalImg').src = qrUrl;
    document.getElementById('qrDownloadBtn').href = qrUrl;
    document.getElementById('qrDownloadBtn').download = `QR_${deviceCode}.png`;

    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeQrModal() {
    const modal = document.getElementById('qrModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function printQrCard() {
    window.print();
}

// Universal Back Button Navigation Handler
function goBack() {
    const currentHost = window.location.host;
    if (document.referrer && document.referrer.includes(currentHost) && window.history.length > 1) {
        window.history.back();
    } else if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// Global Toast Notification Helper
function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'fixed top-20 right-4 z-50 flex flex-col space-y-2 pointer-events-none';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgStyles = type === 'error' ? 'bg-red-600 text-white shadow-red-500/30' :
                     type === 'success' ? 'bg-emerald-600 text-white shadow-emerald-500/30' :
                     type === 'warning' ? 'bg-amber-600 text-white shadow-amber-500/30' :
                     'bg-slate-900 text-white shadow-slate-900/30';

    toast.className = `pointer-events-auto px-4 py-3 rounded-xl shadow-xl text-xs font-semibold flex items-center space-x-2.5 transition-all transform duration-300 translate-y-2 opacity-0 ${bgStyles}`;
    toast.innerHTML = `
        <span class="shrink-0">${type === 'error' ? '⚠️' : type === 'success' ? '✓' : 'ℹ️'}</span>
        <span class="flex-1">${message}</span>
        <button class="ml-2 hover:opacity-80 p-0.5" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-4');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
