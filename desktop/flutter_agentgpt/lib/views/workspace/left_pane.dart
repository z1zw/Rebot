import "package:flutter/material.dart";
import "package:rebot_agentgpt/views/chat_view.dart";

class WorkspaceLeftPane extends StatelessWidget {
  const WorkspaceLeftPane({
    super.key,
    required this.mode,
    required this.path,
    required this.content,
    required this.onNewConversation,
  });

  final String mode;
  final String path;
  final String content;
  final VoidCallback onNewConversation;

  @override
  Widget build(BuildContext context) {
    if (mode == "chat") {
      return Container(
        decoration: const BoxDecoration(
          color: Color(0xFF17181C),
          border: Border(right: BorderSide(color: Color(0xFF343A46))),
        ),
        child: Column(
          children: [
            Container(
              height: 48,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: const BoxDecoration(
                color: Color(0xFF202329),
                border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
              ),
              child: Row(
                children: [
                  const Text(
                    "AI Assistant",
                    style: TextStyle(
                      color: Color(0xFFE8ECF2),
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.1,
                    ),
                  ),
                  const Spacer(),
                  _MiniAction(icon: Icons.add_rounded, onTap: onNewConversation),
                ],
              ),
            ),
            const Expanded(child: ChatView()),
          ],
        ),
      );
    }

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF17181C),
        border: Border(right: BorderSide(color: Color(0xFF343A46))),
      ),
      child: Column(
        children: [
          Container(
            height: 42,
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: const BoxDecoration(
              color: Color(0xFF202329),
              border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
            ),
            child: Text(
              path.isEmpty ? "No file selected" : path,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Color(0xFFA0A8B8), fontSize: 12),
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(12),
              child: SelectableText(
                content.isEmpty ? "Select a file from explorer to open code." : content,
                style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 13, color: Color(0xFFB8C2D2), height: 1.6),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniAction extends StatefulWidget {
  const _MiniAction({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;

  @override
  State<_MiniAction> createState() => _MiniActionState();
}

class _MiniActionState extends State<_MiniAction> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: _hover ? const Color(0xFF2D3340) : const Color(0xFF252A33),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: _hover ? const Color(0xFF53617A) : const Color(0xFF3A4252),
            ),
          ),
          child: Icon(
            widget.icon,
            size: 16,
            color: _hover ? const Color(0xFF2A98FF) : const Color(0xFFAAB3C2),
          ),
        ),
      ),
    );
  }
}
