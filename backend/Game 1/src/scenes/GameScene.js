import Player from '../entities/Player.js';
import Cheese from '../entities/Cheese.js';
import ScoreDisplay from '../ui/ScoreDisplay.js';

export default class GameScene {
    constructor(game) {
        this.game = game;
        this.canvas = game.canvas;
        this.ctx = game.ctx;
        this.player = null;
        this.cheeses = [];
        this.scoreDisplay = null;
        this.score = 0;
        this.keys = {};
        this.spawnInterval = null;
        this.gameRunning = false;
        this.init();
    }

    init() {
        this.player = new Player(this.canvas.width / 2, this.canvas.height / 2);
        this.scoreDisplay = new ScoreDisplay(this.ctx, this.canvas.width);
        this.setupEventListeners();
        this.startSpawning();
        this.gameRunning = true;
        this.gameLoop();
    }

    setupEventListeners() {
        window.addEventListener('keydown', (e) => {
            this.keys[e.key.toLowerCase()] = true;
        });
        window.addEventListener('keyup', (e) => {
            this.keys[e.key.toLowerCase()] = false;
        });
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.handleTouch(touch.clientX, touch.clientY);
        });
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.handleTouch(touch.clientX, touch.clientY);
        });
    }

    handleTouch(x, y) {
        const rect = this.canvas.getBoundingClientRect();
        const touchX = x - rect.left;
        const touchY = y - rect.top;
        this.player.moveTowards(touchX, touchY);
    }

    startSpawning() {
        this.spawnCheese();
        this.spawnInterval = setInterval(() => {
            if (this.gameRunning) {
                this.spawnCheese();
            }
        }, 1500);
    }

    spawnCheese() {
        if (this.cheeses.length >= 10) return;
        const x = Math.random() * (this.canvas.width - 40) + 20;
        const y = Math.random() * (this.canvas.height - 40) + 20;
        this.cheeses.push(new Cheese(x, y));
    }

    handleInput() {
        const speed = 5;
        if (this.keys['w'] || this.keys['arrowup']) this.player.y -= speed;
        if (this.keys['s'] || this.keys['arrowdown']) this.player.y += speed;
        if (this.keys['a'] || this.keys['arrowleft']) this.player.x -= speed;
        if (this.keys['d'] || this.keys['arrowright']) this.player.x += speed;

        this.player.x = Math.max(20, Math.min(this.canvas.width - 20, this.player.x));
        this.player.y = Math.max(20, Math.min(this.canvas.height - 20, this.player.y));
    }

    checkCollisions() {
        for (let i = this.cheeses.length - 1; i >= 0; i--) {
            const cheese = this.cheeses[i];
            const dx = this.player.x - cheese.x;
            const dy = this.player.y - cheese.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < this.player.radius + cheese.radius) {
                this.cheeses.splice(i, 1);
                this.score += 10;
                this.scoreDisplay.updateScore(this.score);
            }
        }
    }

    update() {
        if (!this.gameRunning) return;
        this.handleInput();
        this.checkCollisions();
        this.cheeses.forEach(cheese => cheese.update());
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.cheeses.forEach(cheese => cheese.draw(this.ctx));
        this.player.draw(this.ctx);
        this.scoreDisplay.draw();
    }

    gameLoop() {
        this.update();
        this.draw();
        if (this.gameRunning) {
            requestAnimationFrame(() => this.gameLoop());
        }
    }

    stop() {
        this.gameRunning = false;
        clearInterval(this.spawnInterval);
        window.removeEventListener('keydown', this.keys);
        window.removeEventListener('keyup', this.keys);
    }

    resize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
        this.scoreDisplay.updatePosition(width);
        this.player.x = Math.min(this.player.x, width - 20);
        this.player.y = Math.min(this.player.y, height - 20);
    }
}