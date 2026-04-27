// ===== DOM Elements =====
const btnCamera = document.getElementById('btnCamera');
const btnUpload = document.getElementById('btnUpload');
const btnClear = document.getElementById('btnClear');
const fileInput = document.getElementById('fileInput');
const previewImage = document.getElementById('previewImage');
const cameraContainer = document.getElementById('cameraContainer');
const cameraVideo = document.getElementById('cameraVideo');
const emptyState = document.getElementById('emptyState');
const captureGallery = document.getElementById('captureGallery');
const linkStatus = document.getElementById('linkStatus');
const linkPulse = document.getElementById('linkPulse');
const linkDot = document.getElementById('linkDot');
const tabScan = document.getElementById('tabScan');
const tabHistory = document.getElementById('tabHistory');
const scanPanel = document.getElementById('scanPanel');
const historyPanel = document.getElementById('historyPanel');
const filterFruit = document.getElementById('filterFruit');
const filterSort = document.getElementById('filterSort');
const filterDate = document.getElementById('filterDate');
const btnReloadHistory = document.getElementById('btnReloadHistory');
const historyList = document.getElementById('historyList');
const historyEmpty = document.getElementById('historyEmpty');
const historyError = document.getElementById('historyError');

const apiBase = window.location.protocol.startsWith('http') && window.location.port ?
    `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api` :
    'http://127.0.0.1:8001/api';

// ===== State =====
let cameraStream = null;
let cameraOpen = false;
let brokerOnline = false;
let capturedImages = [];
let historyItems = [];

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    updateLinkStatus();
    setInterval(updateLinkStatus, 2000);
    switchTab('scan');
});

function setupEventListeners() {
    btnUpload.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files || []);
        handleUploadFiles(files);
    });

    btnCamera.addEventListener('click', () => {
        if (!cameraOpen) {
            openCamera();
        } else {
            capturePhoto();
        }
    });

    btnClear.addEventListener('click', clearCaptures);
    tabScan.addEventListener('click', () => switchTab('scan'));
    tabHistory.addEventListener('click', () => switchTab('history'));
    filterFruit.addEventListener('change', renderHistory);
    filterSort.addEventListener('change', renderHistory);
    filterDate.addEventListener('change', renderHistory);
    btnReloadHistory.addEventListener('click', loadHistory);
}

async function fetchJson(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Network error');
        return await res.json();
    } catch (err) {
        return null;
    }
}

function switchTab(tab) {
    if (tab === 'history') {
        tabScan.classList.replace('bg-emerald-600', 'bg-white');
        tabScan.classList.replace('text-white', 'text-gray-700');
        tabScan.classList.replace('border', 'border-gray-200');
        tabScan.classList.remove('shadow-sm');
        tabHistory.classList.replace('bg-white', 'bg-emerald-600');
        tabHistory.classList.replace('text-gray-700', 'text-white');
        tabHistory.classList.add('shadow-sm');
        scanPanel.classList.add('hidden');
        historyPanel.classList.remove('hidden');
        loadHistory();
    } else {
        tabHistory.classList.replace('bg-emerald-600', 'bg-white');
        tabHistory.classList.replace('text-white', 'text-gray-700');
        tabHistory.classList.replace('border', 'border-gray-200');
        tabHistory.classList.remove('shadow-sm');
        tabScan.classList.replace('bg-white', 'bg-emerald-600');
        tabScan.classList.replace('text-gray-700', 'text-white');
        tabScan.classList.add('shadow-sm');
        historyPanel.classList.add('hidden');
        scanPanel.classList.remove('hidden');
    }
}

async function openCamera() {
    if (!brokerOnline) {
        alert('Broker is offline. Connect the broker before capturing.');
        return;
    }

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        cameraVideo.srcObject = cameraStream;
        cameraContainer.classList.remove('hidden');
        emptyState.classList.add('hidden');
        cameraOpen = true;
        btnCamera.innerHTML = '<i data-lucide="aperture" class="w-4 h-4"></i> Capture';
        btnClear.classList.remove('hidden');
        lucide.createIcons();
    } catch (err) {
        alert('Camera error. Please ensure you are on HTTPS and allow camera access.');
    }
}

