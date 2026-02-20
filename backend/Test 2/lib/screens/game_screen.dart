import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/game_logic.dart';
import '../models/game_state.dart';
import '../widgets/cheese_widget.dart';
import '../widgets/timer_widget.dart';
import '../widgets/score_display.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({Key? key}) : super(key: key);

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> with SingleTickerProviderStateMixin {
  late GameLogic _gameLogic;
  late GameState _gameState;
  late AnimationController _animationController;
  final Duration _gameDuration = const Duration(seconds: 30);
  bool _isGameActive = false;
  bool _isGameOver = false;
  Timer? _gameTimer;

  @override
  void initState() {
    super.initState();
    _gameState = GameState();
    _gameLogic = GameLogic(_gameState);
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _startNewGame();
  }

  void _startNewGame() {
    setState(() {
      _gameLogic.startGame();
      _isGameActive = true;
      _isGameOver = false;
    });
  }

  void _onTimerTick() {
    if (mounted) {
      setState(() {});
    }
  }

  void _onGameOver() {
    if (mounted) {
      setState(() {
        _isGameActive = false;
        _isGameOver = true;
      });
    }
  }

  void _collectCheese(int index) {
    if (!_isGameActive || _isGameOver) return;
    setState(() {
      _gameLogic.collectCheese(index);
      _animationController.forward(from: 0.0);
    });
  }

  void _restartGame() {
    _gameLogic.restartGame();
    _startNewGame();
  }

  void _exitGame() {
    if (Navigator.canPop(context)) {
      Navigator.pop(context);
    } else {
      SystemNavigator.pop();
    }
  }

  @override
  void dispose() {
    _gameLogic.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final isLandscape = screenSize.width > screenSize.height;
    final double topPadding = MediaQuery.of(context).padding.top;

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9FB),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return Stack(
              children: [
                Column(
                  children: [
                    // Header with score and timer
                    Container(
                      padding: EdgeInsets.fromLTRB(16, 12 + topPadding, 16, 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.05),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          ScoreDisplay(currentScore: _gameState.score),
                          TimerWidget(
                            timeLeft: _gameState.timeRemaining,
                          ),
                        ],
                      ),
                    ),

                    // Game instructions
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
                      child: Text(
                        'Tap the cheeses to collect them!',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.grey[700],
                          fontWeight: FontWeight.w500,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),

                    // Game grid
                    Expanded(
                      child: Padding(
                        padding: EdgeInsets.symmetric(
                          horizontal: isLandscape ? 40 : 16,
                          vertical: isLandscape ? 20 : 8,
                        ),
                        child: GridView.builder(
                          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: isLandscape ? 5 : 3,
                            crossAxisSpacing: 16,
                            mainAxisSpacing: 16,
                            childAspectRatio: 1.0,
                          ),
                          itemCount: _gameState.cheeses.length,
                          itemBuilder: (context, index) {
                            final cheese = _gameState.cheeses[index];
                            return GestureDetector(
                              onTap: () => _collectCheese(index),
                              child: CheeseWidget(
                                cheesePosition: cheese,
                                animationController: _animationController,
                              ),
                            );
                          },
                        ),
                      ),
                    ),

                    // Game controls
                    Container(
                      padding: const EdgeInsets.all(24),
                      color: const Color(0xFFF2F2F5),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          ElevatedButton(
                            onPressed: _restartGame,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF4CAF50),
                              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: const Text(
                              'Restart',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ),
                          ElevatedButton(
                            onPressed: _exitGame,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFF44336),
                              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: const Text(
                              'Exit',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),

                // Game over overlay
                if (_isGameOver)
                  Positioned.fill(
                    child: Container(
                      color: Colors.black.withOpacity(0.7),
                      child: Center(
                        child: Container(
                          width: constraints.maxWidth * 0.8,
                          padding: const EdgeInsets.all(32),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.2),
                                blurRadius: 20,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'Game Over!',
                                style: TextStyle(
                                  fontSize: 28,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.grey[800],
                                ),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Final Score: ${_gameState.score}',
                                style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF4CAF50),
                                ),
                              ),
                              const SizedBox(height: 24),
                              ElevatedButton(
                                onPressed: _restartGame,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF2196F3),
                                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: const Text(
                                  'Play Again',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}