import "dart:convert";
import "dart:io";
import "package:flutter/foundation.dart";

class LocalCache {
  LocalCache._();
  static final instance = LocalCache._();

  late String _cacheDir;
  final Map<String, _CacheEntry> _memory = {};
  bool _initialized = false;

  static const _maxMemoryEntries = 500;
  static const _defaultTtl = Duration(hours: 4);

  Future<void> init() async {
    if (_initialized) return;
    final home = Platform.environment["USERPROFILE"] ??
        Platform.environment["HOME"] ??
        Directory.systemTemp.path;
    _cacheDir = "$home${Platform.pathSeparator}.rebot${Platform.pathSeparator}cache";
    final dir = Directory(_cacheDir);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    _initialized = true;
  }

  String _sanitizeKey(String key) =>
      key.replaceAll(RegExp(r'[^a-zA-Z0-9_\-.]'), '_');

  Future<void> put(
    String key,
    dynamic value, {
    Duration ttl = _defaultTtl,
  }) async {
    await init();
    final entry = _CacheEntry(
      value: value,
      expiresAt: DateTime.now().add(ttl),
      createdAt: DateTime.now(),
    );
    _memory[key] = entry;
    _trimMemory();

    try {
      final file = File("$_cacheDir${Platform.pathSeparator}${_sanitizeKey(key)}.json");
      await file.writeAsString(jsonEncode(entry.toMap()), flush: true);
    } catch (e) {
      debugPrint("Cache write failed for $key: $e");
    }
  }

  Future<T?> get<T>(String key) async {
    if (_memory.containsKey(key)) {
      final entry = _memory[key]!;
      if (!entry.isExpired) return entry.value as T?;
      _memory.remove(key);
    }

    await init();
    try {
      final file = File("$_cacheDir${Platform.pathSeparator}${_sanitizeKey(key)}.json");
      if (await file.exists()) {
        final raw = await file.readAsString();
        final entry = _CacheEntry.fromMap(jsonDecode(raw));
        if (!entry.isExpired) {
          _memory[key] = entry;
          return entry.value as T?;
        } else {
          await file.delete();
        }
      }
    } catch (e) {
      debugPrint("Cache read failed for $key: $e");
    }
    return null;
  }

  Future<T> getOrFetch<T>(
    String key,
    Future<T> Function() fetcher, {
    Duration ttl = _defaultTtl,
  }) async {
    final cached = await get<T>(key);
    if (cached != null) return cached;

    final value = await fetcher();
    await put(key, value, ttl: ttl);
    return value;
  }

  Future<void> remove(String key) async {
    _memory.remove(key);
    await init();
    try {
      final file = File("$_cacheDir${Platform.pathSeparator}${_sanitizeKey(key)}.json");
      if (await file.exists()) await file.delete();
    } catch (_) {}
  }

  Future<void> clear() async {
    _memory.clear();
    await init();
    try {
      final dir = Directory(_cacheDir);
      if (await dir.exists()) {
        await for (final entity in dir.list()) {
          if (entity is File && entity.path.endsWith(".json")) {
            await entity.delete();
          }
        }
      }
    } catch (_) {}
  }

  Future<int> sizeBytes() async {
    await init();
    int total = 0;
    try {
      final dir = Directory(_cacheDir);
      if (await dir.exists()) {
        await for (final entity in dir.list()) {
          if (entity is File) total += await entity.length();
        }
      }
    } catch (_) {}
    return total;
  }

  void _trimMemory() {
    while (_memory.length > _maxMemoryEntries) {
      _memory.remove(_memory.keys.first);
    }
  }
}

class _CacheEntry {
  final dynamic value;
  final DateTime expiresAt;
  final DateTime createdAt;

  _CacheEntry({
    required this.value,
    required this.expiresAt,
    required this.createdAt,
  });

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  Map<String, dynamic> toMap() => {
        "value": value,
        "expires_at": expiresAt.toIso8601String(),
        "created_at": createdAt.toIso8601String(),
      };

  factory _CacheEntry.fromMap(Map<String, dynamic> map) => _CacheEntry(
        value: map["value"],
        expiresAt: DateTime.parse(map["expires_at"]),
        createdAt: DateTime.parse(map["created_at"]),
      );
}

class ConnectivityMonitor {
  ConnectivityMonitor._();
  static final instance = ConnectivityMonitor._();

  bool _isOnline = true;
  DateTime? _lastOnline;
  final List<void Function(bool isOnline)> _listeners = [];

  bool get isOnline => _isOnline;
  DateTime? get lastOnline => _lastOnline;

  void addListener(void Function(bool isOnline) listener) {
    _listeners.add(listener);
  }

  void removeListener(void Function(bool isOnline) listener) {
    _listeners.remove(listener);
  }

  void updateStatus(bool online) {
    if (online == _isOnline) return;
    _isOnline = online;
    if (online) _lastOnline = DateTime.now();
    for (final listener in _listeners) {
      listener(online);
    }
  }

  String get lastSyncedText {
    if (_lastOnline == null) return "Never";
    final diff = DateTime.now().difference(_lastOnline!);
    if (diff.inSeconds < 60) return "Just now";
    if (diff.inMinutes < 60) return "${diff.inMinutes}m ago";
    if (diff.inHours < 24) return "${diff.inHours}h ago";
    return "${diff.inDays}d ago";
  }
}
