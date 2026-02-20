import 'package:flutter/material.dart';

class ScoreWidget extends StatelessWidget {
  final int currentScore;
  final int bestScore;
  final bool gameWon;
  final bool gameOver;
  final VoidCallback onNewGamePressed;

  const ScoreWidget({
    super.key,
    required this.currentScore,
    required this.bestScore,
    required this.gameWon,
    required this.gameOver,
    required this.onNewGamePressed,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      decoration: BoxDecoration(
        color: const Color(0xFFF9F9FB),
        borderRadius: BorderRadius.circular(12.0),
        border: Border.all(color: const Color(0xFFEAECF0), width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: _ScoreCard(
                  label: 'SCORE',
                  score: currentScore,
                  color: const Color(0xFF4A5568),
                ),
              ),
              const SizedBox(width: 12.0),
              Expanded(
                child: _ScoreCard(
                  label: 'BEST',
                  score: bestScore,
                  color: const Color(0xFF2D3748),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16.0),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: _GameStatusIndicator(
                  gameWon: gameWon,
                  gameOver: gameOver,
                ),
              ),
              const SizedBox(width: 12.0),
              Expanded(
                child: ElevatedButton(
                  onPressed: onNewGamePressed,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF3182CE),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12.0),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8.0),
                    ),
                    elevation: 0,
                  ),
                  child: const Text(
                    'New Game',
                    style: TextStyle(
                      fontSize: 14.0,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  final String label;
  final int score;
  final Color color;

  const _ScoreCard({
    required this.label,
    required this.score,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 12.0),
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F5),
        borderRadius: BorderRadius.circular(8.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 13.0,
              fontWeight: FontWeight.w500,
              color: Color(0xFF718096),
            ),
          ),
          const SizedBox(height: 4.0),
          Text(
            score.toString(),
            style: TextStyle(
              fontSize: 24.0,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _GameStatusIndicator extends StatelessWidget {
  final bool gameWon;
  final bool gameOver;

  const _GameStatusIndicator({
    required this.gameWon,
    required this.gameOver,
  });

  @override
  Widget build(BuildContext context) {
    String statusText = 'Playing';
    Color statusColor = const Color(0xFF38A169);

    if (gameWon) {
      statusText = 'You Win!';
      statusColor = const Color(0xFF3182CE);
    } else if (gameOver) {
      statusText = 'Game Over';
      statusColor = const Color(0xFFE53E3E);
    }

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 16.0),
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F5),
        borderRadius: BorderRadius.circular(8.0),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 10.0,
            height: 10.0,
            margin: const EdgeInsets.only(right: 8.0),
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
            ),
          ),
          Text(
            statusText,
            style: TextStyle(
              fontSize: 14.0,
              fontWeight: FontWeight.w600,
              color: statusColor,
            ),
          ),
        ],
      ),
    );
  }
}