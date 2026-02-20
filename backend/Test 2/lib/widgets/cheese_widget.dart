import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/game_state.dart';

class CheeseWidget extends StatefulWidget {
  final double size;
  final VoidCallback? onCollected;

  const CheeseWidget({
    Key? key,
    this.size = 100.0,
    this.onCollected,
  }) : super(key: key);

  @override
  _CheeseWidgetState createState() => _CheeseWidgetState();
}

class _CheeseWidgetState extends State<CheeseWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotationAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    _scaleAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.3), weight: 50),
      TweenSequenceItem(tween: Tween(begin: 1.3, end: 0.0), weight: 50),
    ]).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    ));

    _rotationAnimation = Tween<double>(begin: 0.0, end: 2 * 3.14159).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _controller.reset();
      }
    });
  }

  void _handleTap() {
    final gameState = Provider.of<GameState>(context, listen: false);
    gameState.collectCheese();
    _controller.forward();
    if (widget.onCollected != null) {
      widget.onCollected!();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final double availableWidth = constraints.maxWidth;
        final double availableHeight = constraints.maxHeight;
        final double adaptiveSize = (availableWidth < availableHeight)
            ? availableWidth * 0.8
            : availableHeight * 0.8;
        final double effectiveSize = adaptiveSize > widget.size
            ? widget.size
            : (adaptiveSize < 50.0 ? 50.0 : adaptiveSize);

        return GestureDetector(
          onTap: _handleTap,
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return Transform.scale(
                scale: _scaleAnimation.value,
                child: Transform.rotate(
                  angle: _rotationAnimation.value,
                  child: child,
                ),
              );
            },
            child: Container(
              width: effectiveSize,
              height: effectiveSize,
              decoration: BoxDecoration(
                color: Colors.amber[700],
                borderRadius: BorderRadius.circular(effectiveSize * 0.2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.amber[900]!.withOpacity(0.4),
                    blurRadius: 10,
                    spreadRadius: 2,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Stack(
                children: [
                  // Cheese holes
                  Positioned(
                    top: effectiveSize * 0.3,
                    left: effectiveSize * 0.3,
                    child: _CheeseHole(size: effectiveSize * 0.15),
                  ),
                  Positioned(
                    top: effectiveSize * 0.6,
                    left: effectiveSize * 0.2,
                    child: _CheeseHole(size: effectiveSize * 0.12),
                  ),
                  Positioned(
                    top: effectiveSize * 0.4,
                    left: effectiveSize * 0.7,
                    child: _CheeseHole(size: effectiveSize * 0.1),
                  ),
                  Positioned(
                    top: effectiveSize * 0.7,
                    left: effectiveSize * 0.6,
                    child: _CheeseHole(size: effectiveSize * 0.13),
                  ),
                  // Shine effect
                  Positioned(
                    top: effectiveSize * 0.1,
                    left: effectiveSize * 0.1,
                    child: Container(
                      width: effectiveSize * 0.15,
                      height: effectiveSize * 0.15,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.amber[100]!.withOpacity(0.3),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CheeseHole extends StatelessWidget {
  final double size;

  const _CheeseHole({Key? key, required this.size}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.amber[900]!.withOpacity(0.6),
      ),
    );
  }
}