import "package:flutter/material.dart";

class MessageComposer extends StatefulWidget {
  const MessageComposer({
    super.key,
    required this.onSend,
    this.placeholder = "Message Rebot...",
    this.enabled = true,
  });

  final ValueChanged<String> onSend;
  final String placeholder;
  final bool enabled;

  @override
  State<MessageComposer> createState() => _MessageComposerState();
}

class _MessageComposerState extends State<MessageComposer> {
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    if (!widget.enabled) return;
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    widget.onSend(text);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 8, 8),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              enabled: widget.enabled,
              onSubmitted: (_) => _submit(),
              style: const TextStyle(color: Color(0xFFDCE4F2), fontSize: 13),
              decoration: InputDecoration(
                isDense: true,
                border: InputBorder.none,
                hintText: widget.placeholder,
                hintStyle: const TextStyle(color: Color(0xFF8F9AB0), fontSize: 13),
              ),
            ),
          ),
          IconButton(
            onPressed: widget.enabled ? _submit : null,
            icon: const Icon(Icons.send_rounded, size: 18),
          ),
        ],
      ),
    );
  }
}
