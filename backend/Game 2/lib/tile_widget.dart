import 'package:flutter/material.dart';

class TileWidget extends StatefulWidget {
  final int value;
  final int row;
  final int col;
  final double size;
  final bool isNew;
  final bool isMerged;

  const TileWidget({
    Key? key,
    required this.value,
    required this.row,
    required this.col,
    required this.size,
    this.isNew = false,
    this.isMerged = false,
  }) : super(key: key);

  @override
  _TileWidgetState createState() => _TileWidgetState();
}

class _TileWidgetState extends State<TileWidget> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(
      begin: widget.isNew ? 0.0 : 1.0,
      end: 1.0,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutBack,
      ),
    );

    _opacityAnimation = Tween<double>(
      begin: widget.isMerged ? 0.5 : 1.0,
      end: 1.0,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );

    if (widget.isNew || widget.isMerged) {
      _controller.forward();
    } else {
      _controller.value = 1.0;
    }
  }

  @override
  void didUpdateWidget(TileWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isNew != oldWidget.isNew || widget.isMerged != oldWidget.isMerged) {
      _controller.reset();
      _controller.forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getTileColor() {
    switch (widget.value) {
      case 2:
        return const Color(0xFFEEE4DA);
      case 4:
        return const Color(0xFFEDE0C8);
      case 8:
        return const Color(0xFFF2B179);
      case 16:
        return const Color(0xFFF59563);
      case 32:
        return const Color(0xFFF67C5F);
      case 64:
        return const Color(0xFFF65E3B);
      case 128:
        return const Color(0xFFEDCF72);
      case 256:
        return const Color(0xFFEDCC61);
      case 512:
        return const Color(0xFFEDC850);
      case 1024:
        return const Color(0xFFEDC53F);
      case 2048:
        return const Color(0xFFEDC22E);
      default:
        return const Color(0xFFCDC1B4);
    }
  }

  Color _getTextColor() {
    if (widget.value <= 4) {
      return const Color(0xFF776E65);
    }
    return const Color(0xFFF9F6F2);
  }

  double _getFontSize(double size) {
    if (widget.value < 100) {
      return size * 0.4;
    } else if (widget.value < 1000) {
      return size * 0.35;
    } else {
      return size * 0.3;
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final tileSize = constraints.maxWidth;
        final margin = tileSize * 0.02;
        final fontSize = _getFontSize(tileSize);
        final borderRadius = tileSize * 0.03;

        return AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Transform.scale(
              scale: _scaleAnimation.value,
              child: Opacity(
                opacity: _opacityAnimation.value,
                child: Container(
                  width: tileSize,
                  height: tileSize,
                  margin: EdgeInsets.all(margin),
                  decoration: BoxDecoration(
                    color: _getTileColor(),
                    borderRadius: BorderRadius.circular(borderRadius),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.1),
                        blurRadius: margin * 2,
                        offset: Offset(0, margin * 0.5),
                      ),
                    ],
                  ),
                  child: Center(
                    child: widget.value == 0
                        ? Container()
                        : FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              widget.value.toString(),
                              style: TextStyle(
                                fontSize: fontSize,
                                fontWeight: FontWeight.bold,
                                color: _getTextColor(),
                              ),
                            ),
                          ),
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }
}