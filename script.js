// ===== DOM Elements =====
const btnScan = document.getElementById('hitScanBtn');
const btnCamera = document.getElementById('btnCamera');
const btnUpload = document.getElementById('btnUpload');
const btnClear = document.getElementById('btnClear');
const btnScanAgain = document.getElementById('btnScanAgain');
const fileInput = document.getElementById('fileInput');
const previewImage = document.getElementById('previewImage');
const cameraContainer = document.getElementById('cameraContainer');
const cameraVideo = document.getElementById('cameraVideo');
const emptyState = document.getElementById('emptyState');
const processingOverlay = document.getElementById('processingOverlay');
const progressBar = document.getElementById('progressBar');
const progressLabel = document.getElementById('progressLabel');
const resultCard = document.getElementById('resultCard');

// ===== State =====
let currentImageData = null;
let cameraStream = null;
let isProcessing = false;

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    btnUpload.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => setImage(event.target.result);
            reader.readAsDataURL(file);
        }
    });

    btnCamera.addEventListener('click', () => {
        if (!cameraStream) { openCamera(); } 
        else { capturePhoto(); }
    });

    btnScan.addEventListener('click', handleAIScan);
    btnClear.addEventListener('click', () => location.reload());
    btnScanAgain.addEventListener('click', () => location.reload());
}

async function openCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        cameraVideo.srcObject = cameraStream;
        cameraContainer.classList.remove('hidden');
        emptyState.classList.add('hidden');
        btnCamera.innerHTML = '<i data-lucide="aperture" class="w-4 h-4"></i> Capture';
        lucide.createIcons();
    } catch (err) {
        alert("Camera error. Please ensure you are on HTTPS.");
    }
}

function capturePhoto() {
    const canvas = document.createElement('canvas');
    canvas.width = cameraVideo.videoWidth;
    canvas.height = cameraVideo.videoHeight;
    canvas.getContext('2d').drawImage(cameraVideo, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg');
    stopCamera();
    setImage(dataUrl);
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    cameraContainer.classList.add('hidden');
}

function setImage(dataUrl) {
    currentImageData = dataUrl;
    previewImage.src = dataUrl;
    previewImage.classList.remove('hidden');
    emptyState.classList.add('hidden');
    btnScan.disabled = false;
    btnClear.classList.remove('hidden');
}

function handleAIScan() {
    if (!currentImageData || isProcessing) return;
    isProcessing = true;
    processingOverlay.classList.remove('hidden');
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = progress + '%';
        progressLabel.innerText = "Analyzing: " + progress + "%";
        if (progress >= 100) {
            clearInterval(interval);
            showResult();
        }
    }, 200);
}

function showResult() {
    isProcessing = false;
    processingOverlay.classList.add('hidden');
    resultCard.classList.remove('hidden');
    
    // Mock Result
    document.getElementById('resultFruitType').innerText = "Mango";
    const status = "Healthy";
    const badge = document.getElementById('resultBadge');
    const statusText = document.getElementById('resultStatus');
    
    badge.innerText = status;
    statusText.innerText = status;
    statusText.className = "status-text text-emerald-500";
    badge.className = "px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-700";
    document.getElementById('resultSubtext').innerText = "This fruit is fresh and safe to eat!";
}