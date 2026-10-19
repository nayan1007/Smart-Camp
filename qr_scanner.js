// QR Code Camera Scanner & Look-up Controller
// Powered by html5-qrcode library

let html5QrCode = null;
let isScanning = false;

document.addEventListener('DOMContentLoaded', () => {
    const scanContainer = document.getElementById('reader');
    if (!scanContainer) return;

    const startBtn = document.getElementById('startScanBtn');
    const stopBtn = document.getElementById('stopScanBtn');
    const manualBtn = document.getElementById('manualLookupBtn');
    const manualInput = document.getElementById('manualCodeInput');

    if (startBtn) startBtn.addEventListener('click', startScanner);
    if (stopBtn) stopBtn.addEventListener('click', stopScanner);

    if (manualBtn && manualInput) {
        manualBtn.addEventListener('click', () => {
            const val = manualInput.value.trim();
            if (val) processQrPayload(val);
        });
        manualInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const val = manualInput.value.trim();
                if (val) processQrPayload(val);
            }
        });
    }
});

function startScanner() {
    if (isScanning) return;

    const qrRegionId = "reader";
    html5QrCode = new Html5Qrcode(qrRegionId);

    const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 }
    };

    html5QrCode.start(
        { facingMode: "environment" },
        config,
        (decodedText, decodedResult) => {
            console.log("QR Decoded: ", decodedText);
            stopScanner();
            processQrPayload(decodedText);
        },
        (errorMessage) => {
            // Scanner scanning frame... ignore minor frame errors
        }
    ).then(() => {
        isScanning = true;
        document.getElementById('startScanBtn')?.classList.add('hidden');
        document.getElementById('stopScanBtn')?.classList.remove('hidden');
        document.getElementById('scannerStatus')?.classList.remove('hidden');
    }).catch(err => {
        alert("Camera access was not granted or not available. You can use the manual device code entry below!");
        console.error("Camera error:", err);
    });
}

function stopScanner() {
    if (html5QrCode && isScanning) {
        html5QrCode.stop().then(() => {
            isScanning = false;
            document.getElementById('startScanBtn')?.classList.remove('hidden');
            document.getElementById('stopScanBtn')?.classList.add('hidden');
            document.getElementById('scannerStatus')?.classList.add('hidden');
        }).catch(err => console.error("Stop error:", err));
    }
}

function processQrPayload(qrText) {
    const resultBox = document.getElementById('scanResultBox');
    const resultContent = document.getElementById('scanResultContent');
    if (!resultBox || !resultContent) return;

    resultBox.classList.remove('hidden');
    resultContent.innerHTML = `
        <div class="flex items-center justify-center p-6 text-slate-500">
            <svg class="animate-spin h-6 w-6 mr-3 text-blue-600" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            Querying campus inventory for ${qrText}...
        </div>
    `;

    fetch('/api/scan-qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qr_code: qrText })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.found) {
            resultContent.innerHTML = `
                <div class="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200">
                    <div class="font-bold text-lg mb-1">Device Not Found</div>
                    <p class="text-sm">${data.message || 'No matching device found for scanned payload.'}</p>
                </div>
            `;
            return;
        }

        const dev = data.device;
        const active = data.active_rental;
        const booking = data.pending_booking;

        let statusColor = "bg-emerald-100 text-emerald-800";
        if (dev.status === 'rented') statusColor = "bg-blue-100 text-blue-800";
        else if (dev.status === 'maintenance') statusColor = "bg-amber-100 text-amber-800";

        let actionHtml = '';
        if (dev.status === 'available' || dev.status === 'booked') {
            actionHtml = `
                <a href="/staff/issue-device?code=${dev.code}" class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm shadow">
                    ✓ Issue This Device
                </a>
            `;
        } else if (dev.status === 'rented') {
            actionHtml = `
                <a href="/staff/receive-device?code=${dev.code}" class="inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg text-sm shadow">
                    📥 Receive & Inspect Device
                </a>
            `;
        }

        resultContent.innerHTML = `
            <div class="p-6 bg-white rounded-xl shadow-sm border border-slate-200">
                <div class="flex items-start justify-between">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="px-2.5 py-0.5 text-xs font-bold rounded-full ${statusColor} uppercase tracking-wider">${dev.status}</span>
                            <span class="text-xs text-slate-500 font-mono">${dev.code}</span>
                        </div>
                        <h3 class="text-xl font-bold text-slate-900 mt-1">${dev.name}</h3>
                        <p class="text-sm text-slate-600">${dev.brand} ${dev.model} • S/N: ${dev.serial_number}</p>
                    </div>
                    <div class="text-right">
                        <div class="text-lg font-bold text-blue-600">₹${dev.price_per_day.toFixed(0)}<span class="text-xs text-slate-500">/day</span></div>
                        <div class="text-xs text-slate-500">${dev.location}</div>
                    </div>
                </div>

                ${active ? `
                    <div class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                        <div class="font-semibold text-blue-900">Active Rental: ${active.rental_code}</div>
                        <div class="text-blue-800 text-xs mt-0.5">Rented to: <strong>${active.student_name}</strong> (${active.department})</div>
                        <div class="text-blue-700 text-xs">Due Date: <strong>${active.due_date}</strong></div>
                    </div>
                ` : ''}

                ${booking ? `
                    <div class="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm">
                        <div class="font-semibold text-emerald-900">Approved Reservation: ${booking.booking_code}</div>
                        <div class="text-emerald-800 text-xs mt-0.5">Reserved by: <strong>${booking.student_name}</strong></div>
                        <div class="text-emerald-700 text-xs">Dates: ${booking.start_date} to ${booking.end_date}</div>
                    </div>
                ` : ''}

                <div class="mt-5 flex items-center justify-between pt-4 border-t border-slate-100">
                    <div class="text-xs text-slate-400">Condition: <span class="font-medium text-slate-700">${dev.condition}</span></div>
                    <div class="space-x-2">
                        ${actionHtml}
                        <button onclick="showQrModal('${dev.code}', '${dev.qr_code_url}', '${dev.name}', '${dev.serial_number}')" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium">
                            View QR Badge
                        </button>
                    </div>
                </div>
            </div>
        `;
    })
    .catch(err => {
        resultContent.innerHTML = `<div class="p-4 bg-red-50 text-red-600 rounded-lg">Error processing QR payload: ${err}</div>`;
    });
}
