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
            color: #1a1a1a;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem clamp(1rem, 5vw, 3rem);
            line-height: 1.5;
        }
        .container {
            width: 100%;
            max-width: 800px;
            background-color: #F2F2F5;
            border-radius: 1rem;
            padding: clamp(1.5rem, 4vw, 2.5rem);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        header {
            text-align: center;
            margin-bottom: 0.5rem;
        }
        h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            color: #D4A017;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: clamp(0.9rem, 2vw, 1.1rem);
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }
        .game-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            background-color: #EAECF0;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            font-size: clamp(0.9rem, 2vw, 1rem);
        }
        .score, .lives, .level {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
        }
        .score span, .lives span, .level span {
            background-color: #fff;
            padding: 0.4rem 0.8rem;
            border-radius: 0.5rem;
            min-width: 3.5rem;
            text-align: center;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
        }
        .game-area {
            position: relative;
            width: 100%;
            aspect-ratio: 16/9;
            background-color: #fff;
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: inset 0 0 8px rgba(0,0,0,0.1);
            touch-action: none;
            user-select: none;
        }
        #gameCanvas {
            display: block;
            width: 100%;
            height: 100%;
        }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
            margin-top: 0.5rem;
        }
        button {
            background-color: #D4A017;
            color: white;
            border: none;
            padding: 0.8rem 1.8rem;
            border-radius: 0.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
            flex: 1;
            min-width: 140px;
            max-width: 200px;
        }
        button:hover {
            background-color: #c19115;
        }
        button:active {
            transform: scale(0.98);
        }
        button#restartBtn {
            background-color: #4A6FA5;
        }
        button#restartBtn:hover {
            background-color: #3d5c8a;
        }
        .instructions {
            background-color: #EAECF0;
            padding: 1.2rem 1.5rem;
            border-radius: 0.75rem;
            font-size: clamp(0.85rem, 2vw, 0.95rem);
            line-height: 1.6;
        }
        .instructions h3 {
            margin-bottom: 0.5rem;
            color: #333;
        }
        .instructions ul {
            padding-left: 1.2rem;
            color: #555;
        }
        .instructions li {
            margin-bottom: 0.3rem;
        }
        .game-status {
            text-align: center;
            font-size: clamp(1rem, 2.5vw, 1.3rem);
            font-weight: 700;
            min-height: 2rem;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #fff;
            margin-top: 0.5rem;
        }
        .win {
            color: #2E8B57;
        }
        .lose {
            color: #D32F2F;
        }
        @media (max-width: 600px) {
            .game-info {
                flex-direction: column;
                align-items: stretch;
                text-align: center;
            }
            .score, .lives, .level {
                justify-content: center;
            }
            .controls {
                flex-direction: column;
                align-items: center;
            }
            button {
                max-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Game</h1>
            <p class="subtitle">Collect cheese, avoid enemies, and survive as long as you can!</p>
        </header>

        <div class="game-info">
            <div class="score">Score: <span id="scoreValue">0</span></div>
            <div class="lives">Lives: <span id="livesValue">3</span></div>
            <div class="level">Level: <span id="levelValue">1</span></div>
        </div>

        <div class="game-area">
            <canvas id="gameCanvas"></canvas>
        </div>

        <div class="game-status" id="gameStatus"></div>

        <div class="controls">
            <button id="startBtn">Start Game</button>
            <button id="pauseBtn">Pause</button>
            <button id="restartBtn">Restart</button>
        </div>

        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li><strong>Move:</strong> Use Arrow Keys or WASD, or touch/drag on mobile.</li>
                <li><strong>Goal:</strong> Collect yellow cheese pieces to increase score.</li>
                <li><strong>Avoid:</strong> Red enemies - each hit costs a life.</li>
                <li><strong>Level up:</strong> Every 10 cheese pieces increases level and enemy speed.</li>
                <li><strong>Win:</strong> Reach 50 cheese pieces.</li>
                <li><strong>Lose:</strong> Lose all 3 lives.</li>
            </ul>
        </div>
    </div>

    <script>
        // Game state
        const state = {
            score: 0,
            lives: 3,
            level: 1,
            gameRunning: false,
            gamePaused: false,
            gameOver: false,
            player: { x: 400, y: 300, size: 20, speed: 5 },
            cheese: { x: 100, y: 100, size: 15, active: true },
            enemies: [],
            enemySpeed: 2,
            enemySpawnRate: 100, // frames
            enemySpawnCounter: 0,
            keys: {},
            touch: { x: 0, y: 0, active: false }
        };

        // DOM elements
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreValue = document.getElementById('scoreValue');
        const livesValue = document.getElementById('livesValue');
        const levelValue = document.getElementById('levelValue');
        const gameStatus = document.getElementById('gameStatus');
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const restartBtn = document.getElementById('restartBtn');

        // Initialize canvas
        function initCanvas() {
            const rect = canvas.parentElement.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
            state.player.x = canvas.width / 2;
            state.player.y = canvas.height / 2;
            placeCheese();
        }

        // Place cheese at random position
        function placeCheese() {
            state.cheese.x = Math.random() * (canvas.width - state.cheese.size * 2) + state.cheese.size;
            state.cheese.y = Math.random() * (canvas.height - state.cheese.size * 2) + state.cheese.size;
            state.cheese.active = true;
        }

        // Spawn a new enemy
        function spawnEnemy() {
            const side = Math.floor(Math.random() * 4);
            let x, y;
            const size = 18;
            switch(side) {
                case 0: x = -size; y = Math.random() * canvas.height; break;
                case 1: x = canvas.width + size; y = Math.random() * canvas.height; break;
                case 2: x = Math.random() * canvas.width; y = -size; break;
                case 3: x = Math.random() * canvas.width; y = canvas.height + size; break;
            }
            const angle = Math.atan2(state.player.y - y, state.player.x - x);
            state.enemies.push({
                x, y, size,
                vx: Math.cos(angle) * state.enemySpeed,
                vy: Math.sin(angle) * state.enemySpeed
            });
        }

        // Update game state
        function update() {
            if (!state.gameRunning || state.gamePaused || state.gameOver) return;

            // Move player based on keys
            if (state.keys['ArrowUp'] || state.keys['w'] || state.keys['W']) state.player.y -= state.player.speed;
            if (state.keys['ArrowDown'] || state.keys['s'] || state.keys['S']) state.player.y += state.player.speed;
            if (state.keys['ArrowLeft'] || state.keys['a'] || state.keys['A']) state.player.x -= state.player.speed;
            if (state.keys['ArrowRight'] || state.keys['d'] || state.keys['D']) state.player.x += state.player.speed;

            // Touch movement
            if (state.touch.active) {
                const dx = state.touch.x - state.player.x;
                const dy = state.touch.y - state.player.y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (dist > state.player.speed) {
                    state.player.x += (dx / dist) * state.player.speed;
                    state.player.y += (dy / dist) * state.player.speed;
                }
            }

            // Keep player in bounds
            state.player.x = Math.max(state.player.size, Math.min(canvas.width - state.player.size, state.player.x));
            state.player.y = Math.max(state.player.size, Math.min(canvas.height - state.player.size, state.player.y));

            // Cheese collision
            if (state.cheese.active) {
                const dx = state.player.x - state.cheese.x;
                const dy = state.player.y - state.cheese.y;
                const distance = Math.sqrt(dx*dx + dy*dy);
                if (distance < state.player.size + state.cheese.size) {
                    state.score++;
                    scoreValue.textContent = state.score;
                    placeCheese();
                    // Level up every 10 cheese
                    if (state.score % 10 === 0) {
                        state.level++;
                        levelValue.textContent = state.level;
                        state.enemySpeed += 0.5;
                        gameStatus.textContent = `Level ${state.level}! Enemies faster!`;
                        gameStatus.className = 'game-status win';
                        setTimeout(() => gameStatus.textContent = '', 1500);
                    }
                    // Win condition
                    if (state.score >= 50) {
                        state.gameOver = true;
                        gameStatus.textContent = '🎉 You Win! Collected 50 cheese!';
                        gameStatus.className = 'game-status win';
                    }
                }
            }

            // Enemy spawning
            state.enemySpawnCounter++;
            if (state.enemySpawnCounter >= state.enemySpawnRate) {
                spawnEnemy();
                state.enemySpawnCounter = 0;
            }

            // Update enemies
            for (let i = state.enemies.length - 1; i >= 0; i--) {
                const e = state.enemies[i];
                e.x += e.vx;
                e.y += e.vy;

                // Remove if out of bounds
                if (e.x < -50 || e.x > canvas.width + 50 || e.y < -50 || e.y > canvas.height + 50) {
                    state.enemies.splice(i, 1);
                    continue;
                }

                // Enemy-player collision
                const dx = state.player.x - e.x;
                const dy = state.player.y - e.y;
                const distance = Math.sqrt(dx*dx + dy*dy);
                if (distance < state.player.size + e.size) {
                    state.lives--;
                    livesValue.textContent = state.lives;
                    state.enemies.splice(i, 1);
                    // Flash red
                    canvas.style.backgroundColor = '#ffdddd';
                    setTimeout(() => canvas.style.backgroundColor = '', 200);
                    // Lose condition
                    if (state.lives <= 0) {
                        state.gameOver = true;
                        gameStatus.textContent = '💀 Game Over! No lives left.';
                        gameStatus.className = 'game-status lose';
                    } else {
                        gameStatus.textContent = `Ouch! ${state.lives} lives left.`;
                        gameStatus.className = 'game-status lose';
                        setTimeout(() => gameStatus.textContent = '', 1000);
                    }
                }
            }
        }

        // Draw everything
        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw cheese
            if (state.cheese.active) {
                ctx.fillStyle = '#FFD700';
                ctx.beginPath();
                ctx.arc(state.cheese.x, state.cheese.y, state.cheese.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#DAA520';
                ctx.beginPath();
                ctx.arc(state.cheese.x - 4, state.cheese.y - 3, 3, 0, Math.PI * 2);
                ctx.arc(state.cheese.x + 5, state.cheese.y + 2, 2, 0, Math.PI * 2);
                ctx.arc(state.cheese.x + 2, state.cheese.y - 5, 2.5, 0, Math.PI * 2);
                ctx.fill();
            }

            // Draw player
            ctx.fillStyle = '#4A6FA5';
            ctx.beginPath();
            ctx.arc(state.player.x, state.player.y, state.player.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#2E4A76';
            ctx.beginPath();
            ctx.arc(state.player.x - 5, state.player.y - 5, 4, 0, Math.PI * 2);
            ctx.arc(state.player.x + 6, state.player.y + 4, 3, 0, Math.PI * 2);
            ctx.fill();

            // Draw enemies
            ctx.fillStyle = '#D32F2F';
            for (const e of state.enemies) {
                ctx.beginPath();
                ctx.arc(e.x, e.y, e.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#9A1B1B';
                ctx.beginPath();
                ctx.arc(e.x - 4, e.y - 4, 3, 0, Math.PI * 2);
                ctx.arc(e.x + 4, e.y + 4, 3, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#D32F2F';
            }

            // Draw touch target if active
            if (state.touch.active) {
                ctx.strokeStyle = 'rgba(74, 111, 165, 0.5)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(state.touch.x, state.touch.y, 10, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        // Game loop
        function gameLoop() {
            update();
            draw();
            requestAnimationFrame(gameLoop);
        }

        // Event Listeners
        window.addEventListener('keydown', (e) => {
            state.keys[e.key] = true;
        });
        window.addEventListener('keyup', (e) => {
            state.keys[e.key] = false;
        });

        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            state.touch.x = e.touches[0].clientX - rect.left;
            state.touch.y = e.touches[0].clientY - rect.top;
            state.touch.active = true;
        });
        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            state.touch.x = e.touches[0].clientX - rect.left;
            state.touch.y = e.touches[0].clientY - rect.top;
        });
        canvas.addEventListener('touchend', () => {
            state.touch.active = false;
        });

        canvas.addEventListener('mousedown', (