function capturePhoto() {
    if (!cameraStream) return;

    const videoWidth = cameraVideo.videoWidth;
    const videoHeight = cameraVideo.videoHeight;
    const size = Math.min(videoWidth, videoHeight);
    const sx = (videoWidth - size) / 2;
    const sy = (videoHeight - size) / 2;

    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraVideo, sx, sy, size, size, 0, 0, size, size);

    const dataUrl = canvas.toDataURL('image/jpeg');
    addThumbnail(dataUrl);
    setPreviewImage(dataUrl);
    publishImages([dataUrl]);
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    cameraContainer.classList.add('hidden');
    cameraOpen = false;
    btnCamera.innerHTML = '<i data-lucide="camera" class="w-5 h-5"></i> Open Camera';
}

function setPreviewImage(dataUrl) {
    previewImage.src = dataUrl;
    previewImage.classList.remove('hidden');
    emptyState.classList.add('hidden');
    btnClear.classList.remove('hidden');
}

function addThumbnail(dataUrl) {
    capturedImages.unshift(dataUrl);
    if (capturedImages.length > 6) {
        capturedImages.pop();
    }

    captureGallery.innerHTML = capturedImages.map(image => `
        <div class="w-20 h-20 rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
            <img src="${image}" class="w-full h-full object-cover" alt="Capture thumbnail" />
        </div>
    `).join('');
    captureGallery.classList.remove('hidden');
}

async function handleUploadFiles(files) {
    if (files.length === 0) return;
    if (!brokerOnline) {
        alert('Broker is offline. Connect the broker before uploading.');
        return;
    }

    const readers = files.map(file => new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = event => resolve(event.target.result);
        reader.readAsDataURL(file);
    }));

    const dataUrls = await Promise.all(readers);
    dataUrls.forEach(dataUrl => {
        addThumbnail(dataUrl);
        setPreviewImage(dataUrl);
    });

    publishImages(dataUrls);
}

