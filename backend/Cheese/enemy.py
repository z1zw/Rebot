<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheese Chase Game</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }
        
        body {
            background: #F9F9FB;
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem;
            line-height: 1.5;
        }
        
        .container {
            max-width: 1200px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        header {
            text-align: center;
            padding: 1.5rem;
            background: #F2F2F5;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        h1 {
            font-size: clamp(1.75rem, 4vw, 2.5rem);
            color: #8B4513;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            font-size: clamp(0.9rem, 2vw, 1.1rem);
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .game-area {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        @media (min-width: 768px) {
            .game-area {
                flex-direction: row;
            }
        }
        
        .game-container {
            flex: 1;
            background: #EAECF0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            position: relative;
        }
        
        #gameCanvas {
            display: block;
            width: 100%;
            height: 500px;
            background: #1a1a2e;
        }
        
        .controls-panel {
            width: 100%;
            max-width: 300px;
            background: #F2F2F5;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        
        @media (min-width: 768px) {
            .controls-panel {
                width: 300px;
            }
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .stat-box {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .stat-value {
            font-size: 1.75rem;
            font-weight: bold;
            color: #8B4513;
            margin-top: 0.25rem;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        .controls {
            margin-bottom: 1.5rem;
        }
        
        .control-group {
            margin-bottom: 1rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #555;
            font-size: 0.9rem;
            font-weight: 500;
        }
        
        input[type="range"] {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #8B4513;
            cursor: pointer;
        }
        
        .buttons {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        button {
            padding: 0.875rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .primary-btn {
            background: #8B4513;
            color: white;
        }
        
        .primary-btn:hover {
            background: #A0522D;
            transform: translateY(-2px);
        }
        
        .secondary-btn {
            background: #666;
            color: white;
        }
        
        .secondary-btn:hover {
            background: #777;
            transform: translateY(-2px);
        }
        
        .instructions {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .instructions h3 {
            color: #8B4513;
            margin-bottom: 1rem;
            font-size: 1.25rem;
        }
        
        .instructions ul {
            padding-left: 1.5rem;
            color: #555;
        }
        
        .instructions li {
            margin-bottom: 0.5rem;
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
            z-index: 100;
        }
        
        .game-over h2 {
            font-size: 3rem;
            margin-bottom: 1rem;
            color: #FFD700;
        }
        
        .game-over p {
            font-size: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .mobile-controls {
            display: none;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(2, 1fr);
            gap: 0.5rem;
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
        }
        
        @media (max-width: 767px) {
            .mobile-controls {
                display: grid;
            }
            
            #gameCanvas {
                height: 400px;
            }
        }
        
        .mobile-btn {
            background: rgba(139, 69, 19, 0.8);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 1rem;
            font-size: 1.5rem;
            cursor: pointer;
            user-select: none;
        }
        
        .mobile-btn:active {
            background: rgba(160, 82, 45, 0.9);
        }
        
        .center-btn {
            grid-column: 2;
            grid-row: 1 / span 2;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Chase</h1>
            <p class="subtitle">Collect cheese while avoiding enemy mice! Use arrow keys or WASD to move. Survive as long as you can!</p>
        </header>
        
        <div class="game-area">
            <div class="game-container">
                <canvas id="gameCanvas"></canvas>
                <div class="game-over" id="gameOverScreen">
                    <h2>Game Over!</h2>
                    <p id="finalScore">Score: 0</p>
                    <button class="primary-btn" onclick="restartGame()">Play Again</button>
                </div>
            </div>
            
            <div class="controls-panel">
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-label">Score</div>
                        <div class="stat-value" id="scoreDisplay">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Cheese</div>
                        <div class="stat-value" id="cheeseDisplay">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Time</div>
                        <div class="stat-value" id="timeDisplay">0s</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Enemies</div>
                        <div class="stat-value" id="enemiesDisplay">3</div>
                    </div>
                </div>
                
                <div class="controls">
                    <div class="control-group">
                        <label for="enemySpeed">Enemy Speed: <span id="speedValue">1.0</span></label>
                        <input type="range" id="enemySpeed" min="0.5" max="2.0" step="0.1" value="1.0">
                    </div>
                    <div class="control-group">
                        <label for="enemyCount">Enemy Count: <span id="countValue">3</span></label>
                        <input type="range" id="enemyCount" min="1" max="8" step="1" value="3">
                    </div>
                </div>
                
                <div class="buttons">
                    <button class="primary-btn" onclick="startGame()">Start Game</button>
                    <button class="secondary-btn" onclick="pauseGame()">Pause/Resume</button>
                    <button class="secondary-btn" onclick="restartGame()">Restart Game</button>
                </div>
                
                <div class="mobile-controls">
                    <button class="mobile-btn" onmousedown="startMove('up')" ontouchstart="startMove('up')" onmouseup="stopMove()" ontouchend="stopMove()">↑</button>
                    <button class="mobile-btn center-btn" onmousedown="startMove('action')" ontouchstart="startMove('action')" onmouseup="stopMove()" ontouchend="stopMove()">⚡</button>
                    <button class="mobile-btn" onmousedown="startMove('left')" ontouchstart="startMove('left')" onmouseup="stopMove()" ontouchend="stopMove()">←</button>
                    <button class="mobile-btn" onmousedown="startMove('down')" ontouchstart="startMove('down')" onmouseup="stopMove()" ontouchend="stopMove()">↓</button>
                    <button class="mobile-btn" onmousedown="startMove('right')" ontouchstart="startMove('right')" onmouseup="stopMove()" ontouchend="stopMove()">→</button>
                </div>
            </div>
        </div>
        
        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li><strong>Objective:</strong> Collect as much cheese as possible while avoiding enemy mice.</li>
                <li><strong>Controls:</strong> Use arrow keys or WASD to move your mouse. On mobile, use the directional buttons.</li>
                <li><strong>Scoring:</strong> Each cheese collected gives you 10 points. Survive longer for bonus points!</li>
                <li><strong>Enemies:</strong> Enemy mice will chase you. Adjust their speed and count using sliders.</li>
                <li><strong>Power-up:</strong> The lightning button gives you a temporary speed boost!</li>
                <li><strong>Game Over:</strong> The game ends when an enemy catches you. Try to beat your high score!</li>
            </ul>
        </div>
    </div>

    <script>
        // Game constants
        const CANVAS_WIDTH = 800;
        const CANVAS_HEIGHT = 500;
        const PLAYER_SIZE = 20;
        const ENEMY_SIZE = 18;
        const CHEESE_SIZE = 15;
        const PLAYER_SPEED = 4;
        const BASE_ENEMY_SPEED = 1.0;
        const CHEESE_SPAWN_RATE = 0.02;
        const POWERUP_DURATION = 300;
        
        // Game state
        let canvas, ctx;
        let gameRunning = false;
        let gamePaused = false;
        let gameOver = false;
        let score = 0;
        let cheeseCollected = 0;
        let gameTime = 0;
        let lastTime = 0;
        let animationId = null;
        
        // Player
        let player = {
            x: CANVAS_WIDTH / 2,
            y: CANVAS_HEIGHT / 2,
            dx: 0,
            dy: 0,
            color: '#4CAF50',
            speed: PLAYER_SPEED,
            powerupActive: false,
            powerupTimer: 0
        };
        
        // Enemies array
        let enemies = [];
        
        // Cheese array
        let cheeses = [];
        
        // Power-ups array
        let powerups = [];
        
        // Input state
        let keys = {};
        let mobileMove = null;
        
        // Initialize game
        function init() {
            canvas = document.getElementById('gameCanvas');
            ctx = canvas.getContext('2d');
            
            // Set canvas size
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
            
            // Initialize enemies
            initEnemies();
            
            // Initialize some cheese
            for (let i = 0; i < 5; i++) {
                spawnCheese();
            }
            
            // Set up event listeners
            setupEventListeners();
            
            // Start game loop
            gameLoop();
        }
        
        // Initialize enemies
        function initEnemies() {
            enemies = [];
            const enemyCount = parseInt(document.getElementById('enemyCount').value);
            
            for (let i = 0; i < enemyCount; i++) {
                enemies.push({
                    x: Math.random() * (CANVAS_WIDTH - ENEMY_SIZE * 2) + ENEMY_SIZE,
                    y: Math.random() * (CANVAS_HEIGHT - ENEMY_SIZE * 2) + ENEMY_SIZE,
                    color: '#FF5252',
                    speed: BASE_ENEMY_SPEED * parseFloat(document.getElementById('enemySpeed').value),
                    movePattern: Math.floor(Math.random() * 3) // 0: direct chase, 1: predictive, 2: random
                });
            }
        }
        
        // Set up event listeners
        function setupEventListeners() {
            // Keyboard controls
            window.addEventListener('keydown', (e) => {
                keys[e.key.toLowerCase()] = true;
                
                // Prevent arrow key scrolling
                if(['arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(e.key.toLowerCase())) {
                    e.preventDefault();
                }
            });
            
            window.addEventListener('keyup', (e) => {
                keys[e.key.toLowerCase()] = false;
            });
            
            // Control sliders
            document.getElementById('enemySpeed').addEventListener('input', (e) => {
                document.getElementById('speedValue').textContent = e.target.value;
                if (gameRunning) {
                    enemies.forEach(enemy => {
                        enemy.speed = BASE_ENEMY_SPEED * parseFloat(e.target.value);
                    });
                }
            });
            
            document.getElementById('enemyCount').addEventListener('input', (e) => {
                document.getElementById('countValue').textContent = e.target.value;
                if (gameRunning) {
                    initEnemies();
                }
            });
            
            // Prevent context menu on canvas
            canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        }
        
        // Mobile controls
        function startMove(direction) {
            mobileMove = direction;
        }
        
        function stopMove() {
            mobileMove = null;
        }
        
        // Process input
        function processInput() {
            player.dx = 0;
            player.dy = 0;
            
            // Keyboard input
            if (keys['arrowleft'] || keys['a']) player.dx = -player.speed;
            if (keys['arrowright'] || keys['d']) player.dx = player.speed;
            if (keys['arrowup'] || keys['w']) player.dy = -player.speed;
            if (keys['arrowdown'] || keys['s']) player.dy = player.speed;
            
            // Mobile input
            if (mobileMove) {
                switch(mobileMove) {
                    case 'left': player.dx = -player.speed; break;
                    case 'right': player.dx = player.speed; break;
                    case 'up': player.dy = -player.speed; break;
                    case 'down': player.dy = player.speed; break;
                    case 'action': activatePowerup(); break;
                }
            }
            
            // Normalize diagonal movement
            if (player.dx !== 0 && player.dy !== 0) {
                player.dx *= 0.7071;
                player.dy *= 0.7071;
            }
        }
        
        // Update game state
        function update(deltaTime) {
            if (!gameRunning || gamePaused || gameOver) return;
            
            // Update player
            player.x += player.dx;
            player.y += player.dy;
            
            // Keep player in bounds
            player.x = Math.max(PLAYER_SIZE, Math.min(CANVAS_WIDTH - PLAYER_SIZE, player.x));
            player.y = Math.max(PLAYER_SIZE, Math.min(CANVAS_HEIGHT - PLAYER_SIZE, player.y