let gameActive = false;
let attempts = 0;
let processing = false;

const fileInput = document.getElementById('fileInput');
const loadingOverlay = document.getElementById('loadingOverlay');
const uploadStep = document.getElementById('uploadStep');
const gameStep = document.getElementById('gameStep');
const gameImage = document.getElementById('gameImage');
const gameContainer = document.getElementById('gameContainer');
const message = document.getElementById('message');
const attemptsDisplay = document.getElementById('attempts');
const playAgainBtn = document.getElementById('playAgainBtn');
const giveUpBtn = document.getElementById('giveUpBtn');

const batmanLocation = {
  x: 0.5,
  y: 0.5,
  radius: 50
};

fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file && file.type.startsWith('image/')) {
    processUploadedImage(file);
  }
});

const uploadArea = document.querySelector('.upload-area');
uploadArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadArea.style.backgroundColor = '#333';
});

uploadArea.addEventListener('dragleave', () => {
  uploadArea.style.backgroundColor = '';
});

uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.style.backgroundColor = '';
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    processUploadedImage(file);
  }
});

function startGame(imagePath) {
  gameImage.src = imagePath;
  showStep('game');
  gameActive = true;
  attempts = 0;
  attemptsDisplay.textContent = attempts;
  message.textContent = '';
  message.className = 'message';
  giveUpBtn.style.display = 'inline-block';
}

async function processUploadedImage(file) {
  if (processing) return;
  processing = true;
  message.textContent = 'Processing image with YOLO segmentation...';
  message.className = 'message';

  const formData = new FormData();
  formData.append('image', file);

  try {
    showLoading(true, 'Processing image with YOLO + depth…');
    const res = await fetch('/api/process', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Failed to process image');
    }

    batmanLocation.x = data.batman.x_norm;
    batmanLocation.y = data.batman.y_norm;
    batmanLocation.radius = data.batman.radius || 42;
    startGame(`${data.output_image_url}?t=${Date.now()}`);
    const vis = data.reason?.sprite?.visible_ratio;
    const sal = data.reason?.sprite?.low_saliency_score;
    const bestObj = data.best_object || 'none';
    if (vis !== undefined && sal !== undefined) {
      message.textContent = `Detected ${data.objects_detected} objects. Best occluder: ${bestObj}. Visible fragment ${(vis * 100).toFixed(0)}%, low-saliency ${(sal * 100).toFixed(0)}%. Find Batman!`;
    } else {
      message.textContent = `Detected ${data.objects_detected} objects. Best occluder: ${bestObj}. Find Batman!`;
    }
    message.className = 'message';
  } catch (err) {
    message.textContent = `Error: ${err.message}`;
    message.className = 'message try-again';
  } finally {
    showLoading(false);
    processing = false;
  }
}

gameImage.addEventListener('click', (e) => {
  if (!gameActive) return;

  attempts++;
  attemptsDisplay.textContent = attempts;

  const rect = gameImage.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;

  const batmanX = batmanLocation.x * gameImage.width;
  const batmanY = batmanLocation.y * gameImage.height;

  const distance = Math.sqrt(
    Math.pow(clickX - batmanX, 2) +
    Math.pow(clickY - batmanY, 2)
  );

  const marker = document.createElement('div');
  marker.className = 'click-marker';
  marker.style.left = clickX + 'px';
  marker.style.top = clickY + 'px';

  if (distance <= batmanLocation.radius) {
    marker.classList.add('success-marker');
    gameContainer.appendChild(marker);
    message.textContent = `You found Batman in ${attempts} attempt${attempts !== 1 ? 's' : ''}!`;
    message.className = 'message success';
    gameActive = false;
    playAgainBtn.style.display = 'inline-block';
    giveUpBtn.style.display = 'none';
  } else {
    gameContainer.appendChild(marker);
    message.textContent = 'Not quite! Keep looking...';
    message.className = 'message try-again';

    setTimeout(() => {
      marker.remove();
    }, 1000);
  }
});

function revealBatmanMarker() {
  const revealX = batmanLocation.x * gameImage.width;
  const revealY = batmanLocation.y * gameImage.height;
  const marker = document.createElement('div');
  marker.className = 'click-marker success-marker';
  marker.style.left = revealX + 'px';
  marker.style.top = revealY + 'px';
  gameContainer.appendChild(marker);
}

function showStep(step) {
  uploadStep.classList.remove('active');
  gameStep.classList.remove('active');

  if (step === 'upload') uploadStep.classList.add('active');
  if (step === 'game') gameStep.classList.add('active');
}

function giveUp() {
  if (!gameActive) return;
  gameActive = false;
  revealBatmanMarker();
  message.textContent = 'Batman revealed. Try again!';
  message.className = 'message try-again';
  playAgainBtn.style.display = 'inline-block';
  giveUpBtn.style.display = 'none';
}

function playAgain() {
  const markers = gameContainer.querySelectorAll('.click-marker');
  markers.forEach((m) => m.remove());

  gameActive = true;
  attempts = 0;
  attemptsDisplay.textContent = attempts;
  message.textContent = '';
  message.className = 'message';
  playAgainBtn.style.display = 'none';
  giveUpBtn.style.display = 'inline-block';
}

function resetGame() {
  gameActive = false;
  attempts = 0;
  message.textContent = '';
  message.className = 'message';
  playAgainBtn.style.display = 'none';
  giveUpBtn.style.display = 'none';
  fileInput.value = '';

  const markers = gameContainer.querySelectorAll('.click-marker');
  markers.forEach((m) => m.remove());

  showStep('upload');
}

function showLoading(state, text = 'Processing…') {
  if (!loadingOverlay) return;
  loadingOverlay.style.display = state ? 'flex' : 'none';
  if (state) {
    loadingOverlay.querySelector('p').textContent = text;
  }
  // Disable buttons while loading
  const buttons = document.querySelectorAll('button');
  buttons.forEach((btn) => { btn.disabled = state; });
}
