import "package:flutter/material.dart";

/// ChatGPT风格设计令牌 - 深色主题设计系统
class AppTokens {
  AppTokens._();

  // ─── 主色调 ─────────────────────────────────────────────────────────
  static const Color primary = Color(0xFF10A37F);
  static const Color primaryHover = Color(0xFF0E9469);
  static const Color primaryPressed = Color(0xFF0C8558);
  static const Color accent = Color(0xFF1A7F5A);
  static const Color accentHover = Color(0xFF22996B);

  // ─── 背景色 ─────────────────────────────────────────────────────────
  static const Color bg = Color(0xFF212121);
  static const Color bgElevated = Color(0xFF2A2A2A);
  static const Color bgHover = Color(0xFF2F2F2F);
  static const Color bgActive = Color(0xFF343434);
  static const Color bgInput = Color(0xFF2F2F2F);
  static const Color bgToolbar = Color(0xFF171717);
  static const Color bgEditor = Color(0xFF1A1A1A);
  static const Color bgEditorGutter = Color(0xFF212121);

  // ─── 表面色 ─────────────────────────────────────────────────────────
  static const Color surface = Color(0xFF2A2A2A);
  static const Color surfaceElevated = Color(0xFF333333);
  static const Color surfaceOverlay = Color(0xFF3A3A3A);

  // ─── 边框色 ─────────────────────────────────────────────────────────
  static const Color border = Color(0xFF333333);
  static const Color borderFocused = Color(0xFF10A37F);
  static const Color borderSubtle = Color(0xFF2A2A2A);
  static const Color borderStrong = Color(0xFF444444);

