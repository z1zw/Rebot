import 'dart:async';
import 'dart:math';
import 'game_state.dart';

class GameLogic {
  final GameState _gameState;
  Timer? _gameTimer;
  final Random _random = Random();
  final int _maxCheese = 10;
  final int _gameDurationSeconds = 30;

  GameLogic(this._gameState) {
    _gameState.gameDuration = _gameDurationSeconds;
  }

  void startGame() {
    if (_gameState.isGameActive) return;
    _gameState.reset();
    _gameState.isGameActive = true;
    _gameState.cheeses.clear();
    _spawnInitialCheese();
    _gameTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _updateGameTimer();
    });
  }

  void _spawnInitialCheese() {
    for (int i = 0; i < 5; i++) {
      _addRandomCheese();
    }
  }

  void _addRandomCheese() {
    if (_gameState.cheeses.length >= _maxCheese) return;
    double x = _random.nextDouble() * 0.8 + 0.1;
    double y = _random.nextDouble() * 0.7 + 0.15;
    _gameState.cheeses.add(Cheese(x, y));
  }

  void _updateGameTimer() {
    if (!_gameState.isGameActive) return;
    _gameState.timeRemaining--;
    if (_gameState.timeRemaining <= 0) {
      endGame();
    } else {
      if (_random.nextDouble() > 0.6 && _gameState.cheeses.length < _maxCheese) {
        _addRandomCheese();
      }
    }
  }

  void collectCheese(int index) {
    if (!_gameState.isGameActive) return;
    if (index >= 0 && index < _gameState.cheeses.length) {
      _gameState.cheeses.removeAt(index);
      _gameState.score += 10;
      _addRandomCheese();
    }
  }

  void endGame() {
    _gameState.isGameActive = false;
    _gameTimer?.cancel();
    _gameTimer = null;
  }

  void restartGame() {
    endGame();
    startGame();
  }

  void dispose() {
    _gameTimer?.cancel();
  }
}