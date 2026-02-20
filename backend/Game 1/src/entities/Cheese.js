// src/entities/Cheese.js

/**
 * Cheese collectible entity for the Cheese Game
 * Handles animation, scoring, and collection logic
 */
class Cheese {
    /**
     * Create a new Cheese collectible
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {number} points - Points awarded when collected
     * @param {string} type - Type of cheese (affects appearance)
     */
    constructor(x, y, points = 100, type = 'cheddar') {
        this.x = x;
        this.y = y;
        this.width = 40;
        this.height = 30;
        this.points = points;
        this.type = type;
        this.collected = false;
        this.animationFrame = 0;
        this.animationSpeed = 0.15;
        this.rotation = 0;
        this.bounceOffset = 0;
        this.bounceSpeed = 0.05;
        this.bounceAmplitude = 5;
        this.collectAnimationProgress = 0;
        this.collectAnimationDuration = 20;
        
        // Visual properties based on cheese type
        this.colors = this.getCheeseColors();
        this.holes = this.generateHoles();
    }
    
    /**
     * Get color scheme based on cheese type
     * @returns {Object} Color configuration
     */
    getCheeseColors() {
        const colorSchemes = {
            cheddar: {
                primary: '#FFA726',
                secondary: '#FF9800',
                highlight: '#FFEB3B',
                shadow: '#F57C00'
            },
            gouda: {
                primary: '#FFCC80',
                secondary: '#FFB74D',
                highlight: '#FFF9C4',
                shadow: '#FFA726'
            },
            blue: {
                primary: '#90CAF9',
                secondary: '#64B5F6',
                highlight: '#E3F2FD',
                shadow: '#42A5F5'
            },
            swiss: {
                primary: '#FFF3E0',
                secondary: '#FFE0B2',
                highlight: '#FFFFFF',
                shadow: '#FFCC80'
            }
        };
        
        return colorSchemes[this.type] || colorSchemes.cheddar;
    }
    
    /**
     * Generate random holes for the cheese
     * @returns {Array} Array of hole objects
     */
    generateHoles() {
        const holes = [];
        const holeCount = this.type === 'swiss' ? 8 : 4;
        
        for (let i = 0; i < holeCount; i++) {
            holes.push({
                x: Math.random() * (this.width - 10) + 5,
                y: Math.random() * (this.height - 10) + 5,
                radius: Math.random() * 4 + 2
            });
        }
        
        return holes;
    }
    
    /**
     * Update cheese animation
     */
    update() {
        if (this.collected) {
            this.updateCollectAnimation();
            return;
        }
        
        // Update bounce animation
        this.animationFrame += this.animationSpeed;
        this.bounceOffset = Math.sin(this.animationFrame) * this.bounceAmplitude;
        
        // Update rotation
        this.rotation = Math.sin(this.animationFrame * 0.5) * 0.1;
    }
    
    /**
     * Update collection animation
     */
    updateCollectAnimation() {
        this.collectAnimationProgress++;
        
        if (this.collectAnimationProgress >= this.collectAnimationDuration) {
            // Animation complete
            return;
        }
        
        // Scale down and fade out during collection
        const progress = this.collectAnimationProgress / this.collectAnimationDuration;
        this.width = 40 * (1 - progress);
        this.height = 30 * (1 - progress);
        this.bounceOffset = 20 * progress;
    }
    
    /**
     * Draw the cheese
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     */
    draw(ctx) {
        if (this.collected && this.collectAnimationProgress >= this.collectAnimationDuration) {
            return;
        }
        
        ctx.save();
        
        // Position with bounce offset
        const drawX = this.x;
        const drawY = this.y + this.bounceOffset;
        
        // Apply rotation
        ctx.translate(drawX + this.width / 2, drawY + this.height / 2);
        ctx.rotate(this.rotation);
        ctx.translate(-(drawX + this.width / 2), -(drawY + this.height / 2));
        
        // Draw cheese body with gradient
        this.drawCheeseBody(ctx, drawX, drawY);
        
        // Draw cheese holes
        this.drawCheeseHoles(ctx, drawX, drawY);
        
        // Draw cheese rind
        this.drawCheeseRind(ctx, drawX, drawY);
        
        // Draw collection effect if being collected
        if (this.collected) {
            this.drawCollectEffect(ctx, drawX, drawY);
        }
        
        ctx.restore();
        
        // Draw points indicator when collected
        if (this.collected && this.collectAnimationProgress < this.collectAnimationDuration / 2) {
            this.drawPointsIndicator(ctx, drawX, drawY);
        }
    }
    
    /**
     * Draw cheese body with gradient
     */
    drawCheeseBody(ctx, x, y) {
        const gradient = ctx.createLinearGradient(
            x, y,
            x + this.width, y + this.height
        );
        
        gradient.addColorStop(0, this.colors.primary);
        gradient.addColorStop(0.5, this.colors.secondary);
        gradient.addColorStop(1, this.colors.shadow);
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 8);
        ctx.fill();
        
