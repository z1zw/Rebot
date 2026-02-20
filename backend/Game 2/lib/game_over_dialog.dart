import 'package:flutter/material.dart';

class GameOverDialog extends StatelessWidget {
  final bool isWin;
  final int score;
  final int bestScore;
  final VoidCallback onRestart;
  final VoidCallback onContinue;

  const GameOverDialog({
    Key? key,
    required this.isWin,
    required this.score,
    required this.bestScore,
    required this.onRestart,
    required this.onContinue,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final textTheme = theme.textTheme;
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;
    final isPortrait = screenHeight > screenWidth;
    final dialogWidth = isPortrait ? screenWidth * 0.85 : screenWidth * 0.5;
    final dialogMaxWidth = 500.0;
    final effectiveWidth = dialogWidth.clamp(280.0, dialogMaxWidth);
    final padding = effectiveWidth * 0.06;
    final iconSize = effectiveWidth * 0.16;
    final titleStyle = textTheme.headlineMedium?.copyWith(
      fontWeight: FontWeight.w700,
      color: isWin ? Colors.green.shade700 : Colors.red.shade700,
    );
    final scoreLabelStyle = TextStyle(
      fontSize: effectiveWidth * 0.045,
      color: Colors.grey,
      fontWeight: FontWeight.w500,
    );
    final scoreValueStyle = TextStyle(
      fontSize: effectiveWidth * 0.055,
      fontWeight: FontWeight.w700,
      color: Colors.black87,
    );
    final buttonTextStyle = TextStyle(
      fontSize: effectiveWidth * 0.045,
      fontWeight: FontWeight.w600,
    );

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: EdgeInsets.symmetric(
        horizontal: screenWidth * 0.05,
        vertical: screenHeight * 0.05,
      ),
      child: Container(
        width: effectiveWidth,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(effectiveWidth * 0.04),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        padding: EdgeInsets.all(padding),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              isWin ? 'You Win!' : 'Game Over',
              style: titleStyle,
              textAlign: TextAlign.center,
            ),
            SizedBox(height: effectiveWidth * 0.04),
            Icon(
              isWin ? Icons.emoji_events : Icons.sentiment_dissatisfied,
              size: iconSize,
              color: isWin ? Colors.amber.shade700 : Colors.grey.shade600,
            ),
            SizedBox(height: effectiveWidth * 0.06),
            _buildScoreRow('Your Score', score.toString(), scoreLabelStyle, scoreValueStyle),
            SizedBox(height: effectiveWidth * 0.03),
            _buildScoreRow('Best Score', bestScore.toString(), scoreLabelStyle, scoreValueStyle),
            SizedBox(height: effectiveWidth * 0.08),
            if (isWin)
              Column(
                children: [
                  ElevatedButton(
                    onPressed: onContinue,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: colorScheme.primary,
                      foregroundColor: Colors.white,
                      padding: EdgeInsets.symmetric(vertical: effectiveWidth * 0.04),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(effectiveWidth * 0.03),
                      ),
                    ),
                    child: Text(
                      'Keep Playing',
                      style: buttonTextStyle,
                    ),
                  ),
                  SizedBox(height: effectiveWidth * 0.03),
                  OutlinedButton(
                    onPressed: onRestart,
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: colorScheme.primary),
                      padding: EdgeInsets.symmetric(vertical: effectiveWidth * 0.04),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(effectiveWidth * 0.03),
                      ),
                    ),
                    child: Text(
                      'New Game',
                      style: buttonTextStyle.copyWith(color: colorScheme.primary),
                    ),
                  ),
                ],
              )
            else
              ElevatedButton(
                onPressed: onRestart,
                style: ElevatedButton.styleFrom(
                  backgroundColor: colorScheme.primary,
                  foregroundColor: Colors.white,
                  padding: EdgeInsets.symmetric(vertical: effectiveWidth * 0.04),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(effectiveWidth * 0.03),
                  ),
                ),
                child: Text(
                  'Try Again',
                  style: buttonTextStyle,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildScoreRow(String label, String value, TextStyle labelStyle, TextStyle valueStyle) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: labelStyle),
        Text(value, style: valueStyle),
      ],
    );
  }
}