async function publishSingleImage(rawImage) {
    const response = await fetch(`${apiBase}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: [rawImage] })
    });

    if (!response.ok) {
        throw new Error(`Publish request failed with status ${response.status}`);
    }
    return await response.json();
}

async function publishImages(dataUrls) {
    const rawImages = dataUrls.map(url => url.startsWith('data:') ? url.split(',')[1] : url);
    const failures = [];

    for (const rawImage of rawImages) {
        try {
            await publishSingleImage(rawImage);
        } catch (err) {
            console.error('Publish failed for one image', err);
            failures.push(err);
        }
    }

    if (failures.length > 0) {
        alert('Some images could not be sent to the broker. Please retry those uploads.');
    }
}

function clearCaptures() {
    capturedImages = [];
    captureGallery.innerHTML = '';
    captureGallery.classList.add('hidden');
    previewImage.src = '';
    previewImage.classList.add('hidden');
    emptyState.classList.remove('hidden');
    btnClear.classList.add('hidden');
    stopCamera();
}

async function loadHistory() {
    historyError.classList.add('hidden');
    historyList.innerHTML = '';
    historyEmpty.classList.add('hidden');

    const data = await fetchJson(`${apiBase}/history`);
    if (!data || !Array.isArray(data.history)) {
        historyError.innerText = 'Unable to load scanned history at this time.';
        historyError.classList.remove('hidden');
        return;
    }

    historyItems = data.history.map(item => ({
        ...item,
        analyzed_at: item.analyzed_at || '',
        confidence: item.confidence || '0%',
        disease: item.disease || 'Unknown',
        fruit: item.fruit || 'Unknown'
    }));

    renderHistory();
}

function formatDateForFilter(value) {
    return value ? value.replace(/-/g, '/').split(' ')[0] : '';
}

function filterHistory(items) {
    let filtered = [...items];
    const fruit = filterFruit.value;
    const sort = filterSort.value;
    const date = formatDateForFilter(filterDate.value.trim());

    if (fruit !== 'all') {
        filtered = filtered.filter(item => item.fruit === fruit);
    }
    if (date) {
        filtered = filtered.filter(item => formatDateForFilter(item.analyzed_at).startsWith(date));
    }

    filtered.sort((a, b) => {
        const aTime = a.analyzed_at ? new Date(a.analyzed_at).getTime() : 0;
        const bTime = b.analyzed_at ? new Date(b.analyzed_at).getTime() : 0;
        return sort === 'asc' ? aTime - bTime : bTime - aTime;
    });

    return filtered;
}

function renderHistory() {
    const items = filterHistory(historyItems);
    historyList.innerHTML = '';
    historyError.classList.add('hidden');

    if (items.length === 0) {
        historyEmpty.classList.remove('hidden');
        return;
    }

    historyEmpty.classList.add('hidden');
    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-[120px_minmax(0,1fr)] gap-4 p-4';
        card.innerHTML = `
            <div class="h-32 rounded-3xl overflow-hidden bg-gray-100 border border-gray-200">
                <img src="data:image/jpeg;base64,${item.image_data}" class="w-full h-full object-cover" alt="${item.fruit} scan" />
            </div>
            <div class="flex flex-col justify-between gap-4">
                <div class="space-y-2">
                    <div class="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.2em] text-gray-500 font-black">
                        <span>${item.fruit_id}</span>
                        <span class="px-2 py-1 bg-gray-100 rounded-full">${item.fruit}</span>
                    </div>
                    <h3 class="text-lg font-black text-gray-900">${item.disease}</h3>
                    <p class="text-sm text-gray-500">Confidence: <span class="font-semibold text-gray-900">${item.confidence}</span></p>
                </div>
                <div class="text-xs text-gray-400">Analyzed: ${item.analyzed_at ? formatDateForFilter(item.analyzed_at) : 'Unknown date'}</div>
            </div>
        `;
        historyList.appendChild(card);
    });
}

async function updateLinkStatus() {
    try {
        const status = await fetchJson(`${apiBase}/status`);
        brokerOnline = Boolean(status && status.broker_running);
        if (brokerOnline) {
            linkStatus.innerText = 'Broker connected';
            linkStatus.classList.remove('text-gray-500');
            linkStatus.classList.add('text-emerald-600');
            linkDot.classList.remove('bg-red-500');
            linkDot.classList.add('bg-emerald-500');
            linkPulse.classList.remove('bg-red-400');
            linkPulse.classList.add('bg-emerald-400');
            btnCamera.disabled = false;
            btnUpload.disabled = false;
            btnCamera.classList.remove('opacity-50', 'cursor-not-allowed');
            btnUpload.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            linkStatus.innerText = 'Broker offline';
            linkStatus.classList.remove('text-emerald-600');
            linkStatus.classList.add('text-gray-500');
            linkDot.classList.remove('bg-emerald-500');
            linkDot.classList.add('bg-red-500');
            linkPulse.classList.remove('bg-emerald-400');
            linkPulse.classList.add('bg-red-400');
            btnCamera.disabled = true;
            btnUpload.disabled = true;
            btnCamera.classList.add('opacity-50', 'cursor-not-allowed');
            btnUpload.classList.add('opacity-50', 'cursor-not-allowed');
            stopCamera();
        }
    } catch (err) {
        brokerOnline = false;
        linkStatus.innerText = 'Broker unreachable';
        linkStatus.classList.remove('text-emerald-600');
        linkStatus.classList.add('text-gray-500');
        linkDot.classList.remove('bg-emerald-500');
        linkDot.classList.add('bg-red-500');
        linkPulse.classList.remove('bg-emerald-400');
        linkPulse.classList.add('bg-red-400');
        btnCamera.disabled = true;
        btnUpload.disabled = true;
        btnCamera.classList.add('opacity-50', 'cursor-not-allowed');
        btnUpload.classList.add('opacity-50', 'cursor-not-allowed');
        stopCamera();
    }
}