        // Add highlight
        ctx.fillStyle = this.colors.highlight;
        ctx.globalAlpha = 0.3;
        ctx.beginPath();
        ctx.roundRect(x + 2, y + 2, this.width - 4, 10, 4);
        ctx.fill();
        ctx.globalAlpha = 1;
    }
    
    /**
     * Draw cheese holes
     */
    drawCheeseHoles(ctx, x, y) {
        ctx.fillStyle = this.colors.shadow;
        ctx.globalAlpha = 0.7;
        
        this.holes.forEach(hole => {
            ctx.beginPath();
            ctx.arc(
                x + hole.x,
                y + hole.y,
                hole.radius,
                0,
                Math.PI * 2
            );
            ctx.fill();
        });
        
        ctx.globalAlpha = 1;
    }
    
    /**
     * Draw cheese rind
     */
    drawCheeseRind(ctx, x, y) {
        ctx.strokeStyle = this.colors.shadow;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 8);
        ctx.stroke();
    }
    
    /**
     * Draw collection effect
     */
    drawCollectEffect(ctx, x, y) {
        const progress = this.collectAnimationProgress / this.collectAnimationDuration;
        const centerX = x + this.width / 2;
        const centerY = y + this.height / 2;
        
        // Draw particle effect
        ctx.fillStyle = this.colors.highlight;
        ctx.globalAlpha = 1 - progress;
        
        for (let i = 0; i < 8; i++) {
            const angle = (i / 8) * Math.PI * 2;
            const distance = 20 * progress;
            const particleX = centerX + Math.cos(angle) * distance;
            const particleY = centerY + Math.sin(angle) * distance;
            
            ctx.beginPath();
            ctx.arc(particleX, particleY, 3 * (1 - progress), 0, Math.PI * 2);
            ctx.fill();
        }
        
        ctx.globalAlpha = 1;
    }
    
    /**
     * Draw points indicator
     */
    drawPointsIndicator(ctx, x, y) {
        const centerX = x + this.width / 2;
        const offsetY = -20 - (this.collectAnimationProgress * 2);
        
        ctx.fillStyle = '#4CAF50';
        ctx.font = 'bold 16px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;
        
        ctx.fillText(`+${this.points}`, centerX, y + offsetY);
        
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    }
    
    /**
     * Check if point is inside cheese
     * @param {number} px - Point X
     * @param {number} py - Point Y
     * @returns {boolean} True if point is inside
     */
    containsPoint(px, py) {
        if (this.collected) return false;
        
        const relativeX = px - this.x;
        const relativeY = py - this.y;
        
        // Check if point is within bounding box
        if (relativeX < 0 || relativeX > this.width ||
            relativeY < 0 || relativeY > this.height) {
            return false;
        }
        
        // Check if point is in a hole (not collectible)
        for (const hole of this.holes) {
            const distance = Math.sqrt(
                Math.pow(relativeX - hole.x, 2) +
                Math.pow(relativeY - hole.y, 2)
            );
            
            if (distance < hole.radius) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Collect the cheese
     * @returns {number} Points awarded
     */
    collect() {
        if (this.collected) return 0;
        
        this.collected = true;
        this.collectAnimationProgress = 0;
        
        return this.points;
    }
    
    /**
     * Check if cheese collection animation is complete
     * @returns {boolean} True if animation is complete
     */
    isAnimationComplete() {
        return this.collected && 
               this.collectAnimationProgress >= this.collectAnimationDuration;
    }
    
    /**
     * Reset cheese to initial state
     */
    reset() {
        this.collected = false;
        this.animationFrame = 0;
        this.rotation = 0;
        this.bounceOffset = 0;
        this.collectAnimationProgress = 0;
        this.width = 40;
        this.height = 30;
        this.holes = this.generateHoles();
    }
    
    /**
     * Create a random cheese at position
     * @param {number} x - X position
     * @param {number} y - Y position
     * @returns {Cheese} New cheese instance
     */
    static createRandom(x, y) {
        const types = ['cheddar', 'gouda', 'blue', 'swiss'];
        const type = types[Math.floor(Math.random() * types.length)];
        
        // Different points based on type
        const pointsMap = {
            cheddar: 100,
            gouda: 150,
            blue: 200,
            swiss: 250
        };
        
        const points = pointsMap[type];
        
        return new Cheese(x, y, points, type);
    }
}

// Add roundRect method to CanvasRenderingContext2D if not exists
if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, width, height, radius) {
        if (width < 2 * radius) radius = width / 2;
        if (height < 2 * radius) radius = height / 2;
        
        this.beginPath();
        this.moveTo(x + radius, y);
        this.arcTo(x + width, y, x + width, y + height, radius);
        this.arcTo(x + width, y + height, x, y + height, radius);
        this.arcTo(x, y + height, x, y, radius);
        this.arcTo(x, y, x + width, y, radius);
        this.closePath();
        return this;
    };
}

export default Cheese;