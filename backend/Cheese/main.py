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
            background-color: #F2F2F5;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        header {
            text-align: center;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #EAECF0;
        }

        h1 {
            font-size: clamp(2rem, 5vw, 2.5rem);
            color: #D4A017;
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
            gap: 2rem;
        }

        @media (min-width: 768px) {
            .game-area {
                grid-template-columns: 1fr 1fr;
            }
        }

        .game-info {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }

        .stat-box {
            background-color: #F9F9FB;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }

        .stat-label {
            font-size: 0.875rem;
            color: #666;
            margin-bottom: 0.25rem;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1A1A1A;
        }

        .controls {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .control-buttons {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }

        button {
            padding: 0.875rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            background-color: #EAECF0;
            color: #1A1A1A;
        }

        button:hover {
            background-color: #D4D4D8;
            transform: translateY(-1px);
        }

        button:active {
            transform: translateY(0);
        }

        button.primary {
            background-color: #D4A017;
            color: white;
        }

        button.primary:hover {
            background-color: #B8860B;
        }

        button.danger {
            background-color: #DC2626;
            color: white;
        }

        button.danger:hover {
            background-color: #B91C1C;
        }

        .game-canvas-container {
            position: relative;
            background-color: #FFFFFF;
            border-radius: 12px;
            overflow: hidden;
            aspect-ratio: 1;
            min-height: 300px;
        }

        #gameCanvas {
            width: 100%;
            height: 100%;
            display: block;
        }

        .instructions {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1rem;
        }

        .instructions h3 {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: #1A1A1A;
        }

        .instructions ul {
            list-style-position: inside;
            color: #666;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .instructions li {
            padding-left: 0.5rem;
        }

        .game-over {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.85);
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
            padding: 2rem;
            z-index: 10;
        }

        .game-over h2 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #D4A017;
        }

        .game-over p {
            font-size: 1.25rem;
            margin-bottom: 2rem;
            max-width: 400px;
        }

        .mobile-controls {
            display: none;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(2, 1fr);
            gap: 0.75rem;
            margin-top: 1rem;
            padding: 1rem;
            background-color: #F2F2F5;
            border-radius: 12px;
        }

        @media (max-width: 767px) {
            .mobile-controls {
                display: grid;
            }
            
            .container {
                padding: 1.5rem;
            }
            
            .game-info {
                padding: 1.25rem;
            }
        }

        .mobile-controls button {
            aspect-ratio: 1;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }

        .mobile-controls .up {
            grid-column: 2;
            grid-row: 1;
        }

        .mobile-controls .left {
            grid-column: 1;
            grid-row: 2;
        }

        .mobile-controls .right {
            grid-column: 3;
            grid-row: 2;
        }

        .mobile-controls .down {
            grid-column: 2;
            grid-row: 2;
        }

        .mobile-controls .action {
            grid-column: 1 / span 3;
            grid-row: 3;
            aspect-ratio: auto;
            height: 3rem;
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            color: #666;
            font-size: 0.875rem;
            padding-top: 1.5rem;
            border-top: 1px solid #EAECF0;
            width: 100%;
            max-width: 800px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Collector</h1>
            <p class="subtitle">Collect cheese while avoiding enemies! Use arrow keys or on-screen controls to move.</p>
        </header>

        <div class="game-area">
            <div class="game-info">
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-label">Score</div>
                        <div id="score" class="stat-value">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Cheese Collected</div>
                        <div id="cheeseCount" class="stat-value">0/10</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Lives</div>
                        <div id="lives" class="stat-value">3</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Enemies</div>
                        <div id="enemies" class="stat-value">3</div>
                    </div>
                </div>

                <div class="controls">
                    <div class="control-buttons">
                        <button id="startBtn" class="primary">Start Game</button>
                        <button id="pauseBtn">Pause</button>
                        <button id="restartBtn">Restart</button>
                        <button id="resetBtn" class="danger">Reset All</button>
                    </div>
                </div>
            </div>

            <div class="game-canvas-container">
                <canvas id="gameCanvas"></canvas>
                <div id="gameOverScreen" class="game-over">
                    <h2 id="gameOverTitle">Game Over</h2>
                    <p id="gameOverMessage">You collected all the cheese!</p>
                    <button id="playAgainBtn" class="primary" style="margin-top: 1rem;">Play Again</button>
                </div>
            </div>
        </div>

        <div class="mobile-controls">
            <button class="up" id="mobileUp">↑</button>
            <button class="left" id="mobileLeft">←</button>
            <button class="down" id="mobileDown">↓</button>
            <button class="right" id="mobileRight">→</button>
            <button class="action primary" id="mobileAction">Action</button>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li>Use <strong>Arrow Keys</strong> or <strong>On-Screen Controls</strong> to move the player</li>
                <li>Collect all <strong>10 cheese pieces</strong> to win</li>
                <li>Avoid the <strong>red enemies</strong> - they move randomly</li>
                <li>Each cheese gives <strong>10 points</strong></li>
                <li>You start with <strong>3 lives</strong> - lose one when hit by an enemy</li>
                <li>Game ends when you collect all cheese or lose all lives</li>
            </ul>
        </div>
    </div>

    <footer>
        <p>Cheese Collector Game • Use keyboard or touch controls • Refresh page to completely reset</p>
    </footer>

    <script>
        // Game state
        const gameState = {
            score: 0,
            cheeseCollected: 0,
            totalCheese: 10,
            lives: 3,
            maxLives: 3,
            enemies: 3,
            gameRunning: false,
            gamePaused: false,
            gameOver: false,
            player: { x: 50, y: 50, size: 20, speed: 5 },
            cheeses: [],
            enemies: [],
            keys: {},
            lastTime: 0
        };

        // DOM elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const livesElement = document.getElementById('lives');
        const enemiesElement = document.getElementById('enemies');
        const gameOverScreen = document.getElementById('gameOverScreen');
        const gameOverTitle = document.getElementById('gameOverTitle');
        const gameOverMessage = document.getElementById('gameOverMessage');

        // Initialize canvas size
        function initCanvas() {
            const container = canvas.parentElement;
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        }

        // Initialize game objects
        function initGame() {
            gameState.score = 0;
            gameState.cheeseCollected = 0;
            gameState.lives = gameState.maxLives;
            gameState.gameRunning = true;
            gameState.gamePaused = false;
            gameState.gameOver = false;
            gameState.player.x = canvas.width / 2;
            gameState.player.y = canvas.height / 2;
            
            // Generate cheeses
            gameState.cheeses = [];
            for (let i = 0; i < gameState.totalCheese; i++) {
                gameState.cheeses.push({
                    x: Math.random() * (canvas.width - 30) + 15,
                    y: Math.random() * (canvas.height - 30) + 15,
                    size: 15,
                    collected: false
                });
            }
            
            // Generate enemies
            gameState.enemies = [];
            for (let i = 0; i < gameState.enemies; i++) {
                gameState.enemies.push({
                    x: Math.random() * (canvas.width - 40) + 20,
                    y: Math.random() * (canvas.height - 40) + 20,
                    size: 25,
                    speed: 2 + Math.random() * 2,
                    dx: (Math.random() - 0.5) * 4,
                    dy: (Math.random() - 0.5) * 4
                });
            }
            
            updateUI();
            gameOverScreen.style.display = 'none';
        }

        // Update UI elements
        function updateUI() {
            scoreElement.textContent = gameState.score;
            cheeseCountElement.textContent = `${gameState.cheeseCollected}/${gameState.totalCheese}`;
            livesElement.textContent = gameState.lives;
            enemiesElement.textContent = gameState.enemies;
        }

        // Draw game objects
        function draw() {
            // Clear canvas
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw cheeses
            gameState.cheeses.forEach(cheese => {
                if (!cheese.collected) {
                    ctx.fillStyle = '#FFD700';
                    ctx.beginPath();
                    ctx.arc(cheese.x, cheese.y, cheese.size / 2, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Cheese holes
                    ctx.fillStyle = '#D4A017';
                    ctx.beginPath();
                    ctx.arc(cheese.x - 4, cheese.y - 4, 3, 0, Math.PI * 2);
                    ctx.arc(cheese.x + 5, cheese.y + 3, 2, 0, Math.PI * 2);
                    ctx.arc(cheese.x + 2, cheese.y - 5, 2.5, 0, Math.PI * 2);
                    ctx.fill();
                }
            });
            
            // Draw player
            ctx.fillStyle = '#4A90E2';
            ctx.beginPath();
            ctx.arc(gameState.player.x, gameState.player.y, gameState.player.size / 2, 0, Math.PI * 2);
            ctx.fill();
            
            // Player eyes
            ctx.fillStyle = '#FFFFFF';
            ctx.beginPath();
            ctx.arc(gameState.player.x - 4, gameState.player.y - 4, 3, 0, Math.PI * 2);
            ctx.arc(gameState.player.x + 4, gameState.player.y - 4, 3, 0, Math.PI * 2);
            ctx.fill();
            
            // Draw enemies
            gameState.enemies.forEach(enemy => {
                ctx.fillStyle = '#DC2626';
                ctx.beginPath();
                ctx.arc(enemy.x, enemy.y, enemy.size / 2, 0, Math.PI * 2);
                ctx.fill();
                
                // Enemy eyes
                ctx.fillStyle = '#FFFFFF';
                ctx.beginPath();
                ctx.arc(enemy.x - 5, enemy.y - 5, 4, 0, Math.PI * 2);
                ctx.arc(enemy.x + 5, enemy.y - 5, 4, 0, Math.PI * 2);
                ctx.fill();
                
                ctx.fillStyle = '#000000';
                ctx.beginPath();
                ctx.arc(enemy.x - 5, enemy.y - 5, 2, 0, Math.PI * 2);
                ctx.arc(enemy.x + 5, enemy.y - 5, 2, 0, Math.PI * 2);
                ctx.fill();
            });
            
            // Draw game status
            if (gameState.gamePaused) {
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                ctx.fillStyle = '#FFFFFF';
                ctx.font = 'bold 48px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2);
            }
        }

        // Update game logic
        function update(deltaTime) {
            if (!gameState.gameRunning || gameState.gamePaused || gameState.gameOver) return;
            
            // Move player based on keys
            if (gameState.keys['ArrowUp'] || gameState.keys['KeyW'] || gameState.keys['up']) {
                gameState.player.y -= gameState.player.speed;
            }
            if (gameState.keys['ArrowDown'] || gameState.keys['KeyS'] || gameState.keys['down']) {
                gameState.player.y += gameState.player.speed;
            }
            if (gameState.keys['ArrowLeft'] || gameState.keys['KeyA'] || gameState.keys['left']) {
                gameState.player.x -= gameState.player.speed;
            }
            if (gameState.keys['ArrowRight'] || gameState.keys['KeyD'] || gameState.keys['right']) {
                gameState.player.x += gameState.player.speed;
            }
            
            // Keep player in bounds
            gameState.player.x = Math.max(gameState.player.size / 2, 
                Math.min(canvas.width - gameState.player.size / 2, gameState.player.x));
            gameState.player.y = Math