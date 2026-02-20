import 'dart:math';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:cheese_game/models/game_state.dart';
import 'package:cheese_game/widgets/cheese_button.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GameState _gameState = GameState();
  bool _isGameActive = false;
  int _score = 0;
  int _timeLeft = 60;
  Timer? _gameTimer;
  Timer? _countdownTimer;
  final List<Offset> _cheesePositions = [];
  final Random _random = Random();
  final int _maxCheese = 10;
  final double _cheeseSize = 60.0;

  @override
  void initState() {
    super.initState();
    _gameState.reset();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
  }

  @override
  void dispose() {
    _gameTimer?.cancel();
    _countdownTimer?.cancel();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.landscapeRight,
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
    super.dispose();
  }

  void _startGame() {
    if (_isGameActive) return;
    setState(() {
      _isGameActive = true;
      _score = 0;
      _timeLeft = 60;
      _cheesePositions.clear();
      _gameState.reset();
      _gameState.isPlaying = true;
    });
    _generateCheese();
    _gameTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) {
      if (!_isGameActive) {
        timer.cancel();
        return;
      }
      _updateCheesePositions();
    });
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!_isGameActive) {
        timer.cancel();
        return;
      }
      setState(() {
        _timeLeft--;
      });
      if (_timeLeft <= 0) {
        _endGame();
        timer.cancel();
      }
    });
  }

  void _generateCheese() {
    if (_cheesePositions.length >= _maxCheese || !_isGameActive) return;
    setState(() {
      final double x = _random.nextDouble() * 0.8 + 0.1;
      final double y = _random.nextDouble() * 0.7 + 0.15;
      _cheesePositions.add(Offset(x, y));
    });
  }

  void _updateCheesePositions() {
    if (!_isGameActive) return;
    setState(() {
      if (_cheesePositions.length < _maxCheese && _random.nextDouble() > 0.5) {
        _generateCheese();
      }
    });
  }

  void _tapCheese(int index) {
    if (!_isGameActive) return;
    setState(() {
      _cheesePositions.removeAt(index);
      _score += 10;
      _gameState.score = _score;
      if (_score >= 100) {
        _endGame();
      }
    });
    _generateCheese();
  }

  void _endGame() {
    if (!_isGameActive) return;
    setState(() {
      _isGameActive = false;
      _gameState.isPlaying = false;
      _gameState.score = _score;
      _cheesePositions.clear();
    });
    _gameTimer?.cancel();
    _countdownTimer?.cancel();
    _showGameOverDialog();
  }

  void _showGameOverDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFFF9F9FB),
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: Text(
            _score >= 100 ? 'You Win!' : 'Time\'s Up!',
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Color(0xFF2D3748),
            ),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Your Score: $_score',
                style: const TextStyle(
                  fontSize: 18,
                  color: Color(0xFF4A5568),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _score >= 100
                    ? 'Great job collecting all the cheese!'
                    : 'Try again to collect more cheese!',
                style: const TextStyle(
                  fontSize: 16,
                  color: Color(0xFF718096),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _startGame();
              },
              child: const Text(
                'Play Again',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFF3182CE),
                ),
              ),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: const Text(
                'Close',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFF718096),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  void _showInstructions() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFFF9F9FB),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (BuildContext context) {
        return Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'How to Play',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3748),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                '• Tap on cheese pieces to collect them.\n'
                '• Each cheese gives you 10 points.\n'
                '• You have 60 seconds to collect as much cheese as possible.\n'
                '• Win by reaching 100 points before time runs out.\n'
                '• Cheese will randomly appear on screen.',
                style: TextStyle(
                  fontSize: 16,
                  height: 1.5,
                  color: Color(0xFF4A5568),
                ),
              ),
              const SizedBox(height: 24),
              Center(
                child: CheeseButton(
                  label: 'Got it!',
                  onPressed: () {
                    Navigator.of(context).pop();
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F2F5),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final bool isLarge = constraints.maxWidth > 600;
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.symmetric(
                horizontal: isLarge ? 40.0 : 20.0,
                vertical: isLarge ? 30.0 : 20.0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 20),
                  Text(
                    'Cheese Collector',
                    style: TextStyle(
                      fontSize: isLarge ? 42 : 32,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF2D3748),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tap the cheese before time runs out!',
                    style: TextStyle(
                      fontSize: isLarge ? 18 : 16,
                      color: const Color(0xFF718096),
                    ),
                  ),
                  const SizedBox(height: 40),
                  Expanded(
                    child: Container(
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9F9FB),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: const Color(0xFFEAECF0),
                          width: 1,
                        ),
                      ),
                      child: Stack(
                        children: [
                          if (_isGameActive)
                            ..._cheesePositions.asMap().entries.map((entry) {
                              final int index = entry.key;
                              final Offset position = entry.value;
                              return Positioned(
                                left: position.dx *
                                    (constraints.maxWidth -
                                        (isLarge ? 80 : 40) -
                                        _cheeseSize),
                                top: position.dy *
                                    (constraints.maxHeight - 200 - _cheeseSize),
                                child: GestureDetector(
                                  onTap: () => _tapCheese(index),
                                  child: Container(
                                    width: _cheeseSize,
                                    height: _cheeseSize,
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFFFD700),
                                      borderRadius: BorderRadius.circular(30),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.amber.withOpacity(0.4),
                                          blurRadius: 8,
                                          offset: const Offset(0, 4),
                                        ),
                                      ],
                                    ),
                                    child: const Icon(
                                      Icons.emoji_food_beverage,
                                      size: 40,
                                      color: Color(0xFFD97706),
                                    ),
                                  ),
                                ),
                              );
                            }).toList(),
                          if (!_isGameActive)
                            Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.emoji_food_beverage,
                                    size: isLarge ? 120 : 80,
                                    color: const Color(0xFFD97706),
                                  ),
                                  const SizedBox(height: 20),
                                  Text(
                                    'Ready to collect cheese?',
                                    style: TextStyle(
                                      fontSize: isLarge ? 24 : 20,
                                      color: const Color(0xFF4A5568),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 30),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Score',
                            style: TextStyle(
                              fontSize: isLarge ? 18 : 16,
                              color: const Color(0xFF718096),
                            ),
                          ),
                          Text(
                            '$_score',
                            style: TextStyle(
                              fontSize: isLarge ? 32 : 28,
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF2D3748),
                            ),
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            'Time Left',
                            style: TextStyle(
                              fontSize: isLarge ? 18 : 16,
                              color: const Color(0xFF718096),
                            ),
                          ),
                          Text(
                            '$_timeLeft s',
                            style: TextStyle(
                              fontSize: isLarge ? 32 : 28,
                              fontWeight: FontWeight.bold,
                              color: _timeLeft <= 10
                                  ? const Color(0xFFE53E3E)
                                  : const Color(0xFF2D3748),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 30),
                  if (!_isGameActive)
                    CheeseButton(
                      label: 'Start Game',
                      onPressed: _startGame,
                    ),
                  if (_isGameActive)
                    CheeseButton(
                      label: 'End Game',
                      onPressed: _endGame,
                      backgroundColor: const Color(0xFFE53E3E),
                    ),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: _showInstructions,
                    child: Text(
                      'View Instructions',
                      style: TextStyle(
                        fontSize: isLarge ? 16 : 14,
                        color: const Color(0xFF3182CE),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}