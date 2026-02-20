import "package:flutter/material.dart";

class MessageRow extends StatelessWidget {
  const MessageRow({
    super.key,
    required this.content,
    this.title = "",
    this.trailing,
  });

  final String title;
  final String content;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title.trim().isNotEmpty)
                  Text(
                    title,
                    style: const TextStyle(
                      color: Color(0xFFA8B3C8),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                if (title.trim().isNotEmpty) const SizedBox(height: 4),
                SelectableText(
                  content,
                  style: const TextStyle(
                    color: Color(0xFFDCE4F2),
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 8),
            trailing!,
          ],
        ],
      ),
    );
  }
}
