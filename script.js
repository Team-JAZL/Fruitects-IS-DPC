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

const apiBase = window.location.protocol.startsWith('http') && window.location.port ?
    `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api` :
    'http://127.0.0.1:8001/api';

// ===== State =====
let cameraStream = null;
let cameraOpen = false;
let brokerOnline = false;
let capturedImages = [];

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    updateLinkStatus();
    setInterval(updateLinkStatus, 2000);
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

async function publishImages(dataUrls) {
    const rawImages = dataUrls.map(url => url.startsWith('data:') ? url.split(',')[1] : url);
    try {
        await fetch(`${apiBase}/publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ images: rawImages })
        });
    } catch (err) {
        console.error('Publish failed', err);
        alert('Unable to send images to broker. Please check the broker connection.');
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
