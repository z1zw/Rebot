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
            background: #F9F9FB;
            color: #1A1A1A;
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
            background: #F2F2F5;
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            text-align: center;
            padding-bottom: 1rem;
            border-bottom: 1px solid #EAECF0;
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
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            background: #FFFFFF;
            padding: 1.2rem;
            border-radius: 0.75rem;
            border: 1px solid #EAECF0;
        }

        .stat-box {
            text-align: center;
            padding: 0.8rem;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.3rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #1A1A1A;
        }

        .level-indicator {
            font-size: 1.1rem;
            color: #D4A017;
            font-weight: 600;
        }

        .game-area {
            position: relative;
            width: 100%;
            height: 400px;
            background: #FFFFFF;
            border-radius: 0.75rem;
            border: 2px solid #EAECF0;
            overflow: hidden;
            touch-action: none;
            user-select: none;
        }

        #player {
            position: absolute;
            width: 50px;
            height: 50px;
            background: #4A6FA5;
            border-radius: 50%;
            transition: transform 0.1s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .cheese {
            position: absolute;
            width: 40px;
            height: 40px;
            background: #FFD700;
            border-radius: 50% 50% 50% 0;
            transform: rotate(45deg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: #8B6914;
            cursor: pointer;
            animation: pulse 1.5s infinite;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .enemy {
            position: absolute;
            width: 45px;
            height: 45px;
            background: #DC143C;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        @keyframes pulse {
            0% { transform: rotate(45deg) scale(1); }
            50% { transform: rotate(45deg) scale(1.1); }
            100% { transform: rotate(45deg) scale(1); }
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
            padding: 1rem;
            background: #FFFFFF;
            border-radius: 0.75rem;
            border: 1px solid #EAECF0;
        }

        button {
            padding: 0.8rem 1.5rem;
            font-size: 1rem;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }

        #startBtn {
            background: #4CAF50;
            color: white;
        }

        #startBtn:hover {
            background: #45a049;
        }

        #restartBtn {
            background: #FF9800;
            color: white;
        }

        #restartBtn:hover {
            background: #F57C00;
        }

        #resetScoreBtn {
            background: #9E9E9E;
            color: white;
        }

        #resetScoreBtn:hover {
            background: #757575;
        }

        .instructions {
            background: #FFFFFF;
            padding: 1.2rem;
            border-radius: 0.75rem;
            border: 1px solid #EAECF0;
            font-size: 0.95rem;
            color: #555;
        }

        .instructions h3 {
            margin-bottom: 0.5rem;
            color: #1A1A1A;
        }

        .instructions ul {
            padding-left: 1.2rem;
        }

        .instructions li {
            margin-bottom: 0.3rem;
        }

        .game-message {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 2rem 3rem;
            border-radius: 1rem;
            text-align: center;
            font-size: 1.8rem;
            font-weight: bold;
            z-index: 100;
            display: none;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }

        @media (max-width: 600px) {
            .container {
                padding: 1rem;
            }
            .game-area {
                height: 300px;
            }
            .stat-value {
                font-size: 1.7rem;
            }
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            button {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Collector</h1>
            <p class="subtitle">Collect cheese, avoid red enemies, and level up! Use mouse/touch to move the blue player.</p>
        </header>

        <div class="game-info">
            <div class="stat-box">
                <div class="stat-label">Score</div>
                <div id="score" class="stat-value">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Level</div>
                <div id="level" class="stat-value">1</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Cheese Collected</div>
                <div id="cheeseCount" class="stat-value">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">High Score</div>
                <div id="highScore" class="stat-value">0</div>
            </div>
        </div>

        <div class="game-area" id="gameArea">
            <div id="player">😊</div>
            <div class="game-message" id="gameMessage"></div>
        </div>

        <div class="controls">
            <button id="startBtn">Start Game</button>
            <button id="restartBtn">Restart Level</button>
            <button id="resetScoreBtn">Reset High Score</button>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li>Move the blue circle with your mouse or touch inside the game area.</li>
                <li>Collect yellow cheese pieces to increase your score.</li>
                <li>Avoid red enemies - touching one ends the game.</li>
                <li>Each level requires more cheese to complete and adds more enemies.</li>
                <li>Level up by collecting all cheese in the level.</li>
                <li>Your high score is saved between sessions.</li>
            </ul>
        </div>
    </div>

    <script>
        // Game state
        const gameState = {
            score: 0,
            level: 1,
            cheeseCollected: 0,
            cheeseRequired: 5,
            highScore: localStorage.getItem('cheeseHighScore') || 0,
            gameRunning: false,
            gameOver: false,
            player: null,
            gameArea: null,
            cheeses: [],
            enemies: [],
            animationId: null,
            playerSpeed: 5
        };

        // DOM elements
        const scoreEl = document.getElementById('score');
        const levelEl = document.getElementById('level');
        const cheeseCountEl = document.getElementById('cheeseCount');
        const highScoreEl = document.getElementById('highScore');
        const gameArea = document.getElementById('gameArea');
        const player = document.getElementById('player');
        const gameMessage = document.getElementById('gameMessage');
        const startBtn = document.getElementById('startBtn');
        const restartBtn = document.getElementById('restartBtn');
        const resetScoreBtn = document.getElementById('resetScoreBtn');

        // Initialize display
        function updateDisplay() {
            scoreEl.textContent = gameState.score;
            levelEl.textContent = gameState.level;
            cheeseCountEl.textContent = gameState.cheeseCollected;
            highScoreEl.textContent = gameState.highScore;
        }

        // Initialize game
        function initGame() {
            gameState.player = player;
            gameState.gameArea = gameArea;
            gameState.cheeses = [];
            gameState.enemies = [];
            gameState.cheeseCollected = 0;
            gameState.cheeseRequired = 5 + (gameState.level - 1) * 3;
            gameState.gameOver = false;
            gameMessage.style.display = 'none';

            // Position player
            player.style.left = '50%';
            player.style.top = '50%';

            // Create cheeses
            for (let i = 0; i < gameState.cheeseRequired; i++) {
                createCheese();
            }

            // Create enemies based on level
            const enemyCount = Math.min(gameState.level + 1, 8);
            for (let i = 0; i < enemyCount; i++) {
                createEnemy();
            }

            updateDisplay();
        }

        // Create a cheese at random position
        function createCheese() {
            const cheese = document.createElement('div');
            cheese.className = 'cheese';
            cheese.textContent = '🧀';
            const areaRect = gameArea.getBoundingClientRect();
            const x = Math.random() * (areaRect.width - 50);
            const y = Math.random() * (areaRect.height - 50);
            cheese.style.left = x + 'px';
            cheese.style.top = y + 'px';
            gameArea.appendChild(cheese);
            gameState.cheeses.push(cheese);
        }

        // Create an enemy at random position
        function createEnemy() {
            const enemy = document.createElement('div');
            enemy.className = 'enemy';
            enemy.textContent = '👾';
            const areaRect = gameArea.getBoundingClientRect();
            const x = Math.random() * (areaRect.width - 50);
            const y = Math.random() * (areaRect.height - 50);
            enemy.style.left = x + 'px';
            enemy.style.top = y + 'px';
            gameArea.appendChild(enemy);
            gameState.enemies.push(enemy);
        }

        // Move player with mouse/touch
        gameArea.addEventListener('mousemove', (e) => {
            if (!gameState.gameRunning || gameState.gameOver) return;
            const rect = gameArea.getBoundingClientRect();
            let x = e.clientX - rect.left - player.offsetWidth / 2;
            let y = e.clientY - rect.top - player.offsetHeight / 2;
            x = Math.max(0, Math.min(x, rect.width - player.offsetWidth));
            y = Math.max(0, Math.min(y, rect.height - player.offsetHeight));
            player.style.left = x + 'px';
            player.style.top = y + 'px';
        });

        gameArea.addEventListener('touchmove', (e) => {
            if (!gameState.gameRunning || gameState.gameOver) return;
            e.preventDefault();
            const touch = e.touches[0];
            const rect = gameArea.getBoundingClientRect();
            let x = touch.clientX - rect.left - player.offsetWidth / 2;
            let y = touch.clientY - rect.top - player.offsetHeight / 2;
            x = Math.max(0, Math.min(x, rect.width - player.offsetWidth));
            y = Math.max(0, Math.min(y, rect.height - player.offsetHeight));
            player.style.left = x + 'px';
            player.style.top = y + 'px';
        }, { passive: false });

        // Check collisions
        function checkCollisions() {
            const playerRect = player.getBoundingClientRect();

            // Check cheese collection
            gameState.cheeses.forEach((cheese, index) => {
                const cheeseRect = cheese.getBoundingClientRect();
                if (rectsOverlap(playerRect, cheeseRect)) {
                    cheese.remove();
                    gameState.cheeses.splice(index, 1);
                    gameState.score += 10 * gameState.level;
                    gameState.cheeseCollected++;
                    updateDisplay();
                    if (gameState.cheeseCollected >= gameState.cheeseRequired) {
                        levelUp();
                    }
                }
            });

            // Check enemy collision
            for (const enemy of gameState.enemies) {
                const enemyRect = enemy.getBoundingClientRect();
                if (rectsOverlap(playerRect, enemyRect)) {
                    gameOver(false);
                    return;
                }
            }
        }

        // Helper: rectangle overlap
        function rectsOverlap(rect1, rect2) {
            return !(rect1.right < rect2.left ||
                     rect1.left > rect2.right ||
                     rect1.bottom < rect2.top ||
                     rect1.top > rect2.bottom);
        }

        // Level up
        function levelUp() {
            gameState.level++;
            gameState.score += 100 * (gameState.level - 1);
            gameMessage.textContent = `🎉 Level ${gameState.level}!`;
            gameMessage.style.display = 'block';
            gameState.gameRunning = false;
            setTimeout(() => {
                gameMessage.style.display = 'none';
                initGame();
                startGame();
            }, 1500);
        }

        // Game over
        function gameOver(win) {
            gameState.gameOver = true;
            gameState.gameRunning = false;
            if (gameState.animationId) {
                cancelAnimationFrame(gameState.animationId);
            }
            if (win) {
                gameMessage.textContent = '🏆 You Win!';
            } else {
                gameMessage.textContent = '💥 Game Over';
            }
            gameMessage.style.display = 'block';

            // Update high score
            if (gameState.score > gameState.highScore) {
                gameState.highScore = gameState.score;
                localStorage.setItem('cheeseHighScore', gameState.highScore);
                updateDisplay();
            }
        }

        // Game loop
        function gameLoop() {
            if (!gameState.gameRunning || gameState.gameOver) return;
            checkCollisions();
            moveEnemies();
            gameState.animationId = requestAnimationFrame(gameLoop);
        }

        // Move enemies
        function moveEnemies() {
            const areaRect = gameArea.getBoundingClientRect();
            gameState.enemies.forEach(enemy => {
                let dx = (Math.random() - 0.5) * 4;
                let dy = (Math.random() - 0.5) * 4;
                let x = parseFloat(enemy.style.left) + dx;
                let y = parseFloat(enemy.style.top) + dy;
                x = Math.max(0, Math.min(x, areaRect.width - enemy.offsetWidth));
                y = Math.max(0, Math.min(y, areaRect.height - enemy.offsetHeight));
                enemy.style.left = x + 'px';
                enemy.style.top = y + 'px';
            });
        }

        // Start game
        function startGame() {
            if (gameState.gameRunning) return;
            gameState.gameRunning = true;
            gameState.gameOver = false;
            gameLoop();
        }

        // Restart level
        function restartLevel() {
            if (gameState.animationId) {
                cancelAnimationFrame(gameState.animationId);
            }
            initGame();
            startGame();
        }

        // Reset high score
        function resetHighScore() {
            gameState.highScore = 0;
            localStorage.setItem('cheeseHighScore', 0);
            updateDisplay();
        }

        // Event listeners
        startBtn.addEventListener('click', () => {
            if (!gameState.gameRunning) {
                startGame();
            }
        });

        restartBtn.addEventListener('