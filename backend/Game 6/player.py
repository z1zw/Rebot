<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheese Game - Player Implementation</title>
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
            line-height: 1.6;
            padding: 1rem;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            max-width: 1000px;
            width: 100%;
            margin: 0 auto;
            padding: 1.5rem;
            background-color: #F2F2F5;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #EAECF0;
        }

        h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            color: #2D3748;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            font-size: 1rem;
            color: #718096;
            max-width: 600px;
            margin: 0 auto;
        }

        .game-area {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        @media (min-width: 768px) {
            .game-area {
                grid-template-columns: 1fr 1fr;
            }
        }

        .canvas-container {
            background-color: #FFFFFF;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        #gameCanvas {
            background-color: #F8FAFC;
            border: 2px solid #E2E8F0;
            border-radius: 6px;
            display: block;
            width: 100%;
            max-width: 400px;
            height: 400px;
            touch-action: none;
        }

        .controls {
            background-color: #FFFFFF;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .control-group {
            margin-bottom: 1.5rem;
        }

        h2 {
            font-size: 1.25rem;
            color: #2D3748;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #EAECF0;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .stat-item {
            background-color: #EDF2F7;
            padding: 0.75rem;
            border-radius: 6px;
            text-align: center;
        }

        .stat-label {
            font-size: 0.875rem;
            color: #718096;
            margin-bottom: 0.25rem;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2D3748;
        }

        .buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }

        button {
            padding: 0.75rem 1.25rem;
            background-color: #4299E1;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            flex: 1;
            min-width: 120px;
        }

        button:hover {
            background-color: #3182CE;
            transform: translateY(-1px);
        }

        button:active {
            transform: translateY(0);
        }

        button.reset {
            background-color: #F56565;
        }

        button.reset:hover {
            background-color: #E53E3E;
        }

        button.movement {
            background-color: #48BB78;
        }

        button.movement:hover {
            background-color: #38A169;
        }

        .instructions {
            background-color: #FFFFFF;
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .instructions h2 {
            margin-top: 0;
        }

        .instructions ul {
            padding-left: 1.5rem;
            margin-bottom: 1rem;
        }

        .instructions li {
            margin-bottom: 0.5rem;
            color: #4A5568;
        }

        .key-hint {
            display: inline-block;
            background-color: #EDF2F7;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.875rem;
            margin: 0 0.25rem;
        }

        .mobile-controls {
            display: none;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-top: 1rem;
            width: 100%;
            max-width: 300px;
        }

        @media (max-width: 767px) {
            .mobile-controls {
                display: grid;
            }
            
            .buttons {
                flex-direction: column;
            }
            
            button {
                width: 100%;
            }
        }

        .game-status {
            text-align: center;
            padding: 1rem;
            margin-top: 1rem;
            border-radius: 6px;
            font-weight: 500;
        }

        .game-status.playing {
            background-color: #C6F6D5;
            color: #22543D;
        }

        .game-status.won {
            background-color: #BEE3F8;
            color: #2C5282;
        }

        .game-status.lost {
            background-color: #FED7D7;
            color: #742A2A;
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            color: #718096;
            font-size: 0.875rem;
            padding-top: 1rem;
            border-top: 1px solid #EAECF0;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Cheese Game - Player Implementation</h1>
            <p class="subtitle">Control the mouse character to collect cheese while avoiding obstacles. Complete player movement, collision detection, and state management.</p>
        </header>

        <div class="game-area">
            <div class="canvas-container">
                <canvas id="gameCanvas" width="400" height="400"></canvas>
                <div class="mobile-controls">
                    <button class="movement" data-direction="up">↑ Up</button>
                    <button class="movement" data-direction="left">← Left</button>
                    <button class="movement" data-direction="down">↓ Down</button>
                    <button class="movement" data-direction="right">→ Right</button>
                </div>
            </div>

            <div class="controls">
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-label">Score</div>
                        <div id="scoreValue" class="stat-value">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Cheese</div>
                        <div id="cheeseCount" class="stat-value">0/5</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Lives</div>
                        <div id="livesValue" class="stat-value">3</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Position</div>
                        <div id="positionValue" class="stat-value">0,0</div>
                    </div>
                </div>

                <div class="control-group">
                    <h2>Game Controls</h2>
                    <div class="buttons">
                        <button id="startBtn">Start Game</button>
                        <button id="pauseBtn">Pause</button>
                        <button id="resetBtn" class="reset">Reset Game</button>
                    </div>
                </div>

                <div class="control-group">
                    <h2>Movement Controls</h2>
                    <div class="buttons">
                        <button class="movement" data-direction="up">Move Up</button>
                        <button class="movement" data-direction="left">Move Left</button>
                        <button class="movement" data-direction="down">Move Down</button>
                        <button class="movement" data-direction="right">Move Right</button>
                    </div>
                </div>

                <div id="gameStatus" class="game-status playing">
                    Game Ready - Press Start!
                </div>
            </div>
        </div>

        <div class="instructions">
            <h2>How to Play</h2>
            <ul>
                <li>Use <span class="key-hint">WASD</span> or <span class="key-hint">Arrow Keys</span> to move the mouse character</li>
                <li>Collect all 5 cheese pieces to win the game</li>
                <li>Avoid the red obstacles - they reduce your lives</li>
                <li>Each cheese collected gives you 100 points</li>
                <li>You start with 3 lives - game ends when lives reach 0</li>
                <li>On mobile, use the directional buttons below the game area</li>
            </ul>
            <p><strong>Player Implementation:</strong> This demo showcases complete player character logic including movement controls, collision detection with cheese and obstacles, score tracking, and game state management.</p>
        </div>
    </div>

    <footer>
        <p>Cheese Game - Player Implementation Demo | Complete game logic with working interactions</p>
    </footer>

    <script>
        // Game Configuration
        const CONFIG = {
            PLAYER_SIZE: 20,
            CHEESE_SIZE: 15,
            OBSTACLE_SIZE: 25,
            PLAYER_SPEED: 4,
            INITIAL_LIVES: 3,
            MAX_CHEESE: 5,
            SCORE_PER_CHEESE: 100
        };

        // Game State
        const gameState = {
            player: {
                x: 200,
                y: 200,
                dx: 0,
                dy: 0
            },
            cheese: [],
            obstacles: [],
            score: 0,
            lives: CONFIG.INITIAL_LIVES,
            cheeseCollected: 0,
            isRunning: false,
            isPaused: false,
            gameOver: false,
            gameWon: false,
            keys: {}
        };

        // DOM Elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('scoreValue');
        const cheeseElement = document.getElementById('cheeseCount');
        const livesElement = document.getElementById('livesValue');
        const positionElement = document.getElementById('positionValue');
        const gameStatusElement = document.getElementById('gameStatus');
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const resetBtn = document.getElementById('resetBtn');
        const movementButtons = document.querySelectorAll('.movement');

        // Initialize Game
        function initGame() {
            // Reset game state
            gameState.player = {
                x: 200,
                y: 200,
                dx: 0,
                dy: 0
            };
            gameState.score = 0;
            gameState.lives = CONFIG.INITIAL_LIVES;
            gameState.cheeseCollected = 0;
            gameState.isRunning = false;
            gameState.isPaused = false;
            gameState.gameOver = false;
            gameState.gameWon = false;
            gameState.keys = {};

            // Generate cheese
            gameState.cheese = [];
            for (let i = 0; i < CONFIG.MAX_CHEESE; i++) {
                gameState.cheese.push({
                    x: Math.random() * (canvas.width - CONFIG.CHEESE_SIZE * 2) + CONFIG.CHEESE_SIZE,
                    y: Math.random() * (canvas.height - CONFIG.CHEESE_SIZE * 2) + CONFIG.CHEESE_SIZE,
                    collected: false
                });
            }

            // Generate obstacles
            gameState.obstacles = [];
            for (let i = 0; i < 8; i++) {
                gameState.obstacles.push({
                    x: Math.random() * (canvas.width - CONFIG.OBSTACLE_SIZE),
                    y: Math.random() * (canvas.height - CONFIG.OBSTACLE_SIZE)
                });
            }

            updateUI();
            gameStatusElement.textContent = 'Game Ready - Press Start!';
            gameStatusElement.className = 'game-status playing';
            draw();
        }

        // Draw Game
        function draw() {
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw obstacles
            ctx.fillStyle = '#F56565';
            gameState.obstacles.forEach(obstacle => {
                ctx.fillRect(obstacle.x, obstacle.y, CONFIG.OBSTACLE_SIZE, CONFIG.OBSTACLE_SIZE);
                ctx.strokeStyle = '#C53030';
                ctx.lineWidth = 2;
                ctx.strokeRect(obstacle.x, obstacle.y, CONFIG.OBSTACLE_SIZE, CONFIG.OBSTACLE_SIZE);
            });

            // Draw cheese
            ctx.fillStyle = '#F6E05E';
            gameState.cheese.forEach(cheese => {
                if (!cheese.collected) {
                    // Cheese wedge shape
                    ctx.beginPath();
                    ctx.moveTo(cheese.x + CONFIG.CHEESE_SIZE / 2, cheese.y);
                    ctx.lineTo(cheese.x + CONFIG.CHEESE_SIZE, cheese.y + CONFIG.CHEESE_SIZE / 2);
                    ctx.lineTo(cheese.x + CONFIG.CHEESE_SIZE / 2, cheese.y + CONFIG.CHEESE_SIZE);
                    ctx.lineTo(cheese.x, cheese.y + CONFIG.CHEESE_SIZE / 2);
                    ctx.closePath();
                    ctx.fill();
                    
                    // Cheese holes
                    ctx.fillStyle = '#D69E2E';
                    ctx.beginPath();
                    ctx.arc(cheese.x + CONFIG.CHEESE_SIZE / 3, cheese.y + CONFIG.CHEESE_SIZE / 3, 2, 0, Math.PI * 2);
                    ctx.arc(cheese.x + 2 * CONFIG.CHEESE_SIZE / 3, cheese.y + CONFIG.CHEESE_SIZE / 3, 2, 0, Math.PI * 2);
                    ctx.arc(cheese.x + CONFIG.CHEESE_SIZE / 3, cheese.y + 2 * CONFIG.CHEESE_SIZE / 3, 2, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = '#F6E05E';
                }
            });

            // Draw player (mouse)
            ctx.fillStyle = '#4A5568';
            ctx.beginPath();
            ctx.arc(gameState.player.x, gameState.player.y, CONFIG.PLAYER_SIZE / 2, 0, Math.PI * 2);
            ctx.fill();
            
            // Player eyes
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(gameState.player.x - 5, gameState.player.y - 3, 3, 0, Math.PI * 2);
            ctx.arc(gameState.player.x + 5, gameState.player.y - 3, 3, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = 'black';
            ctx.beginPath();
            ctx.arc(gameState.player.x - 5, gameState.player.y - 3, 1.5, 0, Math.PI * 2);
            ctx.arc(gameState.player.x + 5, gameState.player.y - 3, 1.5, 0, Math.PI * 2);
            ctx.fill();
            
            // Player tail
            ctx.strokeStyle = '#4A5568';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(gameState.player.x - CONFIG.PLAYER_SIZE / 2, gameState.player.y);
            ctx.lineTo(gameState.player.x - CONFIG.PLAYER_SIZE, gameState.player.y + 5);
            ctx.stroke();

            // Draw score and lives on canvas
            ctx.fillStyle = '#2D3748';
            ctx.font = '14px sans-serif';
            ctx.fillText(`Score: ${gameState.score}`, 10, 20);
            ctx.fillText(`Lives: ${gameState.lives}`, 10, 40);
            ctx.fillText(`Cheese: ${gameState.cheeseCollected}/${CONFIG.MAX_CHEESE}`, 10, 60);
        }

        // Update Game State
        function update() {
            if (!gameState.isRunning || gameState.isPaused || gameState.gameOver) return;

            // Update player position based on keys