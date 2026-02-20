import 'package:flutter/material.dart';
import 'package:cheese_game/models/game_state.dart';
import 'package:cheese_game/widgets/cheese_button.dart';

class ScoreScreen extends StatefulWidget {
  final GameState gameState;
  final VoidCallback onRestart;

  const ScoreScreen({
    Key? key,
    required this.gameState,
    required this.onRestart,
  }) : super(key: key);

  @override
  State<ScoreScreen> createState() => _ScoreScreenState();
}

class _ScoreScreenState extends State<ScoreScreen> {
  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;
    final bool isSmallScreen = screenWidth < 600;

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9FB),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight,
                ),
                child: Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: isSmallScreen ? 20.0 : 40.0,
                    vertical: isSmallScreen ? 20.0 : 40.0,
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      SizedBox(height: isSmallScreen ? 20.0 : 40.0),
                      Text(
                        'Game Over!',
                        style: TextStyle(
                          fontSize: isSmallScreen ? 32.0 : 48.0,
                          fontWeight: FontWeight.bold,
                          color: Colors.deepOrange,
                        ),
                      ),
                      SizedBox(height: isSmallScreen ? 16.0 : 24.0),
                      Container(
                        padding: EdgeInsets.all(isSmallScreen ? 20.0 : 30.0),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF2F2F5),
                          borderRadius: BorderRadius.circular(20.0),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black12,
                              blurRadius: 10.0,
                              offset: Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          children: [
                            _buildScoreRow('Final Score:', widget.gameState.score),
                            SizedBox(height: isSmallScreen ? 12.0 : 16.0),
                            _buildScoreRow('Cheese Collected:', widget.gameState.cheeseCollected),
                            SizedBox(height: isSmallScreen ? 12.0 : 16.0),
                            _buildScoreRow('Time Played:', '${widget.gameState.timePlayed.inSeconds} sec'),
                            SizedBox(height: isSmallScreen ? 12.0 : 16.0),
                            _buildScoreRow('Level Reached:', '${widget.gameState.level}'),
                          ],
                        ),
                      ),
                      SizedBox(height: isSmallScreen ? 24.0 : 40.0),
                      Container(
                        padding: EdgeInsets.all(isSmallScreen ? 16.0 : 24.0),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEAECF0),
                          borderRadius: BorderRadius.circular(16.0),
                        ),
                        child: Column(
                          children: [
                            Text(
                              widget.gameState.isWin ? 'You Won! 🎉' : 'You Lost! 😢',
                              style: TextStyle(
                                fontSize: isSmallScreen ? 24.0 : 32.0,
                                fontWeight: FontWeight.w600,
                                color: widget.gameState.isWin ? Colors.green : Colors.red,
                              ),
                            ),
                            SizedBox(height: isSmallScreen ? 8.0 : 12.0),
                            Text(
                              widget.gameState.isWin
                                  ? 'Great job collecting all the cheese!'
                                  : 'Better luck next time!',
                              style: TextStyle(
                                fontSize: isSmallScreen ? 14.0 : 16.0,
                                color: Colors.grey[700],
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: isSmallScreen ? 32.0 : 48.0),
                      CheeseButton(
                        label: 'Play Again',
                        onPressed: widget.onRestart,
                        backgroundColor: Colors.deepOrange,
                        textColor: Colors.white,
                        isFullWidth: true,
                      ),
                      SizedBox(height: isSmallScreen ? 16.0 : 24.0),
                      CheeseButton(
                        label: 'Back to Menu',
                        onPressed: () {
                          Navigator.of(context).popUntil((route) => route.isFirst);
                        },
                        backgroundColor: Colors.grey[300]!,
                        textColor: Colors.grey[800]!,
                        isFullWidth: true,
                      ),
                      SizedBox(height: isSmallScreen ? 20.0 : 40.0),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildScoreRow(String label, dynamic value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 16.0,
            fontWeight: FontWeight.w500,
            color: Colors.grey[800],
          ),
        ),
        Text(
          value.toString(),
          style: TextStyle(
            fontSize: 18.0,
            fontWeight: FontWeight.bold,
            color: Colors.deepOrange,
          ),
        ),
      ],
    );
  }
}