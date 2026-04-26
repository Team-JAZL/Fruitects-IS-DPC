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
    
    const fruits = ["Apple", "Guava", "Mango"];
    const detectedFruit = fruits[Math.floor(Math.random() * fruits.length)];
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = progress + '%';
        progressLabel.innerText = `Analyzing ${detectedFruit}: ${progress}%`;
        
        localStorage.setItem('liveAdminUpdate', JSON.stringify({
            active: true,
            targetFruit: detectedFruit,
            progress: progress,
            liveConfidence: Math.floor((progress / 100) * 15) + 80
        }));

        if (progress >= 100) {
            clearInterval(interval);
            localStorage.setItem('liveAdminUpdate', JSON.stringify({ active: false }));
            showFinalResult(detectedFruit);
        }
    }, 200);
}

function showFinalResult(fruitName) {
    isProcessing = false;
    processingOverlay.classList.add('hidden');
    resultCard.classList.remove('hidden');
    
    // THE 4 STAGES
    const states = [
        { status: "Healthy", color: "text-emerald-500", bg: "bg-emerald-100", border: "border-emerald-500" },
        { status: "Ripe", color: "text-yellow-500", bg: "bg-yellow-100", border: "border-yellow-500" },
        { status: "Overripe", color: "text-orange-500", bg: "bg-orange-100", border: "border-orange-500" },
        { status: "Rotten", color: "text-red-500", bg: "bg-red-100", border: "border-red-500" }
    ];
    
    const result = states[Math.floor(Math.random() * states.length)];
    const qualityConf = Math.floor(Math.random() * 10) + 88;

    // Update User UI Colors
    const statusText = document.getElementById('resultStatus');
    const badge = document.getElementById('resultBadge');
    const card = document.getElementById('resultCard');

    statusText.innerText = result.status;
    statusText.className = `status-text ${result.color}`;
    
    badge.innerText = result.status;
    badge.className = `px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest ${result.bg} ${result.color.replace('text', 'text-dark')}`;

    card.className = `reveal bg-white rounded-3xl shadow-xl border-2 p-8 transition-all ${result.border}`;

    document.getElementById('resultFruitType').innerText = fruitName;
    document.getElementById('resultSubtext').innerHTML = `Certainty: <strong>${qualityConf}%</strong>`;

    // Save for Admin
    const history = JSON.parse(localStorage.getItem('fruitScanHistory') || '[]');
    history.unshift({
        fruitType: fruitName,
        status: result.status,
        confidence: qualityConf,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('fruitScanHistory', JSON.stringify(history.slice(0, 50))); 
}