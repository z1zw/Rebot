<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheese Game</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }

        body {
            background-color: #F9F9FB;
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1.5rem;
            line-height: 1.5;
        }

        .container {
            width: 100%;
            max-width: 800px;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            text-align: center;
            padding: 1.5rem;
            background: #F2F2F5;
            border-radius: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            color: #5D4037;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            font-size: 1rem;
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }

        .game-area {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        @media (min-width: 768px) {
            .game-area {
                grid-template-columns: 1fr 1fr;
            }
        }

        .panel {
            background: #FFFFFF;
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        .stats-panel {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #EAECF0;
        }

        .stat-label {
            font-weight: 600;
            color: #555;
        }

        .stat-value {
            font-weight: 700;
            color: #5D4037;
        }

        #score {
            font-size: 1.8rem;
        }

        #lives {
            color: #D32F2F;
        }

        #level {
            color: #388E3C;
        }

        .controls-panel {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .control-buttons {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            margin-top: 0.5rem;
        }

        button {
            padding: 0.875rem 1.25rem;
            border: none;
            border-radius: 0.75rem;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #5D4037;
            color: white;
        }

        button:hover {
            background: #4E342E;
            transform: translateY(-2px);
        }

        button:active {
            transform: translateY(0);
        }

        button#restartBtn {
            background: #388E3C;
        }

        button#restartBtn:hover {
            background: #2E7D32;
        }

        button#pauseBtn {
            background: #0288D1;
        }

        button#pauseBtn:hover {
            background: #0277BD;
        }

        .instructions {
            background: #F2F2F5;
            padding: 1.5rem;
            border-radius: 1rem;
            margin-top: 1rem;
        }

        .instructions h3 {
            margin-bottom: 0.75rem;
            color: #5D4037;
        }

        .instructions ul {
            padding-left: 1.25rem;
            color: #555;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .game-canvas-container {
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1;
            background: #1A237E;
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }

        canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        .game-over {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.85);
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
            padding: 2rem;
            border-radius: 1rem;
        }

        .game-over h2 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #FF9800;
        }

        .game-over p {
            font-size: 1.2rem;
            margin-bottom: 1.5rem;
            max-width: 400px;
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            color: #777;
            font-size: 0.9rem;
            padding: 1rem;
        }

        @media (max-width: 480px) {
            .container {
                padding: 0.75rem;
            }
            
            .panel {
                padding: 1rem;
            }
            
            .control-buttons {
                grid-template-columns: 1fr;
            }
            
            button {
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Game</h1>
            <p class="subtitle">Collect cheese, avoid enemies, and survive as long as possible!</p>
        </header>

        <div class="game-area">
            <div class="panel stats-panel">
                <h2>Game Stats</h2>
                <div class="stat-row">
                    <span class="stat-label">Score:</span>
                    <span id="score" class="stat-value">0</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Lives:</span>
                    <span id="lives" class="stat-value">3</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Level:</span>
                    <span id="level" class="stat-value">1</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Cheese Collected:</span>
                    <span id="cheeseCount" class="stat-value">0</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Enemies:</span>
                    <span id="enemyCount" class="stat-value">3</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Status:</span>
                    <span id="status" class="stat-value">Playing</span>
                </div>
            </div>

            <div class="panel controls-panel">
                <h2>Controls</h2>
                <p>Use arrow keys or WASD to move. Collect cheese (🧀) and avoid enemies (👾).</p>
                <div class="control-buttons">
                    <button id="startBtn">Start Game</button>
                    <button id="pauseBtn">Pause</button>
                    <button id="restartBtn">Restart</button>
                    <button id="helpBtn">How to Play</button>
                </div>
            </div>
        </div>

        <div class="game-canvas-container">
            <canvas id="gameCanvas"></canvas>
            <div id="gameOverScreen" class="game-over">
                <h2>Game Over!</h2>
                <p id="gameOverMessage">You collected <span id="finalCheese">0</span> cheese with a score of <span id="finalScore">0</span>.</p>
                <button id="playAgainBtn">Play Again</button>
            </div>
        </div>

        <div class="instructions" id="instructionsPanel" style="display: none;">
            <h3>How to Play</h3>
            <ul>
                <li><strong>Move:</strong> Use Arrow Keys or WASD to control the player (😊)</li>
                <li><strong>Goal:</strong> Collect as much cheese (🧀) as possible</li>
                <li><strong>Avoid:</strong> Don't touch the enemies (👾) or you lose a life</li>
                <li><strong>Levels:</strong> Every 10 cheese increases the level and adds more enemies</li>
                <li><strong>Win:</strong> Survive and collect cheese to get the highest score!</li>
                <li><strong>Lose:</strong> Game ends when you run out of lives (3 total)</li>
            </ul>
            <p style="margin-top: 1rem; font-style: italic;">Press any key or click "Start Game" to begin!</p>
        </div>

        <footer>
            <p>Cheese Game v1.0 • Collect all the cheese! • Made with 🧀</p>
        </footer>
    </div>

    <script>
        // Game state
        const gameState = {
            score: 0,
            lives: 3,
            level: 1,
            cheeseCollected: 0,
            enemies: 3,
            isRunning: false,
            isPaused: false,
            gameOver: false,
            player: { x: 400, y: 300, size: 30, speed: 5 },
            cheeses: [],
            enemies: [],
            keys: {},
            lastTime: 0,
            spawnTimer: 0,
            enemySpawnTimer: 0
        };

        // DOM elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const livesElement = document.getElementById('lives');
        const levelElement = document.getElementById('level');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const enemyCountElement = document.getElementById('enemyCount');
        const statusElement = document.getElementById('status');
        const gameOverScreen = document.getElementById('gameOverScreen');
        const finalCheeseElement = document.getElementById('finalCheese');
        const finalScoreElement = document.getElementById('finalScore');
        const gameOverMessage = document.getElementById('gameOverMessage');
        const instructionsPanel = document.getElementById('instructionsPanel');

        // Initialize canvas
        function initCanvas() {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }

        // Initialize game objects
        function initGame() {
            gameState.cheeses = [];
            gameState.enemies = [];
            gameState.player.x = canvas.width / 2;
            gameState.player.y = canvas.height / 2;
            
            // Create initial cheeses
            for (let i = 0; i < 5; i++) {
                spawnCheese();
            }
            
            // Create initial enemies
            for (let i = 0; i < gameState.enemies; i++) {
                spawnEnemy();
            }
        }

        // Spawn a cheese at random position
        function spawnCheese() {
            gameState.cheeses.push({
                x: Math.random() * (canvas.width - 40) + 20,
                y: Math.random() * (canvas.height - 40) + 20,
                size: 25,
                value: 10
            });
        }

        // Spawn an enemy at random position
        function spawnEnemy() {
            const side = Math.floor(Math.random() * 4);
            let x, y;
            
            switch(side) {
                case 0: // top
                    x = Math.random() * canvas.width;
                    y = -30;
                    break;
                case 1: // right
                    x = canvas.width + 30;
                    y = Math.random() * canvas.height;
                    break;
                case 2: // bottom
                    x = Math.random() * canvas.width;
                    y = canvas.height + 30;
                    break;
                case 3: // left
                    x = -30;
                    y = Math.random() * canvas.height;
                    break;
            }
            
            gameState.enemies.push({
                x: x,
                y: y,
                size: 35,
                speed: 1 + (gameState.level * 0.2),
                angle: Math.random() * Math.PI * 2
            });
        }

        // Update game state
        function update(deltaTime) {
            if (!gameState.isRunning || gameState.isPaused || gameState.gameOver) return;

            // Move player based on keys
            if (gameState.keys['ArrowUp'] || gameState.keys['w'] || gameState.keys['W']) {
                gameState.player.y -= gameState.player.speed;
            }
            if (gameState.keys['ArrowDown'] || gameState.keys['s'] || gameState.keys['S']) {
                gameState.player.y += gameState.player.speed;
            }
            if (gameState.keys['ArrowLeft'] || gameState.keys['a'] || gameState.keys['A']) {
                gameState.player.x -= gameState.player.speed;
            }
            if (gameState.keys['ArrowRight'] || gameState.keys['d'] || gameState.keys['D']) {
                gameState.player.x += gameState.player.speed;
            }

            // Keep player in bounds
            gameState.player.x = Math.max(gameState.player.size/2, Math.min(canvas.width - gameState.player.size/2, gameState.player.x));
            gameState.player.y = Math.max(gameState.player.size/2, Math.min(canvas.height - gameState.player.size/2, gameState.player.y));

            // Update enemies
            gameState.enemies.forEach(enemy => {
                // Move toward player
                const dx = gameState.player.x - enemy.x;
                const dy = gameState.player.y - enemy.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance > 0) {
                    enemy.x += (dx / distance) * enemy.speed;
                    enemy.y += (dy / distance) * enemy.speed;
                }

                // Check collision with player
                const playerDx = gameState.player.x - enemy.x;
                const playerDy = gameState.player.y - enemy.y;
                const playerDistance = Math.sqrt(playerDx * playerDx + playerDy * playerDy);
                
                if (playerDistance < (gameState.player.size/2 + enemy.size/2)) {
                    gameState.lives--;
                    updateUI();
                    
                    // Respawn enemy
                    enemy.x = Math.random() * canvas.width;
                    enemy.y = Math.random() * canvas.height;
                    
                    if (gameState.lives <= 0) {
                        endGame(false);
                    }
                }
            });

            // Check cheese collection
            for (let i = gameState.cheeses.length - 1; i >= 0; i--) {
                const cheese = gameState.cheeses[i];
                const dx = gameState.player.x - cheese.x;
                const dy = gameState.player.y - cheese.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < (gameState.player.size/2 + cheese.size/2)) {
                    // Collect cheese
                    gameState.score += cheese.value;
                    gameState.cheeseCollected++;
                    gameState.cheeses.splice(i, 1);
                    
                    // Level up every 10 cheese
                    if (gameState.cheeseCollected % 10 === 0) {
                        gameState.level++;
                        gameState.enemies++;
                        spawnEnemy();
                    }
                    
                    updateUI();
                    spawnCheese(); // Spawn new cheese to replace collected one
                }
            }

            // Spawn new enemies periodically
            gameState.enemySpawnTimer += deltaTime;
            if (gameState.enemySpawnTimer > 5000) { // Every 5 seconds
                spawnEnemy();
                gameState.enemySpawnTimer = 0;
            }

            // Spawn extra cheese periodically
            gameState.spawnTimer += deltaTime;
            if (gameState.spawnTimer > 3000 && gameState.cheeses.length < 10) { // Every 3 seconds, max 10 cheese
                spawnCheese();
                gameState.spawnTimer = 0;
            }
        }

        // Draw everything
        function draw() {
            // Clear canvas
            ctx.fillStyle = '#1A237E';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw cheeses
            gameState.cheeses.forEach(cheese => {
                ctx.fillStyle = '#FFD700';
                ctx.beginPath();
                ctx.arc(cheese.x, cheese.y, cheese.size/2, 0, Math.PI * 2);
                ctx.fill();
                
                // Cheese holes
                ctx.fillStyle = '#FFA000';
                ctx.beginPath();
                ctx.arc(cheese.x - 5, cheese.y - 3, 3, 0, Math.PI * 2);
                ctx.arc(cheese.x + 6, cheese.y + 2, 4, 0, Math.PI * 2);
                ctx.arc(cheese.x - 2, cheese.y + 6, 3, 0, Math.PI * 2);
                ctx.fill();
                
                // Cheese label
                ctx.fillStyle = 'white';
                ctx.font = '16px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('🧀', cheese.x, cheese.y + 5);