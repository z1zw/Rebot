import "dart:async";
import "package:flutter/material.dart";
import "package:bitsdojo_window/bitsdojo_window.dart";
import "package:provider/provider.dart";
import "app_state.dart";
import "core/error_boundary.dart";
import "core/performance_monitor.dart";
import "core/local_cache.dart";
import "state/project_state.dart";
import "state/conversation_state.dart";
import "state/file_explorer_state.dart";
import "state/execution_state.dart";
import "state/devserver_state.dart";
import "state/settings_state.dart";
import "state/preview_state.dart";
import "theme/app_tokens.dart";
import "views/project_home.dart";
import "views/main_layout.dart";

void main() {
  runZonedGuarded(() {
    WidgetsFlutterBinding.ensureInitialized();
    PerformanceMonitor.instance.init();
    LocalCache.instance.init();

    FlutterError.onError = (details) {
      PerformanceMonitor.instance.recordError(
        details.exception,
        details.stack,
        context: details.context?.toDescription() ?? "flutter",
      );
      FlutterError.presentError(details);
    };

    runApp(const RebotApp());
    doWhenWindowReady(() {
      const initialSize = Size(1400, 900);
      appWindow.minSize = const Size(1100, 700);
      appWindow.size = initialSize;
      appWindow.alignment = Alignment.center;
      appWindow.title = "Rebot";
      appWindow.show();
    });
  }, (error, stackTrace) {
    PerformanceMonitor.instance.recordError(error, stackTrace, context: "zone");
  });
}

// Pre-built theme to avoid rebuilding on every render
final ThemeData _cachedTheme = _buildAppTheme();

ThemeData _buildAppTheme() {
  // Use system fonts instead of GoogleFonts to avoid network/loading delays
  const textTheme = TextTheme(
    headlineLarge: TextStyle(fontSize: 26, fontWeight: FontWeight.w600, letterSpacing: -0.4, color: Color(0xFFD1D5DB)),
    headlineMedium: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, letterSpacing: -0.2, color: Color(0xFFD1D5DB)),
    titleLarge: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: -0.2, color: Color(0xFFD1D5DB)),
    titleMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: -0.1, color: Color(0xFFD1D5DB)),
    titleSmall: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFFD1D5DB)),
    bodyMedium: TextStyle(fontSize: 13, height: 1.45, color: Color(0xFFD1D5DB)),
    bodySmall: TextStyle(fontSize: 12, height: 1.45, color: Color(0xFF8E8E8E)),
    labelSmall: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, letterSpacing: 0.3, color: Color(0xFF6E6E6E)),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    visualDensity: VisualDensity.compact,
    scaffoldBackgroundColor: AppTokens.bg,
    fontFamily: 'Segoe UI', // Use system font
    colorScheme: ColorScheme.dark(
      primary: AppTokens.primary,
      secondary: AppTokens.textSecondary,
      surface: AppTokens.surface,
      error: const Color(0xFFEF4444),
      onPrimary: Colors.white,
      onSecondary: AppTokens.textPrimary,
      onSurface: AppTokens.textPrimary,
      outline: AppTokens.border,
    ),
    dividerTheme: const DividerThemeData(
      color: AppTokens.border,
      thickness: 1,
      space: 0,
    ),
    textTheme: textTheme,
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFF2F2F2F),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF333333)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF333333)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF10A37F), width: 1.5),
      ),
      hoverColor: const Color(0xFF2A2A2A),
      hintStyle: const TextStyle(fontSize: 13, color: Color(0xFF8E8E8E), letterSpacing: 0.2),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppTokens.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTokens.radiusMd)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppTokens.textPrimary,
        side: const BorderSide(color: AppTokens.border),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTokens.radiusMd)),
      ),
    ),
  );
}


class RebotApp extends StatelessWidget {
  const RebotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppState()),
        ChangeNotifierProvider(create: (_) => ProjectState()),
        ChangeNotifierProvider(create: (_) => ConversationState()),
        ChangeNotifierProvider(create: (_) => FileExplorerState()),
        ChangeNotifierProvider(create: (_) => ExecutionState()),
        ChangeNotifierProvider(create: (_) => DevServerState()),
        ChangeNotifierProvider(create: (_) => SettingsState()),
        ChangeNotifierProvider(create: (_) => PreviewState()),
      ],
      child: ErrorBoundary(
        child: MaterialApp(
          title: "Rebot",
          debugShowCheckedModeBanner: false,
          theme: _cachedTheme,
          home: const _AppRouter(),
        ),
      ),
    );
  }
}

class _AppRouter extends StatelessWidget {
  const _AppRouter();

  @override
  Widget build(BuildContext context) {
    final activeProject = context.select<AppState, Project?>((s) => s.activeProject);
    if (activeProject == null) {
      return const ProjectHome();
    }
    return const Workspace();
  }
}
