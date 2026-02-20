import 'package:flutter/material.dart';

class CheeseButton extends StatefulWidget {
  final String label;
  final VoidCallback onPressed;
  final Color? backgroundColor;
  final Color? textColor;
  final double? width;
  final double? height;
  final bool enabled;

  const CheeseButton({
    Key? key,
    required this.label,
    required this.onPressed,
    this.backgroundColor,
    this.textColor,
    this.width,
    this.height,
    this.enabled = true,
  }) : super(key: key);

  @override
  State<CheeseButton> createState() => _CheeseButtonState();
}

class _CheeseButtonState extends State<CheeseButton> with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 100),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    if (widget.enabled) {
      _animationController.forward();
    }
  }

  void _handleTapUp(TapUpDetails details) {
    if (widget.enabled) {
      _animationController.reverse();
      widget.onPressed();
    }
  }

  void _handleTapCancel() {
    if (widget.enabled) {
      _animationController.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    final Color backgroundColor = widget.backgroundColor ?? const Color(0xFFFFD700);
    final Color textColor = widget.textColor ?? const Color(0xFF8B4513);
    final Color disabledColor = Colors.grey.shade400;
    final Color disabledTextColor = Colors.grey.shade600;

    return LayoutBuilder(
      builder: (context, constraints) {
        final double maxWidth = constraints.maxWidth;
        final double maxHeight = constraints.maxHeight;
        final double buttonWidth = widget.width ?? (maxWidth.isFinite && maxWidth > 0 ? maxWidth * 0.8 : 200);
        final double buttonHeight = widget.height ?? (maxHeight.isFinite && maxHeight > 0 ? maxHeight * 0.1 : 60);
        final double fontSize = buttonHeight * 0.3;
        final double borderRadius = buttonHeight * 0.27;

        return GestureDetector(
          onTapDown: _handleTapDown,
          onTapUp: _handleTapUp,
          onTapCancel: _handleTapCancel,
          child: AnimatedBuilder(
            animation: _scaleAnimation,
            builder: (context, child) {
              return Transform.scale(
                scale: _scaleAnimation.value,
                child: Container(
                  width: buttonWidth,
                  height: buttonHeight,
                  constraints: BoxConstraints(
                    maxWidth: maxWidth.isFinite ? maxWidth : double.infinity,
                    maxHeight: maxHeight.isFinite ? maxHeight : double.infinity,
                  ),
                  decoration: BoxDecoration(
                    color: widget.enabled ? backgroundColor : disabledColor,
                    borderRadius: BorderRadius.circular(borderRadius),
                    boxShadow: widget.enabled
                        ? [
                            BoxShadow(
                              color: backgroundColor.withOpacity(0.5),
                              blurRadius: 8,
                              offset: const Offset(0, 4),
                            ),
                          ]
                        : null,
                    border: Border.all(
                      color: widget.enabled ? const Color(0xFFDAA520) : Colors.grey.shade500,
                      width: 2,
                    ),
                  ),
                  child: Center(
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Padding(
                        padding: EdgeInsets.symmetric(horizontal: buttonWidth * 0.05),
                        child: Text(
                          widget.label,
                          style: TextStyle(
                            fontSize: fontSize,
                            fontWeight: FontWeight.bold,
                            color: widget.enabled ? textColor : disabledTextColor,
                            letterSpacing: 1.2,
                          ),
                          textAlign: TextAlign.center,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }
}