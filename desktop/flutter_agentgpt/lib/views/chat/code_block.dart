import "package:flutter/material.dart";

class CodeBlock extends StatelessWidget {
  const CodeBlock({
    super.key,
    required this.code,
    this.language = "",
  });

  final String code;
  final String language;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF171B23),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (language.trim().isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                language.toUpperCase(),
                style: const TextStyle(
                  color: Color(0xFF8FA0BB),
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          SelectableText(
            code,
            style: const TextStyle(
              fontFamily: "JetBrains Mono",
              fontSize: 12,
              color: Color(0xFFDCE4F2),
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
