// score.js - Score tracking and persistence for 2048 Game

class ScoreManager {
    constructor() {
        this.currentScore = 0;
        this.bestScore = this.loadBestScore();
        this.scoreDisplay = null;
        this.bestDisplay = null;
    }

    // Initialize score displays
    init(scoreElementId, bestElementId) {
        this.scoreDisplay = document.getElementById(scoreElementId);
        this.bestDisplay = document.getElementById(bestElementId);
        this.updateDisplays();
    }

    // Add points to current score
    add(points) {
        this.currentScore += points;
        this.updateDisplays();
        
        // Update best score if current exceeds it
        if (this.currentScore > this.bestScore) {
            this.bestScore = this.currentScore;
            this.saveBestScore();
        }
    }

    // Reset current score (keeps best)
    reset() {
        this.currentScore = 0;
        this.updateDisplays();
    }

    // Update both score displays
    updateDisplays() {
        if (this.scoreDisplay) {
            this.scoreDisplay.textContent = this.currentScore;
        }
        if (this.bestDisplay) {
            this.bestDisplay.textContent = this.bestScore;
        }
    }

    // Load best score from localStorage
    loadBestScore() {
        const saved = localStorage.getItem('2048_best_score');
        return saved ? parseInt(saved, 10) : 0;
    }

    // Save best score to localStorage
    saveBestScore() {
        localStorage.setItem('2048_best_score', this.bestScore.toString());
        this.updateDisplays();
    }

    // Clear best score (reset to 0)
    clearBestScore() {
        this.bestScore = 0;
        localStorage.removeItem('2048_best_score');
        this.updateDisplays();
    }

    // Get current score
    getCurrentScore() {
        return this.currentScore;
    }

    // Get best score
    getBestScore() {
        return this.bestScore;
    }
}

// Create and export a singleton instance
const scoreManager = new ScoreManager();

// For module systems (if used)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = scoreManager;
}