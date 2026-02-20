import "package:flutter/material.dart";

class DeviceProfile {
  const DeviceProfile({
    required this.name,
    required this.size,
    required this.platform,
  });

  final String name;
  final Size size;
  final String platform;
}

class DeviceProfiles {
  DeviceProfiles._();

  static const List<DeviceProfile> all = <DeviceProfile>[
    DeviceProfile(name: "iPhone 15 Pro", size: Size(393, 852), platform: "ios"),
    DeviceProfile(name: "iPhone 15 Pro Max", size: Size(430, 932), platform: "ios"),
    DeviceProfile(name: "iPhone 15", size: Size(390, 844), platform: "ios"),
    DeviceProfile(name: "iPhone 14", size: Size(390, 844), platform: "ios"),
    DeviceProfile(name: "iPhone SE", size: Size(375, 667), platform: "ios"),
    DeviceProfile(name: "iPhone 13 mini", size: Size(375, 812), platform: "ios"),
    DeviceProfile(name: "Pixel 8", size: Size(412, 915), platform: "android"),
    DeviceProfile(name: "Pixel 7", size: Size(412, 915), platform: "android"),
    DeviceProfile(name: "Pixel 6a", size: Size(412, 892), platform: "android"),
    DeviceProfile(name: "Samsung S24", size: Size(360, 780), platform: "android"),
    DeviceProfile(name: "Samsung S23", size: Size(360, 780), platform: "android"),
    DeviceProfile(name: "iPad Pro 12.9", size: Size(1024, 1366), platform: "ios"),
    DeviceProfile(name: "iPad Pro 11", size: Size(834, 1194), platform: "ios"),
    DeviceProfile(name: "iPad Air", size: Size(820, 1180), platform: "ios"),
    DeviceProfile(name: "iPad mini", size: Size(744, 1133), platform: "ios"),
    DeviceProfile(name: "Desktop 1920", size: Size(1920, 1080), platform: "desktop"),
    DeviceProfile(name: "Desktop 1440", size: Size(1440, 900), platform: "desktop"),
    DeviceProfile(name: "Desktop 1280", size: Size(1280, 720), platform: "desktop"),
    DeviceProfile(name: "Custom", size: Size(400, 800), platform: "desktop"),
  ];

  static final Map<String, DeviceProfile> _byName = <String, DeviceProfile>{
    for (final DeviceProfile profile in all) profile.name: profile,
  };

  static List<String> get names => all.map((DeviceProfile e) => e.name).toList(growable: false);

  static DeviceProfile byName(String name) {
    return _byName[name] ?? _byName["iPhone 15 Pro"]!;
  }

  static Size viewportSize(
    String deviceName, {
    bool landscape = false,
    Size? customSize,
  }) {
    final Size base = deviceName == "Custom"
        ? (customSize ?? const Size(400, 800))
        : byName(deviceName).size;
    return landscape ? Size(base.height, base.width) : base;
  }
}
