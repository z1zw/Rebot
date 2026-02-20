import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'game_logic.dart';
import 'tile_widget.dart';
import 'score_widget.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  final GameLogic _gameLogic = GameLogic();
  late FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode();
    _focusNode.requestFocus();
    _gameLogic.startGame();
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  void _handleKeyEvent(RawKeyEvent event) {
    if (event is RawKeyDownEvent) {
      switch (event.logicalKey) {
        case LogicalKeyboardKey.arrowUp:
          _move(Direction.up);
          break;
        case LogicalKeyboardKey.arrowDown:
          _move(Direction.down);
          break;
        case LogicalKeyboardKey.arrowLeft:
          _move(Direction.left);
          break;
        case LogicalKeyboardKey.arrowRight:
          _move(Direction.right);
          break;
        case LogicalKeyboardKey.keyR:
          if (event.isControlPressed || event.isMetaPressed) {
            _restartGame();
          }
          break;
        default:
          break;
      }
    }
  }

  void _move(Direction direction) {
    if (_gameLogic.gameOver || _gameLogic.won) return;
    setState(() {
      _gameLogic.move(direction);
    });
  }

  void _restartGame() {
    setState(() {
      _gameLogic.startGame();
    });
  }

  void _showGameOverDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Game Over'),
          content: Text('Your score: ${_gameLogic.score}'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _restartGame();
              },
              child: const Text('Restart'),
            ),
          ],
        );
      },
    );
  }

  void _showWinDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('You Win!'),
          content: Text('You reached 2048! Score: ${_gameLogic.score}'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _gameLogic.continueAfterWin();
                setState(() {});
              },
              child: const Text('Continue'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _restartGame();
              },
              child: const Text('Restart'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_gameLogic.gameOver) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showGameOverDialog();
      });
    }
    if (_gameLogic.won && !_gameLogic.continuedAfterWin) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showWinDialog();
      });
    }

    return RawKeyboardListener(
      focusNode: _focusNode,
      onKey: _handleKeyEvent,
      child: Scaffold(
        backgroundColor: const Color(0xFFF9F9FB),
        body: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final bool isPortrait = constraints.maxHeight > constraints.maxWidth;
              final double padding = isPortrait ? 16.0 : 32.0;
              final double boardSize = isPortrait
                  ? constraints.maxWidth - 2 * padding
                  : constraints.maxHeight - 2 * padding;

              return SingleChildScrollView(
                child: Padding(
                  padding: EdgeInsets.all(padding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      const SizedBox(height: 16),
                      Text(
                        '2048',
                        style: TextStyle(
                          fontSize: 48,
                          fontWeight: FontWeight.bold,
                          color: Colors.brown[700],
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Use arrow keys or swipe to move',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                        ),
                      ),
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          ScoreWidget(
                            label: 'SCORE',
                            value: _gameLogic.score,
                          ),
                          ScoreWidget(
                            label: 'BEST',
                            value: _gameLogic.bestScore,
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      GestureDetector(
                        onVerticalDragUpdate: (details) {
                          if (details.delta.dy < -10) {
                            _move(Direction.up);
                          } else if (details.delta.dy > 10) {
                            _move(Direction.down);
                          }
                        },
                        onHorizontalDragUpdate: (details) {
                          if (details.delta.dx < -10) {
                            _move(Direction.left);
                          } else if (details.delta.dx > 10) {
                            _move(Direction.right);
                          }
                        },
                        child: Container(
                          width: boardSize,
                          height: boardSize,
                          decoration: BoxDecoration(
                            color: const Color(0xFFBBADA0),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Stack(
                            children: [
                              GridView.builder(
                                physics: const NeverScrollableScrollPhysics(),
                                padding: const EdgeInsets.all(8),
                                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 4,
                                  crossAxisSpacing: 8,
                                  mainAxisSpacing: 8,
                                ),
                                itemCount: 16,
                                itemBuilder: (context, index) {
                                  return Container(
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFCDC1B4),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                  );
                                },
                              ),
                              for (var tile in _gameLogic.tiles)
                                Positioned(
                                  left: (tile.x * (boardSize / 4)) + 8,
                                  top: (tile.y * (boardSize / 4)) + 8,
                                  child: TileWidget(
                                    value: tile.value,
                                    size: (boardSize - 32) / 4,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 32),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          ElevatedButton.icon(
                            onPressed: _restartGame,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Restart Game'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.brown[600],
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                            ),
                          ),
                          const SizedBox(width: 16),
                          OutlinedButton.icon(
                            onPressed: () {
                              showDialog(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('How to Play'),
                                  content: const Text(
                                    '• Use arrow keys or swipe to move tiles.\n'
                                    '• When two tiles with the same number touch, they merge into one.\n'
                                    '• After each move, a new tile (2 or 4) appears.\n'
                                    '• Reach the 2048 tile to win!\n'
                                    '• Game ends when no moves are possible.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(context),
                                      child: const Text('OK'),
                                    ),
                                  ],
                                ),
                              );
                            },
                            icon: const Icon(Icons.help_outline),
                            label: const Text('How to Play'),
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Press R to restart • Arrow keys to move',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.grey[500],
                        ),
                      ),
                      if (_gameLogic.won && _gameLogic.continuedAfterWin)
                        Padding(
                          padding: const EdgeInsets.only(top: 16),
                          child: Text(
                            'You reached 2048! Keep going...',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.green[700],
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}