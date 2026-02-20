import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/game_state.dart';

class TimerWidget extends StatefulWidget {
  const TimerWidget({Key? key}) : super(key: key);

  @override
  State<TimerWidget> createState() => _TimerWidgetState();
}

class _TimerWidgetState extends State<TimerWidget> {
  @override
  Widget build(BuildContext context) {
    final gameState = Provider.of<GameState>(context, listen: true);
    final remainingSeconds = gameState.remainingTime.inSeconds;
    final isRunning = gameState.isRunning;
    final isGameOver = gameState.isGameOver;

    Color timerColor = Colors.green;
    if (remainingSeconds <= 10) {
      timerColor = Colors.red;
    } else if (remainingSeconds <= 20) {
      timerColor = Colors.orange;
    }

    String timerText = isGameOver
        ? 'Game Over'
        : isRunning
            ? '${remainingSeconds ~/ 60}:${(remainingSeconds % 60).toString().padLeft(2, '0')}'
            : 'Tap to Start';

    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isSmallScreen = constraints.maxWidth < 400;
        final double paddingHorizontal = isSmallScreen ? 16 : 20;
        final double paddingVertical = isSmallScreen ? 10 : 12;
        final double iconSize = isSmallScreen ? 18 : 20;
        final double fontSize = isSmallScreen ? 14 : 16;
        final double spacing = isSmallScreen ? 8 : 10;
        final double borderRadius = isSmallScreen ? 12 : 16;

        return GestureDetector(
          onTap: () {
            if (!isRunning && !isGameOver) {
              gameState.startGame();
            }
          },
          child: Container(
            padding: EdgeInsets.symmetric(
              horizontal: paddingHorizontal,
              vertical: paddingVertical,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFF9F9FB),
              borderRadius: BorderRadius.circular(borderRadius),
              border: Border.all(color: const Color(0xFFEAECF0), width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.timer,
                  color: timerColor,
                  size: iconSize,
                ),
                SizedBox(width: spacing),
                Flexible(
                  child: Text(
                    timerText,
                    style: TextStyle(
                      fontSize: fontSize,
                      fontWeight: FontWeight.w600,
                      color: timerColor,
                      letterSpacing: 0.5,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (isGameOver) ...[
                  SizedBox(width: spacing),
                  Icon(
                    Icons.warning_amber_rounded,
                    color: Colors.red,
                    size: iconSize - 2,
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}