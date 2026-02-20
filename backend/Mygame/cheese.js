// cheese.js - Cheese object definition with properties, rendering, and collection logic

class Cheese {
    constructor(x, y, radius = 15, points = 10) {
        this.x = x;
        this.y = y;
        this.radius = radius;
        this.points = points;
        this.collected = false;
        this.color = '#FFD700'; // Gold color for cheese
        this.highlightColor = '#FFEC8B';
        this.pulse = 0;
        this.pulseSpeed = 0.05;
        this.pulseMax = 5;
    }

    update() {
        // Pulsing animation
        this.pulse += this.pulseSpeed;
        if (this.pulse > Math.PI * 2) {
            this.pulse = 0;
        }
    }

    draw(ctx) {
        if (this.collected) return;

        const pulseOffset = Math.sin(this.pulse) * this.pulseMax;
        const currentRadius = this.radius + pulseOffset;

        // Draw cheese circle
        ctx.beginPath();
        ctx.arc(this.x, this.y, currentRadius, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
        ctx.strokeStyle = this.highlightColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw cheese holes
        ctx.fillStyle = '#DAA520';
        // Hole 1
        ctx.beginPath();
        ctx.arc(this.x - currentRadius * 0.4, this.y - currentRadius * 0.3, currentRadius * 0.2, 0, Math.PI * 2);
        ctx.fill();
        // Hole 2
        ctx.beginPath();
        ctx.arc(this.x + currentRadius * 0.3, this.y + currentRadius * 0.2, currentRadius * 0.15, 0, Math.PI * 2);
        ctx.fill();
        // Hole 3
        ctx.beginPath();
        ctx.arc(this.x + currentRadius * 0.1, this.y - currentRadius * 0.4, currentRadius * 0.18, 0, Math.PI * 2);
        ctx.fill();
    }

    isPointInside(px, py) {
        if (this.collected) return false;
        const dx = px - this.x;
        const dy = py - this.y;
        return dx * dx + dy * dy <= this.radius * this.radius;
    }

    collect() {
        if (!this.collected) {
            this.collected = true;
            return this.points;
        }
        return 0;
    }

    reset() {
        this.collected = false;
        this.pulse = 0;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Cheese;
}