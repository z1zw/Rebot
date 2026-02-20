import "package:flutter/material.dart";

class DeviceSimulator extends StatelessWidget {
  const DeviceSimulator({
    super.key,
    this.label = "Preview",
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF11151D),
      alignment: Alignment.center,
      padding: const EdgeInsets.all(16),
      child: Container(
        width: 260,
        height: 500,
        decoration: BoxDecoration(
          color: const Color(0xFF1E222A),
          borderRadius: BorderRadius.circular(26),
          border: Border.all(color: const Color(0xFF343A46), width: 1.5),
        ),
        child: Column(
          children: [
            const SizedBox(height: 8),
            Container(
              width: 76,
              height: 6,
              decoration: BoxDecoration(
                color: const Color(0xFF4A556B),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            const SizedBox(height: 12),
            const Icon(Icons.play_circle_outline_rounded, size: 34, color: Color(0xFF95A0B5)),
            const SizedBox(height: 10),
            const Text(
              "Run to start preview",
              style: TextStyle(color: Color(0xFFDCE4F2), fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                label,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF8FA0BB), fontSize: 11),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
