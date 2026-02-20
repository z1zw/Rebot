<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheese Collector Game</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }

        body {
            background-color: #F9F9FB;
            color: #1a1a1a;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
            line-height: 1.5;
        }

        .container {
            width: 100%;
            max-width: 800px;
            background-color: #F2F2F5;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            text-align: center;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            color: #D4A017;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            font-size: 1rem;
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }

        .game-info {
            display: flex;
            justify-content: space-between;
            background-color: #EAECF0;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .info-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 120px;
        }

        .info-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.25rem;
        }

        .info-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a1a;
        }

        #score {
            color: #2E7D32;
        }

        #timer {
            color: #1565C0;
        }

        #cheese-count {
            color: #D4A017;
        }

        .game-area {
            position: relative;
            width: 100%;
            height: 400px;
            background-color: #FFFFFF;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid #EAECF0;
            touch-action: none;
            user-select: none;
        }

        #player {
            position: absolute;
            width: 40px;
            height: 40px;
            background-color: #4A90E2;
            border-radius: 50%;
            transition: transform 0.1s;
            z-index: 10;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }

        .cheese {
            position: absolute;
            width: 30px;
            height: 30px;
            background-color: #FFD700;
            border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
            transform: rotate(45deg);
            box-shadow: inset -5px -5px 0 rgba(0, 0, 0, 0.1);
            z-index: 5;
            animation: float 2s infinite ease-in-out;
        }

        .cheese::after {
            content: '';
            position: absolute;
            width: 8px;
            height: 8px;
            background-color: #D4A017;
            border-radius: 50%;
            top: 6px;
            left: 6px;
        }

        @keyframes float {
            0%, 100% { transform: rotate(45deg) translateY(0); }
            50% { transform: rotate(45deg) translateY(-5px); }
        }

        .controls {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-top: 1rem;
        }

        .buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        button {
            padding: 0.9rem 1.8rem;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            min-width: 140px;
        }

        #start-btn {
            background-color: #4CAF50;
            color: white;
        }

        #start-btn:hover {
            background-color: #3d8b40;
        }

        #restart-btn {
            background-color: #FF9800;
            color: white;
        }

        #restart-btn:hover {
            background-color: #e68900;
        }

        #reset-btn {
            background-color: #f44336;
            color: white;
        }

        #reset-btn:hover {
            background-color: #d32f2f;
        }

        .instructions {
            background-color: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #D4A017;
        }

        .instructions h3 {
            margin-bottom: 0.75rem;
            color: #333;
        }

        .instructions ul {
            padding-left: 1.5rem;
            color: #555;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .game-message {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 2rem 3rem;
            border-radius: 16px;
            text-align: center;
            z-index: 100;
            display: none;
            flex-direction: column;
            gap: 1.5rem;
            max-width: 90%;
            width: 400px;
        }

        .game-message h2 {
            font-size: 2rem;
            color: #FFD700;
        }

        .game-message p {
            font-size: 1.2rem;
        }

        .message-btn {
            background-color: #4CAF50;
            color: white;
            align-self: center;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1.5rem;
            }

            .game-area {
                height: 350px;
            }

            .game-info {
                flex-direction: column;
                align-items: center;
                text-align: center;
            }

            .info-box {
                min-width: 100px;
            }

            button {
                min-width: 120px;
                padding: 0.8rem 1.5rem;
            }
        }

        @media (max-width: 480px) {
            body {
                padding: 1rem 0.5rem;
            }

            .container {
                padding: 1rem;
            }

            .game-area {
                height: 300px;
            }

            .buttons {
                flex-direction: column;
                align-items: center;
            }

            button {
                width: 100%;
                max-width: 250px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Collector</h1>
            <p class="subtitle">Move the blue circle with your mouse/touch to collect cheese. Get as much as you can before time runs out!</p>
        </header>

        <div class="game-info">
            <div class="info-box">
                <div class="info-label">SCORE</div>
                <div id="score" class="info-value">0</div>
            </div>
            <div class="info-box">
                <div class="info-label">TIME LEFT</div>
                <div id="timer" class="info-value">60</div>
            </div>
            <div class="info-box">
                <div class="info-label">CHEESE LEFT</div>
                <div id="cheese-count" class="info-value">10</div>
            </div>
        </div>

        <div class="game-area" id="game-area">
            <div id="player"></div>
            <!-- Cheese objects will be generated here -->
        </div>

        <div class="controls">
            <div class="buttons">
                <button id="start-btn">Start Game</button>
                <button id="restart-btn">Restart Round</button>
                <button id="reset-btn">Reset Game</button>
            </div>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li>Move your mouse or touch inside the game area to control the blue circle.</li>
                <li>Collect yellow cheese pieces to increase your score.</li>
                <li>Each cheese gives you 10 points.</li>
                <li>You have 60 seconds to collect as much cheese as possible.</li>
                <li>When all cheese is collected, a new batch will spawn.</li>
                <li>Try to beat your high score!</li>
            </ul>
        </div>
    </div>

    <div class="game-message" id="game-message">
        <h2 id="message-title">Game Over</h2>
        <p id="message-text">Your final score: <span id="final-score">0</span></p>
        <button class="message-btn" id="message-btn">Play Again</button>
    </div>

    <script>
        // Game state
        const gameState = {
            score: 0,
            timeLeft: 60,
            cheeseCount: 10,
            gameActive: false,
            gameLoopId: null,
            timerId: null,
            player: null,
            gameArea: null,
            cheeses: [],
            highScore: localStorage.getItem('cheeseHighScore') || 0,
            playerSpeed: 5
        };

        // DOM elements
        const scoreElement = document.getElementById('score');
        const timerElement = document.getElementById('timer');
        const cheeseCountElement = document.getElementById('cheese-count');
        const gameArea = document.getElementById('game-area');
        const player = document.getElementById('player');
        const startBtn = document.getElementById('start-btn');
        const restartBtn = document.getElementById('restart-btn');
        const resetBtn = document.getElementById('reset-btn');
        const gameMessage = document.getElementById('game-message');
        const messageTitle = document.getElementById('message-title');
        const messageText = document.getElementById('message-text');
        const finalScoreElement = document.getElementById('final-score');
        const messageBtn = document.getElementById('message-btn');

        // Initialize game
        function initGame() {
            gameState.player = player;
            gameState.gameArea = gameArea;
            
            // Position player in center
            const areaRect = gameArea.getBoundingClientRect();
            player.style.left = (areaRect.width / 2 - 20) + 'px';
            player.style.top = (areaRect.height / 2 - 20) + 'px';
            
            // Create initial cheese
            spawnCheese(gameState.cheeseCount);
            
            // Update UI
            updateUI();
            
            // Set up event listeners
            setupEventListeners();
        }

        // Spawn cheese objects
        function spawnCheese(count) {
            // Clear existing cheese
            gameState.cheeses.forEach(cheese => cheese.remove());
            gameState.cheeses = [];
            
            const areaRect = gameArea.getBoundingClientRect();
            
            for (let i = 0; i < count; i++) {
                const cheese = document.createElement('div');
                cheese.className = 'cheese';
                
                // Random position within game area (avoid edges)
                const x = Math.random() * (areaRect.width - 40) + 20;
                const y = Math.random() * (areaRect.height - 40) + 20;
                
                cheese.style.left = x + 'px';
                cheese.style.top = y + 'px';
                
                gameArea.appendChild(cheese);
                gameState.cheeses.push(cheese);
            }
            
            gameState.cheeseCount = count;
            cheeseCountElement.textContent = count;
        }

        // Update UI elements
        function updateUI() {
            scoreElement.textContent = gameState.score;
            timerElement.textContent = gameState.timeLeft;
            cheeseCountElement.textContent = gameState.cheeseCount;
        }

        // Game loop
        function gameLoop() {
            if (!gameState.gameActive) return;
            
            // Check collisions
            checkCollisions();
            
            // Continue game loop
            gameState.gameLoopId = requestAnimationFrame(gameLoop);
        }

        // Check collisions between player and cheese
        function checkCollisions() {
            const playerRect = player.getBoundingClientRect();
            const areaRect = gameArea.getBoundingClientRect();
            
            gameState.cheeses = gameState.cheeses.filter(cheese => {
                const cheeseRect = cheese.getBoundingClientRect();
                
                // Calculate positions relative to game area
                const playerX = playerRect.left - areaRect.left + playerRect.width / 2;
                const playerY = playerRect.top - areaRect.top + playerRect.height / 2;
                const cheeseX = cheeseRect.left - areaRect.left + cheeseRect.width / 2;
                const cheeseY = cheeseRect.top - areaRect.top + cheeseRect.height / 2;
                
                // Check collision (distance between centers)
                const distance = Math.sqrt(
                    Math.pow(playerX - cheeseX, 2) + Math.pow(playerY - cheeseY, 2)
                );
                
                if (distance < 35) { // Collision detected
                    // Remove cheese
                    cheese.remove();
                    
                    // Update score
                    gameState.score += 10;
                    scoreElement.textContent = gameState.score;
                    
                    // Update cheese count
                    gameState.cheeseCount--;
                    cheeseCountElement.textContent = gameState.cheeseCount;
                    
                    // Spawn new cheese if all collected
                    if (gameState.cheeseCount === 0) {
                        spawnCheese(10);
                    }
                    
                    return false; // Remove from array
                }
                
                return true; // Keep in array
            });
        }

        // Start game
        function startGame() {
            if (gameState.gameActive) return;
            
            gameState.gameActive = true;
            gameState.timeLeft = 60;
            gameState.score = 0;
            
            // Spawn initial cheese
            spawnCheese(10);
            
            // Start game loop
            gameLoop();
            
            // Start timer
            gameState.timerId = setInterval(() => {
                gameState.timeLeft--;
                timerElement.textContent = gameState.timeLeft;
                
                if (gameState.timeLeft <= 0) {
                    endGame();
                }
            }, 1000);
            
            // Update UI
            updateUI();
            startBtn.disabled = true;
        }

        // End game
        function endGame() {
            gameState.gameActive = false;
            
            // Stop game loop
            cancelAnimationFrame(gameState.gameLoopId);
            clearInterval(gameState.timerId);
            
            // Update high score
            if (gameState.score > gameState.highScore) {
                gameState.highScore = gameState.score;
                localStorage.setItem('cheeseHighScore', gameState.highScore);
            }
            
            // Show game over message
            finalScoreElement.textContent = gameState.score;
            messageTitle.textContent = 'Game Over!';
            messageText.innerHTML = `Your final score: <strong>${gameState.score}</strong><br>High Score: ${gameState.highScore}`;
            gameMessage.style.display = 'flex';
            
            startBtn.disabled = false;
        }

        // Restart round
        function restartRound() {
            if (gameState.gameActive) {
                clearInterval(gameState.timerId);
                cancelAnimationFrame(gameState.gameLoopId);
            }
            
            gameState.gameActive = false;
            gameState.timeLeft = 60;
            gameState.score = 0;
            gameState.cheeseCount = 10;
            
            spawnCheese(10);
            updateUI();
            
            // Position player in center
            const areaRect = gameArea.getBoundingClientRect();
            player.style.left = (areaRect.width / 2 - 20) + 'px';
            player.style.top = (areaRect.height / 2 - 20) + 'px';
            
            gameMessage.style.display = 'none';
            startBtn.disabled = false;
        }

        // Reset game (full reset)
        function resetGame() {
            if (gameState.gameActive) {
                clearInterval(gameState.timerId);
                cancelAnimationFrame(gameState.gameLoopId);
            }
            
            gameState.gameActive = false;
            gameState.score = 0;
            gameState.timeLeft = 60;
            gameState.cheeseCount = 10;
            gameState.highScore = localStorage.getItem('cheeseHighScore') || 0;
            
            spawnCheese(10);
            updateUI();
            
            // Position player in center
            const areaRect = gameArea.getBoundingClientRect();
            player.style.left = (areaRect.width / 2 - 20) + 'px';
            player.style.top = (areaRect.height / 2 - 20) + 'px';
            
            gameMessage.style.display = 'none';
            startBtn.disabled = false;
        }

        // Set up event listeners
        function setupEventListeners() {
            // Mouse movement
            gameArea.addEventListener('mousemove', (e) => {
                if (!gameState.gameActive) return;
                
                const rect = gameArea.getBoundingClientRect();
                const x = e.clientX - rect.left - 20;
                const y = e.clientY - rect.top - 20;
                
                // Constrain within game area
                const maxX = rect.width - 40;
                const maxY = rect.height - 40