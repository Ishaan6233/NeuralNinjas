let gameActive = false;
let clicks = 0;
let startTime = null;
let timerInterval = null;
let compositeImagePath = null;

const fileInput = document.getElementById('fileInput');
const uploadStep = document.getElementById('uploadStep');
const readyStep = document.getElementById('readyStep');
const gameStep = document.getElementById('gameStep');
const resultsStep = document.getElementById('resultsStep');
const gameImage = document.getElementById('gameImage');
const gameContainer = document.getElementById('gameContainer');
const message = document.getElementById('message');
const clicksDisplay = document.getElementById('clicks');
const timerDisplay = document.getElementById('timer');
const uploadStatus = document.getElementById('uploadStatus');

// Batman's location - will be provided by Python backend
const batmanLocation = {
  x: 0.5,      // 50% from left (0.0 to 1.0)
  y: 0.5,      // 50% from top (0.0 to 1.0)
  radius: 50   // Detection radius in pixels
};

// Handle file upload
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file && file.type.startsWith('image/')) {
    await uploadAndProcess(file);
  }
});

// Drag and drop
const uploadArea = document.querySelector('.upload-area');
uploadArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadArea.style.backgroundColor = '#333';
});

uploadArea.addEventListener('dragleave', () => {
  uploadArea.style.backgroundColor = '';
});

uploadArea.addEventListener('drop', async (e) => {
  e.preventDefault();
  uploadArea.style.backgroundColor = '';
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    await uploadAndProcess(file);
  }
});

// Upload and process image
async function uploadAndProcess(file) {
  uploadStatus.textContent = 'Uploading and processing image... Please wait.';
  
  const formData = new FormData();
  formData.append('image', file);
  
  try {
    const response = await fetch('/upload', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Image saved to:', result.path);
      
      // TODO: Call Python script here to generate composite
      // For now, we'll use a placeholder
      compositeImagePath = result.path; // This will be the composite image path from Python
      
      uploadStatus.textContent = 'Image processed! Ready to play.';
      
      // Show ready step
      setTimeout(() => {
        showStep('ready');
      }, 1000);
    } else {
      uploadStatus.textContent = 'Failed to upload image. Please try again.';
    }
  } catch (error) {
    console.error('Upload error:', error);
    uploadStatus.textContent = 'Error uploading image. Please try again.';
  }
}

// Start the game
function startGame() {
  // Load the composite image
  gameImage.src = compositeImagePath;
  
  // Show game step
  showStep('game');
  
  // Start timer
  startTime = Date.now();
  timerInterval = setInterval(updateTimer, 100);
  
  // Reset counters
  clicks = 0;
  clicksDisplay.textContent = clicks;
  gameActive = true;
}

// Update timer display
function updateTimer() {
  if (!startTime) return;
  
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  
  timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Game click handler
gameImage.addEventListener('click', (e) => {
  if (!gameActive) return;

  clicks++;
  clicksDisplay.textContent = clicks;

  const rect = gameImage.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;

  // Convert stored percentage to pixels
  const batmanX = batmanLocation.x * gameImage.width;
  const batmanY = batmanLocation.y * gameImage.height;

  // Calculate distance
  const distance = Math.sqrt(
    Math.pow(clickX - batmanX, 2) + 
    Math.pow(clickY - batmanY, 2)
  );

  // Create marker
  const marker = document.createElement('div');
  marker.className = 'click-marker';
  marker.style.left = clickX + 'px';
  marker.style.top = clickY + 'px';

  if (distance <= batmanLocation.radius) {
    // Success! Stop timer
    clearInterval(timerInterval);
    gameActive = false;
    
    marker.classList.add('success-marker');
    gameContainer.appendChild(marker);
    
    // Calculate score
    const timeElapsed = Math.floor((Date.now() - startTime) / 1000);
    const score = calculateScore(clicks, timeElapsed);
    
    // Show results
    setTimeout(() => {
      showResults(clicks, timeElapsed, score);
    }, 1000);
  } else {
    // Try again
    gameContainer.appendChild(marker);
    message.textContent = 'Not quite! Keep looking...';
    message.className = 'message try-again';
    
    // Remove marker after 1 second
    setTimeout(() => {
      marker.remove();
    }, 1000);
  }
});

// Calculate score: 1000 - (clicks × 50) - (seconds × 10)
function calculateScore(clicks, seconds) {
  const baseScore = 1000;
  const clickPenalty = clicks * 50;
  const timePenalty = seconds * 10;
  const score = Math.max(0, baseScore - clickPenalty - timePenalty);
  return score;
}

// Show results
function showResults(clicks, timeElapsed, score) {
  const minutes = Math.floor(timeElapsed / 60);
  const seconds = timeElapsed % 60;
  const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
  
  document.getElementById('finalTime').textContent = timeString;
  document.getElementById('finalClicks').textContent = clicks;
  document.getElementById('finalScore').textContent = score;
  
  showStep('results');
}

// Helper functions
function showStep(step) {
  uploadStep.classList.remove('active');
  readyStep.classList.remove('active');
  gameStep.classList.remove('active');
  resultsStep.classList.remove('active');

  if (step === 'upload') uploadStep.classList.add('active');
  if (step === 'ready') readyStep.classList.add('active');
  if (step === 'game') gameStep.classList.add('active');
  if (step === 'results') resultsStep.classList.add('active');
}

function resetGame() {
  gameActive = false;
  clicks = 0;
  startTime = null;
  compositeImagePath = null;
  message.textContent = '';
  fileInput.value = '';
  uploadStatus.textContent = '';
  
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  const markers = gameContainer.querySelectorAll('.click-marker');
  markers.forEach(m => m.remove());

  showStep('upload');
}