import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/home_screen.dart';
import 'screens/game_screen.dart';
import 'screens/score_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  runApp(const CheeseGameApp());
}

class CheeseGameApp extends StatelessWidget {
  const CheeseGameApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cheese Game',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.amber,
          background: const Color(0xFFF9F9FB),
          surface: const Color(0xFFF2F2F5),
          surfaceVariant: const Color(0xFFEAECF0),
        ),
        useMaterial3: true,
        fontFamily: 'Inter',
        textTheme: const TextTheme(
          displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w700),
          displayMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
          bodyLarge: TextStyle(fontSize: 16, height: 1.5),
          bodyMedium: TextStyle(fontSize: 14, height: 1.5),
          labelLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => const HomeScreen(),
        '/game': (context) => const GameScreen(),
        '/score': (context) => const ScoreScreen(),
      },
      builder: (context, child) {
        return LayoutBuilder(
          builder: (context, constraints) {
            // Set a reference width for scaling calculations
            final double referenceWidth = 375.0; // Typical mobile width
            final double scaleFactor = constraints.maxWidth / referenceWidth;
            
            return MediaQuery(
              data: MediaQuery.of(context).copyWith(
                textScaler: TextScaler.linear(MediaQuery.of(context).textScaleFactor * 
                  (scaleFactor > 1.2 ? 1.2 : (scaleFactor < 0.8 ? 0.8 : scaleFactor))),
              ),
              child: Container(
                constraints: BoxConstraints(
                  minWidth: constraints.minWidth,
                  maxWidth: constraints.maxWidth,
                  minHeight: constraints.minHeight,
                  maxHeight: constraints.maxHeight,
                ),
                child: child!,
              ),
            );
          },
        );
      },
    );
  }
}