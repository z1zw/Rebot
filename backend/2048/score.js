// score.js - Score tracking and best score persistence for 2048 Game

class ScoreManager {
    constructor() {
        this.currentScore = 0;
        this.bestScore = this.loadBestScore();
    }

    // Load best score from localStorage
    loadBestScore() {
        const savedBest = localStorage.getItem('2048-best-score');
        return savedBest ? parseInt(savedBest, 10) : 0;
    }

    // Save best score to localStorage
    saveBestScore() {
        localStorage.setItem('2048-best-score', this.bestScore.toString());
    }

    // Add points to current score
    add(points) {
        this.currentScore += points;
        
        // Update best score if current exceeds it
        if (this.currentScore > this.bestScore) {
            this.bestScore = this.currentScore;
            this.saveBestScore();
        }
        
        return this.currentScore;
    }

    // Reset current score (keeps best score)
    reset() {
        this.currentScore = 0;
        return this.currentScore;
    }

    // Reset everything including best score
    resetAll() {
        this.currentScore = 0;
        this.bestScore = 0;
        localStorage.removeItem('2048-best-score');
        return { current: this.currentScore, best: this.bestScore };
    }

    // Get current score
    getCurrent() {
        return this.currentScore;
    }

    // Get best score
    getBest() {
        return this.bestScore;
    }

    // Update best score from external source (e.g., if loaded from another device)
    updateBestScore(newBest) {
        if (newBest > this.bestScore) {
            this.bestScore = newBest;
            this.saveBestScore();
        }
        return this.bestScore;
    }

    // Export scores as object
    exportScores() {
        return {
            current: this.currentScore,
            best: this.bestScore
        };
    }
}

// Create and export a singleton instance
const scoreManager = new ScoreManager();

// For module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = scoreManager;
}