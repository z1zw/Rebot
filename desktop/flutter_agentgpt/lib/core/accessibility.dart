import "package:flutter/material.dart";
import "package:flutter/rendering.dart";
import "package:flutter/services.dart";

class AccessibleButton extends StatelessWidget {
  const AccessibleButton({
    super.key,
    required this.label,
    required this.onTap,
    required this.child,
    this.hint,
    this.isButton = true,
    this.shortcut,
  });

  final String label;
  final String? hint;
  final VoidCallback onTap;
  final Widget child;
  final bool isButton;
  final SingleActivator? shortcut;

  @override
  Widget build(BuildContext context) {
    Widget widget = Semantics(
      label: label,
      hint: hint,
      button: isButton,
      enabled: true,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          child: child,
        ),
      ),
    );

    if (shortcut != null) {
      widget = CallbackShortcuts(
        bindings: {shortcut!: onTap},
        child: Focus(child: widget),
      );
    }

    return widget;
  }
}

class AccessibleIconButton extends StatelessWidget {
  const AccessibleIconButton({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.size = 14,
    this.color,
    this.tooltip,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final double size;
  final Color? color;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      button: true,
      child: Tooltip(
        message: tooltip ?? label,
        waitDuration: const Duration(milliseconds: 500),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(4),
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: Icon(icon, size: size, color: color),
          ),
        ),
      ),
    );
  }
}

class AccessibleTextField extends StatelessWidget {
  const AccessibleTextField({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.obscure = false,
    this.onSubmitted,
    this.autofocus = false,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final bool obscure;
  final ValueChanged<String>? onSubmitted;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      textField: true,
      child: TextField(
        controller: controller,
        obscureText: obscure,
        autofocus: autofocus,
        onSubmitted: onSubmitted,
        decoration: InputDecoration(hintText: hint),
      ),
    );
  }
}

class AccessibleListItem extends StatelessWidget {
  const AccessibleListItem({
    super.key,
    required this.label,
    required this.child,
    this.onTap,
    this.selected = false,
    this.index,
    this.total,
  });

  final String label;
  final Widget child;
  final VoidCallback? onTap;
  final bool selected;
  final int? index;
  final int? total;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      selected: selected,
      inMutuallyExclusiveGroup: true,
      enabled: onTap != null,
      child: InkWell(
        onTap: onTap,
        child: child,
      ),
    );
  }
}

class KeyboardNavigable extends StatefulWidget {
  const KeyboardNavigable({
    super.key,
    required this.itemCount,
    required this.onItemSelected,
    required this.child,
    this.onEscape,
  });

  final int itemCount;
  final void Function(int index) onItemSelected;
  final Widget child;
  final VoidCallback? onEscape;

  @override
  State<KeyboardNavigable> createState() => _KeyboardNavigableState();
}

class _KeyboardNavigableState extends State<KeyboardNavigable> {
  int _focusedIndex = -1;
  late FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode();
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  KeyEventResult _handleKey(FocusNode node, KeyEvent event) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;

    if (event.logicalKey == LogicalKeyboardKey.arrowDown) {
      setState(() {
        _focusedIndex = (_focusedIndex + 1).clamp(0, widget.itemCount - 1);
      });
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.arrowUp) {
      setState(() {
        _focusedIndex = (_focusedIndex - 1).clamp(0, widget.itemCount - 1);
      });
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.enter && _focusedIndex >= 0) {
      widget.onItemSelected(_focusedIndex);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.escape) {
      widget.onEscape?.call();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _focusNode,
      onKeyEvent: _handleKey,
      child: widget.child,
    );
  }
}

class ScreenReaderAnnounce {
  static void announce(BuildContext context, String message) {
    SemanticsService.announce(message, TextDirection.ltr);
  }
}
