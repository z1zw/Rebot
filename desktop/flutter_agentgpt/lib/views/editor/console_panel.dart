import 'package:flutter/material.dart';

class ConsolePanel extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // Placeholder for console output/logs
    return Container(
      color: Colors.black,
      padding: EdgeInsets.all(8),
      child: ListView(
        children: [
          Text(
            'Console output will appear here.',
            style: TextStyle(color: Colors.greenAccent, fontFamily: 'monospace'),
          ),
          // ... more log lines ...
        ],
      ),
    );
  }
}
