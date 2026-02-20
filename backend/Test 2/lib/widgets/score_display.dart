import 'package:flutter/material.dart';
import 'package:cheese_game/models/game_state.dart';

class ScoreDisplay extends StatelessWidget {
  final GameState gameState;

  const ScoreDisplay({
    Key? key,
    required this.gameState,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isSmallScreen = constraints.maxWidth < 600;
        final double iconSize = isSmallScreen ? 20.0 : 24.0;
        final double fontSizeLabel = isSmallScreen ? 14.0 : 16.0;
        final double fontSizeValue = isSmallScreen ? 18.0 : 20.0;
        final EdgeInsets padding = isSmallScreen
            ? const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0)
            : const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0);

        return Container(
          padding: padding,
          decoration: BoxDecoration(
            color: const Color(0xFFF9F9FB),
            borderRadius: BorderRadius.circular(12.0),
            border: Border.all(color: const Color(0xFFEAECF0), width: 1.0),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.emoji_food_beverage,
                color: Colors.orange[700],
                size: iconSize,
              ),
              SizedBox(width: isSmallScreen ? 6.0 : 8.0),
              Text(
                'Cheese:',
                style: TextStyle(
                  fontSize: fontSizeLabel,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey[800],
                ),
              ),
              SizedBox(width: isSmallScreen ? 2.0 : 4.0),
              Text(
                '${gameState.cheeseCount}',
                style: TextStyle(
                  fontSize: fontSizeValue,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFFD35400),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}