  // ─── 文字色 ─────────────────────────────────────────────────────────
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFD1D5DB);
  static const Color textTertiary = Color(0xFF8E8E8E);
  static const Color textDisabled = Color(0xFF6B6B6B);
  static const Color textLink = Color(0xFF10A37F);
  static const Color textOnPrimary = Color(0xFFFFFFFF);

  // ─── 语义色 ─────────────────────────────────────────────────────────
  static const Color success = Color(0xFF10A37F);
  static const Color successBg = Color(0xFF1A3D2E);
  static const Color warning = Color(0xFFFFC107);
  static const Color warningBg = Color(0xFF3D3A1A);
  static const Color error = Color(0xFFEF4444);
  static const Color errorBg = Color(0xFF3D1A1A);
  static const Color info = Color(0xFF3B82F6);
  static const Color infoBg = Color(0xFF1A2A3D);

  // ─── 语法高亮色 ─────────────────────────────────────────────────────
  static const Color syntaxKeyword = Color(0xFFCC7832);
  static const Color syntaxString = Color(0xFF6A8759);
  static const Color syntaxNumber = Color(0xFF6897BB);
  static const Color syntaxComment = Color(0xFF808080);
  static const Color syntaxFunction = Color(0xFFFFC66D);
  static const Color syntaxClass = Color(0xFFA9B7C6);
  static const Color syntaxVariable = Color(0xFF9876AA);
  static const Color syntaxOperator = Color(0xFFA9B7C6);

  // ─── 行号颜色 ─────────────────────────────────────────────────────
  static const Color lineNumber = Color(0xFF606366);
  static const Color lineNumberActive = Color(0xFFA4A3A3);
  static const Color lineHighlight = Color(0xFF323438);

  // ─── Tab样式 ─────────────────────────────────────────────────────
  static const Color tabBg = Color(0xFF2A2A2A);
  static const Color tabActiveBg = Color(0xFF212121);
  static const Color tabHoverBg = Color(0xFF333333);
  static const Color tabBorder = Color(0xFF10A37F);
  static const Color tabCloseHover = Color(0xFF444444);

  // ─── 圆角 ─────────────────────────────────────────────────────────
  static const double radiusXs = 4;
  static const double radiusSm = 6;
  static const double radiusMd = 8;
  static const double radiusLg = 10;
  static const double radiusXl = 12;
  static const double radiusPill = 999;

  // Spacing scale
  static const double space2 = 2;
  static const double space4 = 4;
  static const double space6 = 6;
  static const double space8 = 8;
  static const double space10 = 10;
  static const double space12 = 12;
  static const double space14 = 14;
  static const double space16 = 16;
  static const double space20 = 20;

  // Typography scale
  static const double textXs = 11;
  static const double textSm = 12;
  static const double textMd = 14;
  static const double textLg = 16;

  // ─── 动画时长 ─────────────────────────────────────────────────────
  static const Duration motionFast = Duration(milliseconds: 100);
  static const Duration motionNormal = Duration(milliseconds: 150);
  static const Duration motionSlow = Duration(milliseconds: 200);
  static const Duration motionSlowest = Duration(milliseconds: 300);

  // ─── 阴影 ─────────────────────────────────────────────────────────
  static const List<BoxShadow> cardShadow = [
    BoxShadow(color: Color(0x40000000), blurRadius: 16, offset: Offset(0, 4)),
  ];

  static const List<BoxShadow> dropdownShadow = [
    BoxShadow(color: Color(0x60000000), blurRadius: 20, offset: Offset(0, 8)),
  ];

  static const List<BoxShadow> focusShadow = [
    BoxShadow(color: Color(0x403574F0), blurRadius: 0, spreadRadius: 2),
  ];

  static const List<BoxShadow> subtleShadow = [
    BoxShadow(color: Color(0x20000000), blurRadius: 8, offset: Offset(0, 2)),
  ];

  // ─── 字体 ─────────────────────────────────────────────────────────
  static const String fontMono = "JetBrains Mono";
  static const List<String> fontFallback = [
    "Inter",
    ".SF Pro Text",
    ".SF Pro Display",
    "Segoe UI",
    "PingFang SC",
    "Microsoft YaHei UI",
    "Noto Sans CJK SC",
  ];

  // ─── 文字样式工厂 ─────────────────────────────────────────────────
  static TextStyle text({
    double? size,
    FontWeight? weight,
    Color? color,
    double? height,
    double? letterSpacing,
    bool mono = false,
  }) {
    return TextStyle(
      fontSize: size,
      fontWeight: weight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
      fontFamily: mono ? fontMono : null,
      fontFamilyFallback: mono ? null : fontFallback,
    );
  }

  static TextStyle titleStyle() => text(
        size: textMd,
        weight: FontWeight.w700,
        color: textPrimary,
        height: 1.25,
      );

  static TextStyle bodyStyle() => text(
        size: textMd,
        weight: FontWeight.w500,
        color: textPrimary,
        height: 1.35,
      );

  static TextStyle captionStyle() => text(
        size: textSm,
        weight: FontWeight.w500,
        color: textTertiary,
        height: 1.25,
      );

  static BoxDecoration cardDecoration({bool elevated = false}) => BoxDecoration(
        color: elevated ? surfaceElevated : surface,
        borderRadius: BorderRadius.circular(radiusLg),
        border: Border.all(color: border),
      );

  // ─── ChatGPT风格输入框装饰 ─────────────────────────────────────────
  static InputDecoration ideaInputDecoration({
    String? hintText,
    Widget? prefixIcon,
    Widget? suffixIcon,
    bool dense = true,
  }) {
    return InputDecoration(
      hintText: hintText,
      hintStyle: const TextStyle(fontSize: 13, color: Color(0xFF8E8E8E), letterSpacing: 0.2),
      prefixIcon: prefixIcon,
      suffixIcon: suffixIcon,
      isDense: dense,
      filled: true,
      fillColor: const Color(0xFF2F2F2F),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF333333), width: 1),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF10A37F), width: 1.5),
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF333333)),
      ),
    );
  }

  // ─── ChatGPT风格按钮装饰 ─────────────────────────────────────────
  static BoxDecoration ideaButtonDecoration({
    bool primary = false,
    bool hovered = false,
    bool danger = false,
  }) {
    Color bgColor;
    if (danger) {
      bgColor = hovered ? const Color(0xFFDC2626) : error;
    } else if (primary) {
      bgColor = hovered ? primaryHover : AppTokens.primary;
    } else {
      bgColor = hovered ? bgHover : surfaceElevated;
    }
    return BoxDecoration(
      color: bgColor,
      borderRadius: BorderRadius.circular(radiusSm),
      boxShadow: primary ? subtleShadow : null,
    );
  }
}
