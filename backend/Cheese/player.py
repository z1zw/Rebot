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
            padding: 1.5rem;
            line-height: 1.5;
        }

        .container {
            width: 100%;
            max-width: 900px;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            text-align: center;
            padding: 1rem;
            background-color: #F2F2F5;
            border-radius: 1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        h1 {
            font-size: clamp(1.75rem, 4vw, 2.5rem);
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
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        @media (min-width: 768px) {
            .game-area {
                flex-direction: row;
                align-items: flex-start;
            }
        }

        .stats-panel {
            background-color: #EAECF0;
            padding: 1.5rem;
            border-radius: 1rem;
            flex: 1;
            min-width: 250px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .stats-panel h2 {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: #333;
        }

        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #D1D5DB;
        }

        .stat-item:last-child {
            border-bottom: none;
        }

        .stat-label {
            font-weight: 500;
            color: #555;
        }

        .stat-value {
            font-weight: 600;
            color: #1A1A1A;
        }

        #score {
            color: #D4A017;
            font-size: 1.1rem;
        }

        #lives {
            color: #DC2626;
        }

        .controls {
            margin-top: 1.5rem;
        }

        .controls h3 {
            font-size: 1rem;
            margin-bottom: 0.75rem;
            color: #555;
        }

        .key-hint {
            display: inline-block;
            background-color: #1A1A1A;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 0.5rem;
            font-family: monospace;
            margin: 0.25rem;
            font-size: 0.9rem;
        }

        .game-container {
            flex: 2;
            background-color: #1A1A1A;
            border-radius: 1rem;
            overflow: hidden;
            position: relative;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            min-height: 400px;
        }

        #gameCanvas {
            display: block;
            width: 100%;
            height: 100%;
            background-color: #0F0F0F;
        }

        .game-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: rgba(0, 0, 0, 0.85);
            color: white;
            text-align: center;
            padding: 2rem;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }

        .game-overlay.active {
            opacity: 1;
            pointer-events: all;
        }

        .overlay-title {
            font-size: clamp(2rem, 5vw, 3rem);
            margin-bottom: 1rem;
            color: #D4A017;
        }

        .overlay-message {
            font-size: 1.1rem;
            margin-bottom: 2rem;
            max-width: 500px;
            color: #CCC;
        }

        .btn {
            background-color: #D4A017;
            color: white;
            border: none;
            padding: 0.875rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 1rem;
        }

        .btn:hover {
            background-color: #B8860B;
            transform: translateY(-2px);
        }

        .btn:active {
            transform: translateY(0);
        }

        .mobile-controls {
            display: none;
            margin-top: 1.5rem;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        @media (max-width: 767px) {
            .mobile-controls {
                display: flex;
            }
        }

        .mobile-btn {
            background-color: #333;
            color: white;
            border: none;
            width: 4rem;
            height: 4rem;
            border-radius: 50%;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            user-select: none;
            touch-action: manipulation;
        }

        .mobile-btn:active {
            background-color: #555;
        }

        .instructions {
            background-color: #F2F2F5;
            padding: 1.5rem;
            border-radius: 1rem;
            margin-top: 1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .instructions h3 {
            font-size: 1.1rem;
            margin-bottom: 0.75rem;
            color: #333;
        }

        .instructions p {
            color: #666;
            margin-bottom: 0.5rem;
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            color: #888;
            font-size: 0.875rem;
            padding: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Collector</h1>
            <p class="subtitle">Move the mouse cursor to collect cheese while avoiding obstacles. Use arrow keys or WASD to control movement.</p>
        </header>

        <div class="game-area">
            <div class="stats-panel">
                <h2>Game Stats</h2>
                <div class="stat-item">
                    <span class="stat-label">Score</span>
                    <span id="score" class="stat-value">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Lives</span>
                    <span id="lives" class="stat-value">3</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Cheese Collected</span>
                    <span id="cheeseCount" class="stat-value">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">High Score</span>
                    <span id="highScore" class="stat-value">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Game Status</span>
                    <span id="status" class="stat-value">Playing</span>
                </div>

                <div class="controls">
                    <h3>Controls</h3>
                    <p>
                        <span class="key-hint">W</span> or <span class="key-hint">↑</span> - Move Up<br>
                        <span class="key-hint">A</span> or <span class="key-hint">←</span> - Move Left<br>
                        <span class="key-hint">S</span> or <span class="key-hint">↓</span> - Move Down<br>
                        <span class="key-hint">D</span> or <span class="key-hint">→</span> - Move Right<br>
                        <span class="key-hint">R</span> - Restart Game<br>
                        <span class="key-hint">P</span> - Pause/Resume
                    </p>
                </div>

                <button id="restartBtn" class="btn" style="width: 100%; margin-top: 1.5rem;">
                    Restart Game
                </button>
                <button id="pauseBtn" class="btn" style="width: 100%; margin-top: 0.75rem; background-color: #4B5563;">
                    Pause Game
                </button>
            </div>

            <div class="game-container">
                <canvas id="gameCanvas"></canvas>
                <div id="gameOverOverlay" class="game-overlay">
                    <h2 class="overlay-title">Game Over!</h2>
                    <p class="overlay-message">You collected <span id="finalScore">0</span> pieces of cheese. Try again to beat your high score!</p>
                    <button id="restartOverlayBtn" class="btn">Play Again</button>
                </div>
                <div id="pauseOverlay" class="game-overlay">
                    <h2 class="overlay-title">Game Paused</h2>
                    <p class="overlay-message">Press P or click Resume to continue playing.</p>
                    <button id="resumeBtn" class="btn">Resume Game</button>
                </div>
            </div>
        </div>

        <div class="mobile-controls">
            <button class="mobile-btn" id="upBtn">↑</button>
            <div style="display: flex; gap: 1rem; width: 100%; justify-content: center;">
                <button class="mobile-btn" id="leftBtn">←</button>
                <button class="mobile-btn" id="downBtn">↓</button>
                <button class="mobile-btn" id="rightBtn">→</button>
            </div>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <p>• Control the mouse cursor with keyboard arrows or WASD keys.</p>
            <p>• Collect yellow cheese pieces to increase your score.</p>
            <p>• Avoid red obstacles - they reduce your lives.</p>
            <p>• Game ends when you run out of lives.</p>
            <p>• Try to beat your high score!</p>
        </div>

        <footer>
            <p>Cheese Collector Game • Use keyboard controls to play • Refresh page to reset high score</p>
        </footer>
    </div>

    <script>
        // Game constants
        const PLAYER_SIZE = 20;
        const CHEESE_SIZE = 15;
        const OBSTACLE_SIZE = 25;
        const PLAYER_SPEED = 5;
        const MAX_CHEESE = 10;
        const MAX_OBSTACLES = 6;
        const INITIAL_LIVES = 3;

        // Game state
        let player = { x: 0, y: 0 };
        let cheese = [];
        let obstacles = [];
        let score = 0;
        let lives = INITIAL_LIVES;
        let cheeseCollected = 0;
        let highScore = localStorage.getItem('cheeseGameHighScore') || 0;
        let gameOver = false;
        let paused = false;
        let keys = {};
        let canvas, ctx;
        let animationId;

        // DOM elements
        const scoreElement = document.getElementById('score');
        const livesElement = document.getElementById('lives');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const highScoreElement = document.getElementById('highScore');
        const statusElement = document.getElementById('status');
        const finalScoreElement = document.getElementById('finalScore');
        const gameOverOverlay = document.getElementById('gameOverOverlay');
        const pauseOverlay = document.getElementById('pauseOverlay');
        const restartBtn = document.getElementById('restartBtn');
        const restartOverlayBtn = document.getElementById('restartOverlayBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const resumeBtn = document.getElementById('resumeBtn');

        // Mobile controls
        const upBtn = document.getElementById('upBtn');
        const downBtn = document.getElementById('downBtn');
        const leftBtn = document.getElementById('leftBtn');
        const rightBtn = document.getElementById('rightBtn');

        // Initialize game
        function init() {
            canvas = document.getElementById('gameCanvas');
            ctx = canvas.getContext('2d');
            
            // Set canvas size
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            
            // Initialize player position
            player.x = canvas.width / 2;
            player.y = canvas.height / 2;
            
            // Generate initial cheese and obstacles
            generateCheese();
            generateObstacles();
            
            // Set high score
            highScoreElement.textContent = highScore;
            
            // Start game loop
            gameLoop();
            
            // Setup event listeners
            setupEventListeners();
        }

        function resizeCanvas() {
            const container = canvas.parentElement;
            canvas.width = container.clientWidth;
            canvas.height = Math.max(400, container.clientHeight);
        }

        function generateCheese() {
            cheese = [];
            for (let i = 0; i < MAX_CHEESE; i++) {
                cheese.push({
                    x: Math.random() * (canvas.width - CHEESE_SIZE),
                    y: Math.random() * (canvas.height - CHEESE_SIZE),
                    collected: false
                });
            }
        }

        function generateObstacles() {
            obstacles = [];
            for (let i = 0; i < MAX_OBSTACLES; i++) {
                obstacles.push({
                    x: Math.random() * (canvas.width - OBSTACLE_SIZE),
                    y: Math.random() * (canvas.height - OBSTACLE_SIZE),
                    vx: (Math.random() - 0.5) * 3,
                    vy: (Math.random() - 0.5) * 3
                });
            }
        }

        function update() {
            if (paused || gameOver) return;
            
            // Move player based on keys
            if (keys['ArrowUp'] || keys['w'] || keys['W']) player.y -= PLAYER_SPEED;
            if (keys['ArrowDown'] || keys['s'] || keys['S']) player.y += PLAYER_SPEED;
            if (keys['ArrowLeft'] || keys['a'] || keys['A']) player.x -= PLAYER_SPEED;
            if (keys['ArrowRight'] || keys['d'] || keys['D']) player.x += PLAYER_SPEED;
            
            // Keep player within bounds
            player.x = Math.max(PLAYER_SIZE / 2, Math.min(canvas.width - PLAYER_SIZE / 2, player.x));
            player.y = Math.max(PLAYER_SIZE / 2, Math.min(canvas.height - PLAYER_SIZE / 2, player.y));
            
            // Update obstacles
            obstacles.forEach(obs => {
                obs.x += obs.vx;
                obs.y += obs.vy;
                
                // Bounce off walls
                if (obs.x <= 0 || obs.x >= canvas.width - OBSTACLE_SIZE) obs.vx *= -1;
                if (obs.y <= 0 || obs.y >= canvas.height - OBSTACLE_SIZE) obs.vy *= -1;
                
                // Keep within bounds
                obs.x = Math.max(0, Math.min(canvas.width - OBSTACLE_SIZE, obs.x));
                obs.y = Math.max(0, Math.min(canvas.height - OBSTACLE_SIZE, obs.y));
                
                // Check collision with player
                const dx = player.x - (obs.x + OBSTACLE_SIZE / 2);
                const dy = player.y - (obs.y + OBSTACLE_SIZE / 2);
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < (PLAYER_SIZE / 2 + OBSTACLE_SIZE / 2)) {
                    lives--;
                    livesElement.textContent = lives;
                    
                    // Move obstacle away after collision
                    obs.x = Math.random() * (canvas.width - OBSTACLE_SIZE);
                    obs.y = Math.random() * (canvas.height - OBSTACLE_SIZE);
                    
                    if (lives <= 0) {
                        endGame();
                    }
                }
            });
            
            // Check cheese collection
            cheese.forEach(c => {
                if (!c.collected) {
                    const dx = player.x - (c.x + CHEESE_SIZE / 2);
                    const dy = player.y - (c.y + CHEESE_SIZE / 2);
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < (PLAYER_SIZE / 2 + CHEESE_SIZE / 2)) {
                        c.collected = true;
                        score += 10;
                        cheeseCollected++;
                        scoreElement.textContent = score;
                        cheeseCountElement.textContent = cheeseCollected;
                        
                        // Update high score
                        if (score > highScore) {
                            highScore = score;
                            highScoreElement.textContent = highScore;
                            localStorage.setItem('cheeseGameHighScore', high