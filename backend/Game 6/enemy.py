<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheese Game - Enemy AI</title>
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
            background-color: #F2F2F5;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-top: 1rem;
        }

        h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            margin-bottom: 0.5rem;
            color: #2D3748;
            text-align: center;
        }

        .subtitle {
            font-size: 1rem;
            color: #718096;
            text-align: center;
            margin-bottom: 2rem;
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

        .panel {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .panel h2 {
            font-size: 1.3rem;
            margin-bottom: 1rem;
            color: #4A5568;
            border-bottom: 2px solid #EAECF0;
            padding-bottom: 0.5rem;
        }

        .canvas-container {
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1;
            background-color: #1A202C;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 1rem;
        }

        canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
            margin-top: 1rem;
        }

        button {
            padding: 0.7rem 1.2rem;
            border: none;
            border-radius: 6px;
            background-color: #4299E1;
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: background-color 0.2s;
            flex: 1;
            min-width: 120px;
        }

        button:hover {
            background-color: #3182CE;
        }

        button:active {
            transform: scale(0.98);
        }

        button.reset {
            background-color: #F56565;
        }

        button.reset:hover {
            background-color: #E53E3E;
        }

        button.pause {
            background-color: #ED8936;
        }

        button.pause:hover {
            background-color: #DD6B20;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .stat-box {
            background-color: #EDF2F7;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #2D3748;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #718096;
            margin-top: 0.3rem;
        }

        .instructions {
            margin-top: 2rem;
            padding: 1.5rem;
            background-color: #E6FFFA;
            border-radius: 10px;
            border-left: 4px solid #38B2AC;
        }

        .instructions h3 {
            color: #285E61;
            margin-bottom: 0.8rem;
        }

        .instructions ul {
            padding-left: 1.2rem;
            color: #4A5568;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .game-over {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
            z-index: 100;
            display: none;
        }

        .game-over h2 {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #F56565;
        }

        .game-over p {
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
        }

        .mobile-controls {
            display: none;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-top: 1.5rem;
            touch-action: manipulation;
        }

        .mobile-controls button {
            padding: 1.2rem;
            font-size: 1.2rem;
        }

        @media (max-width: 767px) {
            .mobile-controls {
                display: grid;
            }
            .container {
                padding: 1rem;
            }
            .panel {
                padding: 1rem;
            }
        }

        .enemy-info {
            margin-top: 1rem;
            padding: 1rem;
            background-color: #FFF5F5;
            border-radius: 8px;
            border-left: 4px solid #FC8181;
        }

        .enemy-info p {
            margin-bottom: 0.5rem;
            color: #742A2A;
        }
    </style>
</head>
<body>
    <h1>🧀 Cheese Game - Enemy AI</h1>
    <p class="subtitle">Avoid the enemies, collect cheese, and survive as long as possible!</p>

    <div class="container">
        <div class="game-area">
            <div class="panel">
                <h2>Game Canvas</h2>
                <div class="canvas-container">
                    <canvas id="gameCanvas"></canvas>
                    <div class="game-over" id="gameOverScreen">
                        <h2>Game Over!</h2>
                        <p id="finalScore">Score: 0</p>
                        <button onclick="restartGame()">Play Again</button>
                    </div>
                </div>
                
                <div class="controls">
                    <button onclick="startGame()" id="startBtn">Start Game</button>
                    <button onclick="togglePause()" id="pauseBtn" class="pause">Pause</button>
                    <button onclick="restartGame()" class="reset">Restart</button>
                </div>

                <div class="mobile-controls">
                    <button onmousedown="movePlayer('up')" ontouchstart="movePlayer('up')" ontouchend="stopPlayer()">⬆️</button>
                    <button onmousedown="movePlayer('left')" ontouchstart="movePlayer('left')" ontouchend="stopPlayer()">⬅️</button>
                    <button onmousedown="movePlayer('down')" ontouchstart="movePlayer('down')" ontouchend="stopPlayer()">⬇️</button>
                    <button onmousedown="movePlayer('right')" ontouchstart="movePlayer('right')" ontouchend="stopPlayer()">➡️</button>
                    <button onclick="collectCheese()" style="grid-column: span 2;">Collect Cheese</button>
                </div>
            </div>

            <div class="panel">
                <h2>Game Stats</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value" id="score">0</div>
                        <div class="stat-label">Score</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="cheeseCount">0</div>
                        <div class="stat-label">Cheese Collected</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="enemiesCount">3</div>
                        <div class="stat-label">Active Enemies</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="timeAlive">0</div>
                        <div class="stat-label">Seconds Alive</div>
                    </div>
                </div>

                <div class="enemy-info">
                    <h2>Enemy AI Information</h2>
                    <p><strong>Movement Patterns:</strong> Chase, Patrol, Random</p>
                    <p><strong>Collision Detection:</strong> Active with player and boundaries</p>
                    <p><strong>Game Over:</strong> Triggered on enemy-player collision</p>
                    <p><strong>Speed:</strong> Increases with score</p>
                </div>

                <div style="margin-top: 1.5rem;">
                    <h2>Controls</h2>
                    <p><strong>Desktop:</strong> Use WASD or Arrow Keys to move</p>
                    <p><strong>Mobile:</strong> Use on-screen buttons</p>
                    <p><strong>Goal:</strong> Collect yellow cheese while avoiding red enemies</p>
                </div>
            </div>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li>Move the blue player character using keyboard or touch controls</li>
                <li>Collect yellow cheese pieces to increase your score</li>
                <li>Avoid red enemy AI characters - they will chase you!</li>
                <li>Enemies become faster as your score increases</li>
                <li>Game ends when an enemy catches you</li>
                <li>Try to survive as long as possible and get the highest score!</li>
            </ul>
        </div>
    </div>

    <script>
        // Game Configuration
        const config = {
            canvasWidth: 600,
            canvasHeight: 600,
            playerSize: 20,
            enemySize: 25,
            cheeseSize: 15,
            playerSpeed: 5,
            baseEnemySpeed: 2,
            maxEnemies: 5,
            cheeseSpawnRate: 100, // frames between cheese spawns
            enemySpawnRate: 300, // frames between enemy spawns
            initialEnemies: 3
        };

        // Game State
        let gameState = {
            score: 0,
            cheeseCollected: 0,
            enemies: [],
            cheeses: [],
            player: {
                x: 300,
                y: 300,
                dx: 0,
                dy: 0
            },
            gameRunning: false,
            gamePaused: false,
            gameOver: false,
            frameCount: 0,
            timeAlive: 0,
            lastTime: 0,
            keys: {}
        };

        // DOM Elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const enemiesCountElement = document.getElementById('enemiesCount');
        const timeAliveElement = document.getElementById('timeAlive');
        const gameOverScreen = document.getElementById('gameOverScreen');
        const finalScoreElement = document.getElementById('finalScore');
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');

        // Initialize Canvas
        canvas.width = config.canvasWidth;
        canvas.height = config.canvasHeight;

        // Enemy Class
        class Enemy {
            constructor(x, y, pattern = 'chase') {
                this.x = x;
                this.y = y;
                this.size = config.enemySize;
                this.speed = config.baseEnemySpeed;
                this.pattern = pattern;
                this.color = '#FC8181';
                this.dx = 0;
                this.dy = 0;
                this.patrolDirection = Math.random() > 0.5 ? 1 : -1;
                this.patrolCounter = 0;
                this.patrolMax = 60;
            }

            update(playerX, playerY) {
                // Increase speed based on score
                this.speed = config.baseEnemySpeed + (gameState.score * 0.01);
                
                switch(this.pattern) {
                    case 'chase':
                        this.chasePattern(playerX, playerY);
                        break;
                    case 'patrol':
                        this.patrolPattern();
                        break;
                    case 'random':
                        this.randomPattern();
                        break;
                }

                // Update position
                this.x += this.dx;
                this.y += this.dy;

                // Boundary check
                if (this.x < 0) this.x = 0;
                if (this.x > config.canvasWidth - this.size) this.x = config.canvasWidth - this.size;
                if (this.y < 0) this.y = 0;
                if (this.y > config.canvasHeight - this.size) this.y = config.canvasHeight - this.size;
            }

            chasePattern(playerX, playerY) {
                const dx = playerX - this.x;
                const dy = playerY - this.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance > 0) {
                    this.dx = (dx / distance) * this.speed;
                    this.dy = (dy / distance) * this.speed;
                }
            }

            patrolPattern() {
                this.patrolCounter++;
                if (this.patrolCounter > this.patrolMax) {
                    this.patrolDirection *= -1;
                    this.patrolCounter = 0;
                    this.patrolMax = 30 + Math.random() * 60;
                }
                
                this.dx = this.patrolDirection * this.speed * 0.7;
                this.dy = Math.sin(this.patrolCounter * 0.1) * this.speed * 0.5;
            }

            randomPattern() {
                if (Math.random() < 0.05) {
                    this.dx = (Math.random() - 0.5) * this.speed * 2;
                    this.dy = (Math.random() - 0.5) * this.speed * 2;
                }
            }

            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x + this.size/2, this.y + this.size/2, this.size/2, 0, Math.PI * 2);
                ctx.fill();
                
                // Enemy eyes
                ctx.fillStyle = '#000';
                ctx.beginPath();
                ctx.arc(this.x + this.size/3, this.y + this.size/3, this.size/6, 0, Math.PI * 2);
                ctx.arc(this.x + 2*this.size/3, this.y + this.size/3, this.size/6, 0, Math.PI * 2);
                ctx.fill();
            }

            checkCollision(playerX, playerY, playerSize) {
                const dx = (this.x + this.size/2) - (playerX + playerSize/2);
                const dy = (this.y + this.size/2) - (playerY + playerSize/2);
                const distance = Math.sqrt(dx * dx + dy * dy);
                return distance < (this.size/2 + playerSize/2);
            }
        }

        // Cheese Class
        class Cheese {
            constructor(x, y) {
                this.x = x;
                this.y = y;
                this.size = config.cheeseSize;
                this.color = '#F6E05E';
            }

            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.ellipse(this.x + this.size/2, this.y + this.size/2, this.size/2, this.size/4, 0, 0, Math.PI * 2);
                ctx.fill();
                
                // Cheese holes
                ctx.fillStyle = '#D69E2E';
                ctx.beginPath();
                ctx.arc(this.x + this.size/3, this.y + this.size/3, this.size/8, 0, Math.PI * 2);
                ctx.arc(this.x + 2*this.size/3, this.y + 2*this.size/3, this.size/8, 0, Math.PI * 2);
                ctx.fill();
            }

            checkCollision(playerX, playerY, playerSize) {
                const dx = (this.x + this.size/2) - (playerX + playerSize/2);
                const dy = (this.y + this.size/2) - (playerY + playerSize/2);
                const distance = Math.sqrt(dx * dx + dy * dy);
                return distance < (this.size/2 + playerSize/2);
            }
        }

        // Initialize Game
        function initGame() {
            gameState.player = {
                x: config.canvasWidth / 2 - config.playerSize / 2,
                y: config.canvasHeight / 2 - config.playerSize / 2,
                dx: 0,
                dy: 0
            };
            
            gameState.enemies = [];
            gameState.cheeses = [];
            gameState.score = 0;
            gameState.cheeseCollected = 0;
            gameState.gameOver = false;
            gameState