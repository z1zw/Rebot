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
            color: #333;
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
        .game-area {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        .stats {
            background-color: #F2F2F5;
            border-radius: 12px;
            padding: 1.2rem;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stat-box {
            text-align: center;
            flex: 1;
            min-width: 120px;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #D4A017;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.3rem;
        }
        .canvas-container {
            position: relative;
            width: 100%;
            aspect-ratio: 16/9;
            background-color: #EAECF0;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
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
            margin-top: 1rem;
        }
        button {
            padding: 0.8rem 1.8rem;
            font-size: 1rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            background-color: #D4A017;
            color: white;
            min-width: 140px;
        }
        button:hover {
            background-color: #B8860B;
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        button#restartBtn {
            background-color: #666;
        }
        button#restartBtn:hover {
            background-color: #555;
        }
        .instructions {
            background-color: #F2F2F5;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1rem;
        }
        .instructions h3 {
            margin-bottom: 0.8rem;
            color: #333;
        }
        .instructions ul {
            padding-left: 1.2rem;
            color: #555;
        }
        .instructions li {
            margin-bottom: 0.5rem;
        }
        .game-over {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(0,0,0,0.85);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            text-align: center;
            display: none;
            z-index: 10;
            width: 90%;
            max-width: 400px;
        }
        .game-over h2 {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #FFD700;
        }
        .game-over p {
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
        }
        @media (max-width: 600px) {
            .stats {
                flex-direction: column;
                align-items: center;
                gap: 1.5rem;
            }
            .stat-box {
                min-width: 100%;
            }
            .controls {
                flex-direction: column;
                align-items: center;
            }
            button {
                width: 100%;
                max-width: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Collector</h1>
            <p class="subtitle">Move the mouse or touch to collect cheese. Avoid the holes! Each cheese gives +10 points. Game ends when you miss 5 cheeses.</p>
        </header>
        <div class="game-area">
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
                    <div class="stat-value" id="missedCount">0</div>
                    <div class="stat-label">Missed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="lives">5</div>
                    <div class="stat-label">Lives Left</div>
                </div>
            </div>
            <div class="canvas-container">
                <canvas id="gameCanvas"></canvas>
                <div class="game-over" id="gameOverScreen">
                    <h2>Game Over!</h2>
                    <p>Final Score: <span id="finalScore">0</span></p>
                    <p>Cheese Collected: <span id="finalCheese">0</span></p>
                    <button id="playAgainBtn">Play Again</button>
                </div>
            </div>
            <div class="controls">
                <button id="startBtn">Start Game</button>
                <button id="pauseBtn">Pause</button>
                <button id="restartBtn">Restart</button>
            </div>
        </div>
        <div class="instructions">
            <h3>How to Play</h3>
            <ul>
                <li><strong>Move</strong>: Use mouse or touch to control the collector.</li>
                <li><strong>Collect</strong>: Catch yellow cheese pieces to earn 10 points each.</li>
                <li><strong>Avoid</strong>: If a cheese reaches the bottom, you lose a life.</li>
                <li><strong>Game Over</strong>: Game ends when you lose all 5 lives.</li>
                <li>Cheese spawns randomly. Speed increases slightly every 10 cheeses.</li>
            </ul>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const cheeseCountElement = document.getElementById('cheeseCount');
        const missedCountElement = document.getElementById('missedCount');
        const livesElement = document.getElementById('lives');
        const gameOverScreen = document.getElementById('gameOverScreen');
        const finalScoreElement = document.getElementById('finalScore');
        const finalCheeseElement = document.getElementById('finalCheese');
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const restartBtn = document.getElementById('restartBtn');
        const playAgainBtn = document.getElementById('playAgainBtn');

        let gameRunning = false;
        let gamePaused = false;
        let animationId = null;
        let lastTime = 0;
        let spawnTimer = 0;

        const config = {
            playerSize: 40,
            cheeseSize: 24,
            cheeseSpawnInterval: 800,
            cheeseFallSpeed: 2,
            speedIncreaseFactor: 1.05,
            maxMissed: 5,
            pointsPerCheese: 10
        };

        let player = {
            x: 0,
            y: 0,
            width: config.playerSize,
            height: config.playerSize
        };

        let cheeses = [];
        let score = 0;
        let cheeseCollected = 0;
        let missed = 0;
        let lives = config.maxMissed;
        let currentCheeseSpeed = config.cheeseFallSpeed;

        function resizeCanvas() {
            const container = canvas.parentElement;
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            player.x = canvas.width / 2 - player.width / 2;
            player.y = canvas.height - player.height - 20;
        }

        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        function drawPlayer() {
            ctx.fillStyle = '#4A90E2';
            ctx.fillRect(player.x, player.y, player.width, player.height);
            ctx.fillStyle = '#2C5282';
            ctx.fillRect(player.x + 5, player.y + 5, player.width - 10, player.height - 10);
        }

        function drawCheeses() {
            cheeses.forEach(cheese => {
                ctx.fillStyle = '#FFD700';
                ctx.beginPath();
                ctx.arc(cheese.x, cheese.y, cheese.radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#D4A017';
                ctx.beginPath();
                ctx.arc(cheese.x, cheese.y, cheese.radius * 0.6, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawPlayer();
            drawCheeses();
        }

        function updateCheeses(deltaTime) {
            for (let i = cheeses.length - 1; i >= 0; i--) {
                const cheese = cheeses[i];
                cheese.y += currentCheeseSpeed;

                if (cheese.y - cheese.radius > canvas.height) {
                    cheeses.splice(i, 1);
                    missed++;
                    missedCountElement.textContent = missed;
                    lives--;
                    livesElement.textContent = lives;
                    if (lives <= 0) {
                        endGame();
                    }
                } else if (
                    cheese.x + cheese.radius > player.x &&
                    cheese.x - cheese.radius < player.x + player.width &&
                    cheese.y + cheese.radius > player.y &&
                    cheese.y - cheese.radius < player.y + player.height
                ) {
                    cheeses.splice(i, 1);
                    score += config.pointsPerCheese;
                    cheeseCollected++;
                    scoreElement.textContent = score;
                    cheeseCountElement.textContent = cheeseCollected;

                    if (cheeseCollected % 10 === 0) {
                        currentCheeseSpeed *= config.speedIncreaseFactor;
                    }
                }
            }
        }

        function spawnCheese() {
            const radius = config.cheeseSize / 2;
            const x = radius + Math.random() * (canvas.width - radius * 2);
            cheeses.push({ x, y: -radius, radius });
        }

        function gameLoop(timestamp) {
            if (!gameRunning || gamePaused) return;

            const deltaTime = timestamp - lastTime;
            lastTime = timestamp;

            spawnTimer += deltaTime;
            if (spawnTimer > config.cheeseSpawnInterval) {
                spawnCheese();
                spawnTimer = 0;
            }

            updateCheeses(deltaTime);
            draw();

            animationId = requestAnimationFrame(gameLoop);
        }

        function startGame() {
            if (gameRunning) return;
            resetGame();
            gameRunning = true;
            gamePaused = false;
            lastTime = performance.now();
            animationId = requestAnimationFrame(gameLoop);
            startBtn.textContent = 'Restart';
        }

        function pauseGame() {
            if (!gameRunning) return;
            gamePaused = !gamePaused;
            pauseBtn.textContent = gamePaused ? 'Resume' : 'Pause';
            if (!gamePaused) {
                lastTime = performance.now();
                animationId = requestAnimationFrame(gameLoop);
            }
        }

        function resetGame() {
            cheeses = [];
            score = 0;
            cheeseCollected = 0;
            missed = 0;
            lives = config.maxMissed;
            currentCheeseSpeed = config.cheeseFallSpeed;
            spawnTimer = 0;

            scoreElement.textContent = score;
            cheeseCountElement.textContent = cheeseCollected;
            missedCountElement.textContent = missed;
            livesElement.textContent = lives;

            gameOverScreen.style.display = 'none';
            pauseBtn.textContent = 'Pause';
            gamePaused = false;
        }

        function endGame() {
            gameRunning = false;
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
            finalScoreElement.textContent = score;
            finalCheeseElement.textContent = cheeseCollected;
            gameOverScreen.style.display = 'block';
        }

        function handleMouseMove(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const x = (e.clientX - rect.left) * scaleX;
            player.x = Math.max(0, Math.min(x - player.width / 2, canvas.width - player.width));
        }

        function handleTouchMove(e) {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const x = (touch.clientX - rect.left) * scaleX;
            player.x = Math.max(0, Math.min(x - player.width / 2, canvas.width - player.width));
        }

        canvas.addEventListener('mousemove', handleMouseMove);
        canvas.addEventListener('touchmove', handleTouchMove, { passive: false });

        startBtn.addEventListener('click', startGame);
        pauseBtn.addEventListener('click', pauseGame);
        restartBtn.addEventListener('click', () => {
            if (gameRunning) {
                if (animationId) cancelAnimationFrame(animationId);
            }
            resetGame();
            startGame();
        });
        playAgainBtn.addEventListener('click', () => {
            gameOverScreen.style.display = 'none';
            resetGame();
            startGame();
        });

        draw();
    </script>
</body>
</html>