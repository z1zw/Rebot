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
            background-color: #F9F9FB;
            color: #1A1A1A;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            line-height: 1.5;
        }

        .container {
            width: 100%;
            max-width: 800px;
            background-color: #F2F2F5;
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

        .stats {
            display: flex;
            justify-content: space-between;
            background-color: #FFFFFF;
            padding: 1rem;
            border-radius: 0.75rem;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .stat-box {
            text-align: center;
            flex: 1;
            min-width: 120px;
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

        #gameCanvas {
            background-color: #FFFFFF;
            border-radius: 0.75rem;
            display: block;
            width: 100%;
            height: auto;
            aspect-ratio: 1 / 1;
            max-height: 70vh;
            touch-action: none;
            box-shadow: inset 0 0 8px rgba(0, 0, 0, 0.05);
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
            margin-top: 1rem;
        }

        button {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 140px;
        }

        #startBtn {
            background-color: #4CAF50;
            color: white;
        }

        #startBtn:hover {
            background-color: #45A049;
        }

        #restartBtn {
            background-color: #2196F3;
            color: white;
        }

        #restartBtn:hover {
            background-color: #0B7DDA;
        }

        #pauseBtn {
            background-color: #FF9800;
            color: white;
        }

        #pauseBtn:hover {
            background-color: #E68A00;
        }

        .instructions {
            background-color: #FFFFFF;
            padding: 1.25rem;
            border-radius: 0.75rem;
            font-size: 0.9375rem;
            color: #444;
            line-height: 1.6;
        }

        .instructions h3 {
            color: #D4A017;
            margin-bottom: 0.75rem;
            font-size: 1.125rem;
        }

        .instructions ul {
            padding-left: 1.25rem;
            margin-bottom: 0.75rem;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .game-over {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 1rem;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            z-index: 100;
            display: none;
            max-width: 90%;
            width: 400px;
        }

        .game-over h2 {
            color: #D32F2F;
            margin-bottom: 1rem;
            font-size: 2rem;
        }

        .game-over p {
            font-size: 1.125rem;
            margin-bottom: 1.5rem;
            color: #333;
        }

        #closeOverlay {
            background-color: #2196F3;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            border: none;
            font-size: 1rem;
            cursor: pointer;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .stats {
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
            
            .stat-box {
                min-width: 100%;
            }
            
            button {
                min-width: 100%;
            }
            
            .controls {
                flex-direction: column;
            }
        }

        @media (max-width: 480px) {
            body {
                padding: 0.5rem;
            }
            
            .instructions {
                padding: 1rem;
            }
            
            .game-over {
                padding: 1.5rem;
                width: 95%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Chase</h1>
            <p class="subtitle">Guide the mouse to collect cheese while avoiding obstacles. Use arrow keys or touch to move!</p>
        </header>

        <div class="game-area">
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-label">Score</div>
                    <div id="score" class="stat-value">0</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Cheese Collected</div>
                    <div id="cheeseCount" class="stat-value">0</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Lives</div>
                    <div id="lives" class="stat-value">3</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Time</div>
                    <div id="time" class="stat-value">60</div>
                </div>
            </div>

            <canvas id="gameCanvas" width="600" height="600"></canvas>

            <div class="controls">
                <button id="startBtn">Start Game</button>
                <button id="pauseBtn">Pause</button>
                <button id="restartBtn">Restart</button>
            </div>

            <div class="instructions">
                <h3>How to Play</h3>
                <ul>
                    <li><strong>Objective:</strong> Collect as much cheese as possible before time runs out.</li>
                    <li><strong>Controls:</strong> Use arrow keys (↑, ↓, ←, →) or touch/swipe on the game area to move the mouse.</li>
                    <li><strong>Avoid:</strong> Red obstacles - touching them costs a life.</li>
                    <li><strong>Collect:</strong> Yellow cheese pieces to increase your score.</li>
                    <li><strong>Win:</strong> Score 50 points before time runs out.</li>
                    <li><strong>Lose:</strong> If you run out of lives or time reaches zero.</li>
                </ul>
                <p>Game speed increases every 10 cheese collected. Good luck!</p>
            </div>
        </div>
    </div>

    <div class="game-over" id="gameOver">
        <h2 id="gameOverTitle">Game Over</h2>
        <p id="gameOverMessage">You ran out of time!</p>
        <p>Final Score: <span id="finalScore">0</span></p>
        <p>Cheese Collected: <span id="finalCheese">0</span></p>
        <button id="closeOverlay">Play Again</button>
    </div>

    <script>
        // Game Configuration
        const CONFIG = {
            CANVAS_WIDTH: 600,
            CANVAS_HEIGHT: 600,
            PLAYER_SIZE: 20,
            CHEESE_SIZE: 15,
            OBSTACLE_SIZE: 25,
            INITIAL_SPEED: 3,
            MAX_SPEED: 8,
            SPEED_INCREMENT: 0.5,
            CHEESE_POINTS: 10,
            OBSTACLE_PENALTY: 1,
            INITIAL_LIVES: 3,
            GAME_TIME: 60, // seconds
            CHEESE_COUNT_FOR_WIN: 50,
            OBSTACLE_COUNT: 8,
            CHEESE_COUNT: 5,
            COLORS: {
                BACKGROUND: '#FFFFFF',
                PLAYER: '#4A4A4A',
                CHEESE: '#FFD700',
                OBSTACLE: '#FF5252',
                TEXT: '#1A1A1A',
                UI_BACKGROUND: '#F2F2F5'
            }
        };

        // Game State
        let gameState = {
            score: 0,
            cheeseCollected: 0,
            lives: CONFIG.INITIAL_LIVES,
            timeLeft: CONFIG.GAME_TIME,
            playerSpeed: CONFIG.INITIAL_SPEED,
            gameRunning: false,
            gamePaused: false,
            gameOver: false,
            lastTime: 0,
            keys: {},
            touchStart: null
        };

        // Game Objects
        let player = {
            x: CONFIG.CANVAS_WIDTH / 2,
            y: CONFIG.CANVAS_HEIGHT / 2,
            width: CONFIG.PLAYER_SIZE,
            height: CONFIG.PLAYER_SIZE
        };

        let cheese = [];
        let obstacles = [];

        // DOM Elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const livesElement = document.getElementById('lives');
        const timeElement = document.getElementById('time');
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const restartBtn = document.getElementById('restartBtn');
        const gameOverElement = document.getElementById('gameOver');
        const gameOverTitle = document.getElementById('gameOverTitle');
        const gameOverMessage = document.getElementById('gameOverMessage');
        const finalScoreElement = document.getElementById('finalScore');
        const finalCheeseElement = document.getElementById('finalCheese');
        const closeOverlayBtn = document.getElementById('closeOverlay');

        // Initialize Game Objects
        function initGameObjects() {
            cheese = [];
            obstacles = [];
            
            // Create cheese pieces
            for (let i = 0; i < CONFIG.CHEESE_COUNT; i++) {
                cheese.push(createCheese());
            }
            
            // Create obstacles
            for (let i = 0; i < CONFIG.OBSTACLE_COUNT; i++) {
                obstacles.push(createObstacle());
            }
            
            // Reset player position
            player.x = CONFIG.CANVAS_WIDTH / 2;
            player.y = CONFIG.CANVAS_HEIGHT / 2;
        }

        // Create a cheese piece at random position
        function createCheese() {
            return {
                x: Math.random() * (CONFIG.CANVAS_WIDTH - CONFIG.CHEESE_SIZE),
                y: Math.random() * (CONFIG.CANVAS_HEIGHT - CONFIG.CHEESE_SIZE),
                width: CONFIG.CHEESE_SIZE,
                height: CONFIG.CHEESE_SIZE,
                collected: false
            };
        }

        // Create an obstacle at random position
        function createObstacle() {
            return {
                x: Math.random() * (CONFIG.CANVAS_WIDTH - CONFIG.OBSTACLE_SIZE),
                y: Math.random() * (CONFIG.CANVAS_HEIGHT - CONFIG.OBSTACLE_SIZE),
                width: CONFIG.OBSTACLE_SIZE,
                height: CONFIG.OBSTACLE_SIZE
            };
        }

        // Update UI elements
        function updateUI() {
            scoreElement.textContent = gameState.score;
            cheeseCountElement.textContent = gameState.cheeseCollected;
            livesElement.textContent = gameState.lives;
            timeElement.textContent = Math.max(0, Math.floor(gameState.timeLeft));
        }

        // Handle player movement
        function updatePlayer() {
            let dx = 0, dy = 0;
            
            // Keyboard controls
            if (gameState.keys['ArrowUp'] || gameState.keys['w']) dy = -gameState.playerSpeed;
            if (gameState.keys['ArrowDown'] || gameState.keys['s']) dy = gameState.playerSpeed;
            if (gameState.keys['ArrowLeft'] || gameState.keys['a']) dx = -gameState.playerSpeed;
            if (gameState.keys['ArrowRight'] || gameState.keys['d']) dx = gameState.playerSpeed;
            
            // Normalize diagonal movement
            if (dx !== 0 && dy !== 0) {
                dx *= 0.7071; // 1/√2
                dy *= 0.7071;
            }
            
            // Update player position with boundary checking
            player.x = Math.max(0, Math.min(CONFIG.CANVAS_WIDTH - player.width, player.x + dx));
            player.y = Math.max(0, Math.min(CONFIG.CANVAS_HEIGHT - player.height, player.y + dy));
        }

        // Check collisions
        function checkCollisions() {
            // Check cheese collisions
            for (let i = 0; i < cheese.length; i++) {
                const c = cheese[i];
                if (!c.collected &&
                    player.x < c.x + c.width &&
                    player.x + player.width > c.x &&
                    player.y < c.y + c.height &&
                    player.y + player.height > c.y) {
                    
                    c.collected = true;
                    gameState.score += CONFIG.CHEESE_POINTS;
                    gameState.cheeseCollected++;
                    
                    // Increase speed every 10 cheese
                    if (gameState.cheeseCollected % 10 === 0 && gameState.playerSpeed < CONFIG.MAX_SPEED) {
                        gameState.playerSpeed += CONFIG.SPEED_INCREMENT;
                    }
                    
                    // Replace collected cheese
                    cheese[i] = createCheese();
                    
                    // Check win condition
                    if (gameState.cheeseCollected >= CONFIG.CHEESE_COUNT_FOR_WIN) {
                        endGame(true);
                    }
                }
            }
            
            // Check obstacle collisions
            for (const obstacle of obstacles) {
                if (player.x < obstacle.x + obstacle.width &&
                    player.x + player.width > obstacle.x &&
                    player.y < obstacle.y + obstacle.height &&
                    player.y + player.height > obstacle.y) {
                    
                    gameState.lives -= CONFIG.OBSTACLE_PENALTY;
                    gameState.score = Math.max(0, gameState.score - 5);
                    
                    // Push player away from obstacle
                    const pushX = player.x < obstacle.x ? -20 : 20;
                    const pushY = player.y < obstacle.y ? -20 : 20;
                    player.x = Math.max(0, Math.min(CONFIG.CANVAS_WIDTH - player.width, player.x + pushX));
                    player.y = Math.max(0, Math.min(CONFIG.CANVAS_HEIGHT - player.height, player.y + pushY));
                    
                    // Check lose condition
                    if (gameState.lives <= 0) {
                        endGame(false);
                    }
                    break;
                }
            }
        }

        // Draw game objects
        function draw() {
            // Clear canvas
            ctx.fillStyle = CONFIG.COLORS.BACKGROUND;
            ctx.fillRect(0, 0, CONFIG.CANVAS_WIDTH, CONFIG.CANVAS_HEIGHT);
            
            // Draw obstacles
            ctx.fillStyle = CONFIG.COLORS.OBSTACLE;
            for (const obstacle of obstacles) {
                ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
                // Add some detail to obstacles
                ctx.strokeStyle = '#C62828';
                ctx.lineWidth = 2;
                ctx.strokeRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
            }
            
            // Draw cheese
            ctx.fillStyle = CONFIG.COLORS.CHEESE;
            for (const c of cheese) {
                if (!c.collected) {
                    // Draw cheese wedge shape
                    ctx.beginPath();
                    ctx.moveTo(c.x + c.width/2, c.y);
                    ctx.lineTo(c.x + c.width, c.y + c.height/2);
                    ctx.lineTo(c.x + c.width/2, c.y + c.height);
                    ctx.lineTo(c.x, c.y + c.height/2);
                    ctx.closePath();
                    ctx.fill();
                    
                    // Add cheese holes
                    ctx.fillStyle = '#FFA000';
                    ctx.beginPath();
                    ctx.arc(c.x +