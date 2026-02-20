import 'dart:math';

class Game2048 {
  static const int boardSize = 4;
  List<List<int>> board;
  int score;
  int bestScore;
  bool gameOver;
  bool gameWon;
  Random random;

  Game2048()
      : board = List.generate(boardSize, (_) => List.filled(boardSize, 0)),
        score = 0,
        bestScore = 0,
        gameOver = false,
        gameWon = false,
        random = Random() {
    _addNewTile();
    _addNewTile();
  }

  void _addNewTile() {
    List<Point<int>> emptyCells = [];
    for (int i = 0; i < boardSize; i++) {
      for (int j = 0; j < boardSize; j++) {
        if (board[i][j] == 0) {
          emptyCells.add(Point(i, j));
        }
      }
    }
    if (emptyCells.isNotEmpty) {
      Point<int> cell = emptyCells[random.nextInt(emptyCells.length)];
      board[cell.x][cell.y] = random.nextDouble() < 0.9 ? 2 : 4;
    }
  }

  bool _moveLeft() {
    bool moved = false;
    for (int i = 0; i < boardSize; i++) {
      List<int> row = board[i];
      List<int> newRow = List.filled(boardSize, 0);
      int index = 0;
      for (int j = 0; j < boardSize; j++) {
        if (row[j] != 0) {
          if (index > 0 && newRow[index - 1] == row[j]) {
            newRow[index - 1] *= 2;
            score += newRow[index - 1];
            moved = true;
          } else {
            newRow[index] = row[j];
            if (index != j) moved = true;
            index++;
          }
        }
      }
      board[i] = newRow;
    }
    return moved;
  }

  bool _moveRight() {
    bool moved = false;
    for (int i = 0; i < boardSize; i++) {
      List<int> row = board[i];
      List<int> newRow = List.filled(boardSize, 0);
      int index = boardSize - 1;
      for (int j = boardSize - 1; j >= 0; j--) {
        if (row[j] != 0) {
          if (index < boardSize - 1 && newRow[index + 1] == row[j]) {
            newRow[index + 1] *= 2;
            score += newRow[index + 1];
            moved = true;
          } else {
            newRow[index] = row[j];
            if (index != j) moved = true;
            index--;
          }
        }
      }
      board[i] = newRow;
    }
    return moved;
  }

  bool _moveUp() {
    bool moved = false;
    for (int j = 0; j < boardSize; j++) {
      List<int> column = List.generate(boardSize, (i) => board[i][j]);
      List<int> newColumn = List.filled(boardSize, 0);
      int index = 0;
      for (int i = 0; i < boardSize; i++) {
        if (column[i] != 0) {
          if (index > 0 && newColumn[index - 1] == column[i]) {
            newColumn[index - 1] *= 2;
            score += newColumn[index - 1];
            moved = true;
          } else {
            newColumn[index] = column[i];
            if (index != i) moved = true;
            index++;
          }
        }
      }
      for (int i = 0; i < boardSize; i++) {
        board[i][j] = newColumn[i];
      }
    }
    return moved;
  }

  bool _moveDown() {
    bool moved = false;
    for (int j = 0; j < boardSize; j++) {
      List<int> column = List.generate(boardSize, (i) => board[i][j]);
      List<int> newColumn = List.filled(boardSize, 0);
      int index = boardSize - 1;
      for (int i = boardSize - 1; i >= 0; i--) {
        if (column[i] != 0) {
          if (index < boardSize - 1 && newColumn[index + 1] == column[i]) {
            newColumn[index + 1] *= 2;
            score += newColumn[index + 1];
            moved = true;
          } else {
            newColumn[index] = column[i];
            if (index != i) moved = true;
            index--;
          }
        }
      }
      for (int i = 0; i < boardSize; i++) {
        board[i][j] = newColumn[i];
      }
    }
    return moved;
  }

  void move(Direction direction) {
    if (gameOver || gameWon) return;
    bool moved = false;
    switch (direction) {
      case Direction.left:
        moved = _moveLeft();
        break;
      case Direction.right:
        moved = _moveRight();
        break;
      case Direction.up:
        moved = _moveUp();
        break;
      case Direction.down:
        moved = _moveDown();
        break;
    }
    if (moved) {
      _addNewTile();
      _checkGameState();
      if (score > bestScore) {
        bestScore = score;
      }
    }
  }

  void _checkGameState() {
    // Check for win
    for (int i = 0; i < boardSize; i++) {
      for (int j = 0; j < boardSize; j++) {
        if (board[i][j] == 2048) {
          gameWon = true;
          return;
        }
      }
    }
    // Check for game over (no empty cells and no possible merges)
    bool hasEmpty = false;
    bool canMerge = false;
    for (int i = 0; i < boardSize; i++) {
      for (int j = 0; j < boardSize; j++) {
        if (board[i][j] == 0) {
          hasEmpty = true;
        }
        if (i < boardSize - 1 && board[i][j] == board[i + 1][j]) {
          canMerge = true;
        }
        if (j < boardSize - 1 && board[i][j] == board[i][j + 1]) {
          canMerge = true;
        }
      }
    }
    gameOver = !hasEmpty && !canMerge;
  }

  void restart() {
    board = List.generate(boardSize, (_) => List.filled(boardSize, 0));
    score = 0;
    gameOver = false;
    gameWon = false;
    _addNewTile();
    _addNewTile();
  }

  List<List<int>> getBoard() => board;
  int getScore() => score;
  int getBestScore() => bestScore;
  bool isGameOver() => gameOver;
  bool isGameWon() => gameWon;
}

enum Direction { left, right, up, down }