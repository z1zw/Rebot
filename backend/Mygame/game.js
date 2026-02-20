// cheese.js - Cheese class
class Cheese {
    constructor(x, y, size = 20) {
        this.x = x;
        this.y = y;
        this.size = size;
        this.collected = false;
    }

    draw(ctx) {
        if (this.collected) return;
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#8B4513';
        for (let i = 0; i < 4; i++) {
            const angle = (Math.PI / 2) * i;
            const holeX = this.x + Math.cos(angle) * (this.size * 0.5);
            const holeY = this.y + Math.sin(angle) * (this.size * 0.5);
            ctx.beginPath();
            ctx.arc(holeX, holeY, this.size * 0.2, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    checkCollision(mouse) {
        if (this.collected) return false;
        const dx = this.x - mouse.x;
        const dy = this.y - mouse.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        return distance < (this.size + mouse.size);
    }
}

// mouse.js - Mouse class
class Mouse {
    constructor(x, y, size = 15) {
        this.x = x;
        this.y = y;
        this.size = size;
        this.speed = 5;
        this.color = '#8B4513';
        this.tailLength = 10;
        this.tail = [];
    }

    update(keys) {
        // Save tail
        this.tail.unshift({ x: this.x, y: this.y });
        if (this.tail.length > this.tailLength) this.tail.pop();

        // Movement
        if (keys['ArrowUp'] || keys['w']) this.y -= this.speed;
        if (keys['ArrowDown'] || keys['s']) this.y += this.speed;
        if (keys['ArrowLeft'] || keys['a']) this.x -= this.speed;
        if (keys['ArrowRight'] || keys['d']) this.x += this.speed;

        // Boundary check
        const canvas = document.getElementById('gameCanvas');
        if (canvas) {
            this.x = Math.max(this.size, Math.min(canvas.width - this.size, this.x));
            this.y = Math.max(this.size, Math.min(canvas.height - this.size, this.y));
        }
    }

    draw(ctx) {
        // Draw tail
        ctx.strokeStyle = this.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.tail[0]?.x || this.x, this.tail[0]?.y || this.y);
        for (let i = 1; i < this.tail.length; i++) {
            ctx.lineTo(this.tail[i].x, this.tail[i].y);
        }
        ctx.stroke();

        // Draw mouse body
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();

        // Draw eyes
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.arc(this.x - this.size * 0.4, this.y - this.size * 0.4, this.size * 0.3, 0, Math.PI * 2);
        ctx.arc(this.x + this.size * 0.4, this.y - this.size * 0.4, this.size * 0.3, 0, Math.PI * 2);
        ctx.fill();

        // Draw ears
        ctx.fillStyle = '#A0522D';
        ctx.beginPath();
        ctx.arc(this.x - this.size * 0.6, this.y - this.size * 0.8, this.size * 0.5, 0, Math.PI * 2);
        ctx.arc(this.x + this.size * 0.6, this.y - this.size * 0.8, this.size * 0.5, 0, Math.PI * 2);
        ctx.fill();
    }
}

// obstacle.js - Obstacle class
class Obstacle {
    constructor(x, y, width, height, type = 'static') {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.type = type; // 'static' or 'moving'
        this.speed = type === 'moving' ? 2 : 0;
        this.direction = 1;
        this.color = type === 'moving' ? '#FF6B6B' : '#808080';
    }

    update() {
        if (this.type === 'moving') {
            this.x += this.speed * this.direction;
            if (this.x <= 0 || this.x + this.width >= (document.getElementById('gameCanvas')?.width || 800)) {
                this.direction *= -1;
            }
        }
    }

    draw(ctx) {
        ctx.fillStyle = this.color;
        ctx.fillRect(this.x, this.y, this.width, this.height);
        // Add pattern for static obstacles
        if (this.type === 'static') {
            ctx.fillStyle = '#606060';
            for (let i = 0; i < this.width; i += 10) {
                for (let j = 0; j < this.height; j += 10) {
                    if ((i + j) % 20 === 0) {
                        ctx.fillRect(this.x + i, this.y + j, 5, 5);
                    }
                }
            }
        }
    }

    checkCollision(mouse) {
        return mouse.x + mouse.size > this.x &&
               mouse.x - mouse.size < this.x + this.width &&
               mouse.y + mouse.size > this.y &&
               mouse.y - mouse.size < this.y + this.height;
    }
}

// game.js - Main game logic
class CheeseGame {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.mouse = new Mouse(50, 50);
        this.cheeses = [];
        this.obstacles = [];
        this.keys = {};
        this.score = 0;
        this.lives = 3;
        this.gameOver = false;
        this.gameWon = false;
        this.level = 1;
        this.maxLevel = 3;
        this.cheeseCount = 5;
        this.obstacleCount = 3;
        this.init();
        this.setupEventListeners();
        this.gameLoop();
    }

    init() {
        this.resizeCanvas();
        this.generateLevel();
    }

    resizeCanvas() {
        this.canvas.width = Math.min(800, window.innerWidth * 0.9);
        this.canvas.height = Math.min(500, window.innerHeight * 0.7);
    }

    generateLevel() {
        this.cheeses = [];
        this.obstacles = [];
        this.mouse.x = 50;
        this.mouse.y = 50;

        // Generate cheeses
        for (let i = 0; i < this.cheeseCount; i++) {
            let x, y, valid;
            do {
                valid = true;
                x = Math.random() * (this.canvas.width - 40) + 20;
                y = Math.random() * (this.canvas.height - 40) + 20;
                // Avoid spawning on mouse
                if (Math.abs(x - this.mouse.x) < 50 && Math.abs(y - this.mouse.y) < 50) valid = false;
                // Avoid spawning on other cheeses
                for (const cheese of this.cheeses) {
                    if (Math.abs(x - cheese.x) < 40 && Math.abs(y - cheese.y) < 40) valid = false;
                }
            } while (!valid);
            this.cheeses.push(new Cheese(x, y));
        }

        // Generate obstacles
        for (let i = 0; i < this.obstacleCount; i++) {
            const type = i === 0 ? 'moving' : 'static';
            const width = type === 'moving' ? 80 : Math.random() * 60 + 40;
            const height = type === 'moving' ? 20 : Math.random() * 60 + 40;
            let x, y, valid;
            do {
                valid = true;
                x = Math.random() * (this.canvas.width - width);
                y = Math.random() * (this.canvas.height - height);
                // Avoid spawning on mouse
                if (this.mouse.x + this.mouse.size > x && this.mouse.x - this.mouse.size < x + width &&
                    this.mouse.y + this.mouse.size > y && this.mouse.y - this.mouse.size < y + height) valid = false;
                // Avoid spawning on cheeses
                for (const cheese of this.cheeses) {
                    if (cheese.x + cheese.size > x && cheese.x - cheese.size < x + width &&
                        cheese.y + cheese.size > y && cheese.y - cheese.size < y + height) valid = false;
                }
                // Avoid overlapping other obstacles
                for (const obstacle of this.obstacles) {
                    if (x < obstacle.x + obstacle.width && x + width > obstacle.x &&
                        y < obstacle.y + obstacle.height && y + height > obstacle.y) valid = false;
                }
            } while (!valid);
            this.obstacles.push(new Obstacle(x, y, width, height, type));
        }
    }

    setupEventListeners() {
        window.addEventListener('keydown', (e) => {
            this.keys[e.key] = true;
        });
        window.addEventListener('keyup', (e) => {
            this.keys[e.key] = false;
        });
        window.addEventListener('resize', () => {
            this.resizeCanvas();
            this.generateLevel();
        });
        document.getElementById('restartButton').addEventListener('click', () => this.restart());
    }

    update() {
        if (this.gameOver || this.gameWon) return;

        this.mouse.update(this.keys);

        // Check cheese collision
        for (const cheese of this.cheeses) {
            if (cheese.checkCollision(this.mouse)) {
                cheese.collected = true;
                this.score += 10;
                if (this.cheeses.every(c => c.collected)) {
                    this.level++;
                    if (this.level > this.maxLevel) {
                        this.gameWon = true;
                    } else {
                        this.cheeseCount += 2;
                        this.obstacleCount += 1;
                        this.generateLevel();
                    }
                }
            }
        }

        // Check obstacle collision
        for (const obstacle of this.obstacles) {
            obstacle.update();
            if (obstacle.checkCollision(this.mouse)) {
                this.lives--;
                if (this.lives <= 0) {
                    this.gameOver = true;
                } else {
                    // Reset mouse position
                    this.mouse.x = 50;
                    this.mouse.y = 50;
                    this.mouse.tail = [];
                }
                break;
            }
        }
    }

    draw() {
        // Clear canvas
        this.ctx.fillStyle = '#F9F9FB';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw obstacles
        for (const obstacle of this.obstacles) {
            obstacle.draw(this.ctx);
        }

        // Draw cheeses
        for (const cheese of this.cheeses) {
            cheese.draw(this.ctx);
        }

        // Draw mouse
        this.mouse.draw(this.ctx);

        // Draw UI
        this.ctx.fillStyle = '#333';
        this.ctx.font = '16px sans-serif';
        this.ctx.fillText(`Score: ${this.score}`, 10, 25);
        this.ctx.fillText(`Lives: ${this.lives}`, 10, 50);
        this.ctx.fillText(`Level: ${this.level}/${this.maxLevel}`, 10, 75);

        // Game over / win messages
        if (this.gameOver) {
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#FFF';
            this.ctx.font = 'bold 36px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('Game Over!', this.canvas.width / 2, this.canvas.height / 2 - 30);
            this.ctx.font = '24px sans-serif';
            this.ctx.fillText(`Final Score: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2 + 20);
            this.ctx.textAlign = 'left';
        } else if (this.gameWon) {
            this.ctx.fillStyle = 'rgba(0, 100, 0, 0.7)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#FFF';
            this.ctx.font = 'bold 36px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('You Win!', this.canvas.width / 2, this.canvas.height / 2 - 30);
            this.ctx.font = '24px sans-serif';
            this.ctx.fillText(`Total Score: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2 + 20);
            this.ctx.textAlign = 'left';
        }
    }

    gameLoop() {
        this.update();
        this.draw();
        requestAnimationFrame(() => this.gameLoop());
    }

    restart() {
        this.score = 0;
        this.lives = 3;
        this.gameOver = false;
        this.gameWon = false;
        this.level = 1;
        this.cheeseCount = 5;
        this.obstacleCount = 3;
        this.generateLevel();
    }
}

// Initialize game when DOM is loaded
window.addEventListener('DOMContentLoaded', () => {
    new CheeseGame();
});