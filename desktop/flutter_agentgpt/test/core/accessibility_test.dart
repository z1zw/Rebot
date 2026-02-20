import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/accessibility.dart";

void main() {
  group("AccessibleButton", () {
    testWidgets("renders child and handles tap", (tester) async {
      bool tapped = false;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: AccessibleButton(
            label: "Test Button",
            onTap: () => tapped = true,
            child: const Text("Click me"),
          ),
        ),
      ));
      expect(find.text("Click me"), findsOneWidget);
      await tester.tap(find.text("Click me"));
      expect(tapped, true);
    });

    testWidgets("has Semantics with label", (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: AccessibleButton(
            label: "Save file",
            onTap: () {},
            child: const Text("Save"),
          ),
        ),
      ));
      final semantics = tester.getSemantics(find.text("Save"));
      expect(semantics.label, contains("Save file"));
    });
  });

  group("AccessibleIconButton", () {
    testWidgets("renders with tooltip", (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: AccessibleIconButton(
            icon: Icons.refresh,
            label: "Refresh list",
            onTap: () {},
            tooltip: "Refresh",
          ),
        ),
      ));
      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });
  });

  group("KeyboardNavigable", () {
    testWidgets("renders child", (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: KeyboardNavigable(
            itemCount: 5,
            onItemSelected: (_) {},
            child: const Text("Nav items"),
          ),
        ),
      ));
      expect(find.text("Nav items"), findsOneWidget);
    });
  });

  group("AccessibleListItem", () {
    testWidgets("renders with selected state", (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: AccessibleListItem(
            label: "Item 1",
            selected: true,
            child: const Text("Item 1"),
          ),
        ),
      ));
      expect(find.text("Item 1"), findsOneWidget);
    });
  });
}
