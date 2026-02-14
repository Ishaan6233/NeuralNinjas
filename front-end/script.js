let gameActive = false;
let attempts = 0;

const fileInput = document.getElementById('fileInput');
const uploadStep = document.getElementById('uploadStep');
const gameStep = document.getElementById('gameStep');
const gameImage = document.getElementById('gameImage');
const gameContainer = document.getElementById('gameContainer');
const message = document.getElementById('message');
const attemptsDisplay = document.getElementById('attempts');
const playAgainBtn = document.getElementById('playAgainBtn');

// *** IMPORTANT: Change this to your actual game image path ***
const GAME_IMAGE_PATH = 'images/batman-game.jpg';  // Replace with your image filename

// Batman's location - adjust these coordinates based on your image
const batmanLocation = {
  x: 0.5,      // 50% from left (0.0 to 1.0)
  y: 0.5,      // 50% from top (0.0 to 1.0)
  radius: 50   // Detection radius in pixels
};

// Handle file upload
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file && file.type.startsWith('image/')) {
    // User uploaded an image, now show the game image
    startGame();
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

uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.style.backgroundColor = '';
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    // User uploaded an image, now show the game image
    startGame();
  }
});

// Start the game
function startGame() {
  gameImage.src = GAME_IMAGE_PATH;
  showStep('game');
  gameActive = true;
  attempts = 0;
  attemptsDisplay.textContent = attempts;
}

// Game click handler
gameImage.addEventListener('click', (e) => {
  if (!gameActive) return;

  attempts++;
  attemptsDisplay.textContent = attempts;

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
    // Success!
    marker.classList.add('success-marker');
    gameContainer.appendChild(marker);
    message.textContent = `🦇 You found Batman in ${attempts} attempt${attempts !== 1 ? 's' : ''}!`;
    message.className = 'message success';
    gameActive = false;
    playAgainBtn.style.display = 'inline-block';
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

// Helper functions
function showStep(step) {
  uploadStep.classList.remove('active');
  gameStep.classList.remove('active');

  if (step === 'upload') uploadStep.classList.add('active');
  if (step === 'game') gameStep.classList.add('active');
}

function playAgain() {
  // Clear markers
  const markers = gameContainer.querySelectorAll('.click-marker');
  markers.forEach(m => m.remove());
  
  // Reset game state
  gameActive = true;
  attempts = 0;
  attemptsDisplay.textContent = attempts;
  message.textContent = '';
  playAgainBtn.style.display = 'none';
}

function resetGame() {
  gameActive = false;
  attempts = 0;
  message.textContent = '';
  playAgainBtn.style.display = 'none';
  fileInput.value = '';

  const markers = gameContainer.querySelectorAll('.click-marker');
  markers.forEach(m => m.remove());

  showStep('upload');
}