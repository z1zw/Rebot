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
            color: #1A1A1A;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: clamp(1rem, 3vw, 2rem);
            line-height: 1.5;
        }

        .container {
            width: 100%;
            max-width: 800px;
            display: flex;
            flex-direction: column;
            gap: clamp(1rem, 3vw, 2rem);
        }

        header {
            text-align: center;
            padding: 1.5rem;
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
            font-size: clamp(1rem, 2vw, 1.2rem);
            color: #666;
        }

        .game-area {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        @media (min-width: 768px) {
            .game-area {
                grid-template-columns: 1fr 300px;
            }
        }

        .board-container {
            background-color: #EAECF0;
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .stats {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .stat-box {
            background-color: #fff;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            min-width: 120px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        }

        .stat-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.25rem;
        }

        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #1A1A1A;
        }

        #score {
            color: #D4A017;
        }

        #timer {
            color: #2E8B57;
        }

        .game-board {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            aspect-ratio: 1;
            background-color: #fff;
            border-radius: 0.75rem;
            padding: 1rem;
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        @media (min-width: 480px) {
            .game-board {
                grid-template-columns: repeat(5, 1fr);
            }
        }

        @media (min-width: 640px) {
            .game-board {
                grid-template-columns: repeat(6, 1fr);
            }
        }

        .cell {
            background-color: #F2F2F5;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            user-select: none;
            transition: all 0.2s ease;
            font-size: clamp(1.5rem, 3vw, 2rem);
            aspect-ratio: 1;
        }

        .cell:hover {
            background-color: #E0E0E5;
            transform: scale(1.03);
        }

        .cell.cheese {
            background-color: #FFF3CD;
            color: #D4A017;
        }

        .cell.cheese::after {
            content: "🧀";
        }

        .cell.trap {
            background-color: #F8D7DA;
            color: #721C24;
        }

        .cell.trap::after {
            content: "🐭";
        }

        .cell.revealed {
            pointer-events: none;
        }

        .cell.matched {
            opacity: 0.4;
            transform: scale(0.95);
        }

        .controls-sidebar {
            background-color: #fff;
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .instructions {
            background-color: #F8F9FA;
            padding: 1.25rem;
            border-radius: 0.75rem;
            border-left: 4px solid #D4A017;
        }

        .instructions h3 {
            color: #D4A017;
            margin-bottom: 0.75rem;
            font-size: 1.2rem;
        }

        .instructions ul {
            list-style-position: inside;
            color: #555;
            font-size: 0.95rem;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .controls {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        button {
            background-color: #D4A017;
            color: white;
            border: none;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        button:hover {
            background-color: #B8860B;
            transform: translateY(-2px);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            background-color: #CCCCCC;
            cursor: not-allowed;
            transform: none;
        }

        #restartBtn {
            background-color: #2E8B57;
        }

        #restartBtn:hover {
            background-color: #228B22;
        }

        .game-over {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }

        .game-over.active {
            opacity: 1;
            pointer-events: all;
        }

        .game-over-content {
            background-color: #fff;
            padding: clamp(1.5rem, 4vw, 3rem);
            border-radius: 1.5rem;
            text-align: center;
            max-width: 90%;
            width: 500px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        .game-over h2 {
            font-size: clamp(1.75rem, 4vw, 2.5rem);
            margin-bottom: 1rem;
            color: #D4A017;
        }

        .game-over p {
            font-size: 1.1rem;
            color: #555;
            margin-bottom: 1.5rem;
        }

        .final-score {
            font-size: 3rem;
            font-weight: 700;
            color: #2E8B57;
            margin: 1.5rem 0;
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            color: #888;
            font-size: 0.9rem;
            padding: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧀 Cheese Game</h1>
            <p class="subtitle">Find all the cheese before time runs out! Avoid the mouse traps.</p>
        </header>

        <div class="game-area">
            <div class="board-container">
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-label">Score</div>
                        <div id="score" class="stat-value">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Time Left</div>
                        <div id="timer" class="stat-value">60</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Cheese Found</div>
                        <div id="found" class="stat-value">0 / 8</div>
                    </div>
                </div>

                <div id="gameBoard" class="game-board">
                    <!-- Cells will be generated by JavaScript -->
                </div>
            </div>

            <div class="controls-sidebar">
                <div class="instructions">
                    <h3>How to Play</h3>
                    <ul>
                        <li>Click on cells to reveal what's underneath.</li>
                        <li>Find all 8 cheese pieces to win.</li>
                        <li>Avoid the 4 mouse traps - they end the game!</li>
                        <li>You have 60 seconds to complete the game.</li>
                        <li>Each cheese found gives +10 points.</li>
                        <li>Complete quickly for bonus points!</li>
                    </ul>
                </div>

                <div class="controls">
                    <button id="startBtn">
                        <span>▶️</span> Start Game
                    </button>
                    <button id="restartBtn" disabled>
                        <span>🔄</span> Restart Game
                    </button>
                    <button id="hintBtn" disabled>
                        <span>💡</span> Get Hint (Costs 5 points)
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div id="gameOverScreen" class="game-over">
        <div class="game-over-content">
            <h2 id="gameOverTitle">Game Over</h2>
            <p id="gameOverMessage">You found all the cheese! Congratulations!</p>
            <div class="final-score" id="finalScore">0</div>
            <button id="playAgainBtn">
                <span>🎮</span> Play Again
            </button>
        </div>
    </div>

    <footer>
        <p>Cheese Game • Find all the cheese before time runs out!</p>
    </footer>

    <script>
        // Game configuration
        const CONFIG = {
            totalCells: 24,
            cheeseCount: 8,
            trapCount: 4,
            initialTime: 60,
            cheesePoints: 10,
            timeBonusMultiplier: 2,
            hintCost: 5
        };

        // Game state
        let gameState = {
            score: 0,
            timeLeft: CONFIG.initialTime,
            cheeseFound: 0,
            trapsRevealed: 0,
            gameActive: false,
            gameOver: false,
            cells: [],
            revealedCells: [],
            timerInterval: null,
            boardElement: null
        };

        // DOM elements
        const elements = {
            gameBoard: document.getElementById('gameBoard'),
            score: document.getElementById('score'),
            timer: document.getElementById('timer'),
            found: document.getElementById('found'),
            startBtn: document.getElementById('startBtn'),
            restartBtn: document.getElementById('restartBtn'),
            hintBtn: document.getElementById('hintBtn'),
            gameOverScreen: document.getElementById('gameOverScreen'),
            gameOverTitle: document.getElementById('gameOverTitle'),
            gameOverMessage: document.getElementById('gameOverMessage'),
            finalScore: document.getElementById('finalScore'),
            playAgainBtn: document.getElementById('playAgainBtn')
        };

        // Initialize game
        function initGame() {
            resetGameState();
            createBoard();
            updateUI();
            setupEventListeners();
        }

        // Reset game state
        function resetGameState() {
            gameState = {
                score: 0,
                timeLeft: CONFIG.initialTime,
                cheeseFound: 0,
                trapsRevealed: 0,
                gameActive: false,
                gameOver: false,
                cells: [],
                revealedCells: [],
                timerInterval: null,
                boardElement: elements.gameBoard
            };
        }

        // Create game board
        function createBoard() {
            elements.gameBoard.innerHTML = '';
            gameState.cells = [];
            gameState.revealedCells = new Array(CONFIG.totalCells).fill(false);

            // Create cell types array
            let cellTypes = [];
            for (let i = 0; i < CONFIG.cheeseCount; i++) cellTypes.push('cheese');
            for (let i = 0; i < CONFIG.trapCount; i++) cellTypes.push('trap');
            for (let i = 0; i < CONFIG.totalCells - CONFIG.cheeseCount - CONFIG.trapCount; i++) {
                cellTypes.push('empty');
            }

            // Shuffle cell types
            cellTypes = shuffleArray(cellTypes);

            // Create cells
            for (let i = 0; i < CONFIG.totalCells; i++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.index = i;
                cell.dataset.type = cellTypes[i];
                
                cell.addEventListener('click', () => handleCellClick(i));
                
                elements.gameBoard.appendChild(cell);
                gameState.cells.push({
                    element: cell,
                    type: cellTypes[i],
                    revealed: false
                });
            }
        }

        // Shuffle array using Fisher-Yates algorithm
        function shuffleArray(array) {
            const newArray = [...array];
            for (let i = newArray.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
            }
            return newArray;
        }

        // Handle cell click
        function handleCellClick(index) {
            if (!gameState.gameActive || gameState.gameOver || gameState.cells[index].revealed) {
                return;
            }

            const cell = gameState.cells[index];
            cell.revealed = true;
            cell.element.classList.add('revealed', cell.type);

            if (cell.type === 'cheese') {
                gameState.cheeseFound++;
                gameState.score += CONFIG.cheesePoints;
                
                // Check win condition
                if (gameState.cheeseFound === CONFIG.cheeseCount) {
                    endGame(true);
                }
            } else if (cell.type === 'trap') {
                gameState.trapsRevealed++;
                endGame(false);
            }

            updateUI();
        }

        // Start game
        function startGame() {
            if (gameState.gameActive) return;
            
            gameState.gameActive = true;
            gameState.gameOver = false;
            elements.startBtn.disabled = true;
            elements.restartBtn.disabled = false;
            elements.hintBtn.disabled = false;
            
            // Start timer
            gameState.timerInterval = setInterval(() => {
                if (!gameState.gameActive || gameState.gameOver) return;
                
                gameState.timeLeft--;
                elements.timer.textContent = gameState.timeLeft;
                
                if (gameState.timeLeft <= 0) {
                    endGame(false);
                }
            }, 1000);
        }

        // End game
        function endGame(isWin) {
            gameState.gameActive = false;
            gameState.gameOver = true;
            
            clearInterval(gameState.timerInterval);
            
            // Calculate final score
            if (isWin) {
                const timeBonus = Math.floor(gameState.timeLeft * CONFIG.timeBonusMultiplier);
                gameState.score += timeBonus;
            }
            
            // Show game over screen
            elements.gameOverTitle.textContent = isWin ? 'You Win! 🎉' : 'Game Over 💀';
            elements.gameOverMessage.textContent = isWin 
                ? `You found all ${CONFIG.cheeseCount} cheese pieces with ${gameState.timeLeft} seconds left!`
                : `You revealed ${gameState.trapsRevealed} trap${gameState.trapsRevealed > 1 ? 's' : ''}. Better luck next time!`;
            elements.finalScore.textContent = gameState.score;
            elements.gameOverScreen.classList.add('active');
        }

        // Restart game
        function restartGame() {
            clearInterval(gameState.timerInterval);
            resetGameState();
            createBoard();
            updateUI();
            elements.startBtn.disabled = false;
            elements.restartBtn.disabled = true;
            elements.hintBtn.disabled = true;
            elements.gameOverScreen.classList.remove('active');
        }

        // Provide hint
        function provideHint() {
            if (!gameState.gameActive || gameState.gameOver || gameState.score < CONFIG.hintCost) {
                return;
            }

            // Find unrevealed cheese
            const unrevealedCheese = gameState.cells
                .map((cell, index) => ({ cell, index }))
                .filter(({ cell }) => cell.type === 'cheese' && !cell.revealed);

            if (unrevealedCheese.length ===