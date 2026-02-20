import 'package:flutter/material.dart';
class DeviceSimulator extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // Placeholder for device preview/simulator
    return Container(
      color: Colors.grey[100],
      margin: EdgeInsets.all(8),
      child: Center(
        child: Container(
          width: 180,
          height: 320,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.black26, width: 2),
            borderRadius: BorderRadius.circular(16),
            color: Colors.white,
          ),
          child: Center(
            child: Text(
              'Device Preview',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ),
        ),
      ),
    );
  }
}
