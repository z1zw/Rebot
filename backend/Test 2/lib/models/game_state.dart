import 'dart:async';

class GameState {
  int score;
  int timeLeft;
  bool isPlaying;
  bool isGameOver;
  int totalCheeseCollected;
  int highScore;
  Timer? gameTimer;

  GameState({
    this.score = 0,
    this.timeLeft = 60,
    this.isPlaying = false,
    this.isGameOver = false,
    this.totalCheeseCollected = 0,
    this.highScore = 0,
  });

  void startGame() {
    if (isPlaying) return;
    score = 0;
    timeLeft = 60;
    isPlaying = true;
    isGameOver = false;
    totalCheeseCollected = 0;
    gameTimer?.cancel();
    gameTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (timeLeft > 0) {
        timeLeft--;
      } else {
        endGame();
        timer.cancel();
      }
    });
  }

  void collectCheese(int points) {
    if (!isPlaying || isGameOver) return;
    score += points;
    totalCheeseCollected++;
    if (score > highScore) {
      highScore = score;
    }
  }

  void endGame() {
    isPlaying = false;
    isGameOver = true;
    gameTimer?.cancel();
    gameTimer = null;
  }

  void restartGame() {
    gameTimer?.cancel();
    gameTimer = null;
    score = 0;
    timeLeft = 60;
    isPlaying = false;
    isGameOver = false;
    totalCheeseCollected = 0;
  }

  void dispose() {
    gameTimer?.cancel();
    gameTimer = null;
  }
}