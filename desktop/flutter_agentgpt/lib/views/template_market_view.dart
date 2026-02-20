import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../app_state.dart";
import "../services/api_service.dart";

class TemplateMarketView extends StatefulWidget {
  const TemplateMarketView({super.key});

  @override
  State<TemplateMarketView> createState() => _TemplateMarketViewState();
}

class _TemplateMarketViewState extends State<TemplateMarketView> {
  final TextEditingController _searchController = TextEditingController();
  String _query = "";
  bool _busy = false;
  late Future<List<TemplateMarketItem>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<List<TemplateMarketItem>> _load() async {
    final state = context.read<AppState>();
    return state.api.listTemplateMarket(query: _query);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
  }

  Future<void> _saveCurrentTemplate() async {
    final state = context.read<AppState>();
    final nameCtrl = TextEditingController(text: state.activeProject?.name ?? "");
    final descCtrl = TextEditingController();
    final tagsCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Save Current Project as Template"),
        content: SizedBox(
          width: 460,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: "Template Name")),
              const SizedBox(height: 8),
              TextField(controller: descCtrl, decoration: const InputDecoration(labelText: "Description")),
              const SizedBox(height: 8),
              TextField(controller: tagsCtrl, decoration: const InputDecoration(labelText: "Tags (comma separated)")),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Save")),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final tags = tagsCtrl.text
          .split(",")
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      await state.saveCurrentProjectToTemplateMarket(
        name: nameCtrl.text.trim(),
        description: descCtrl.text.trim(),
        tags: tags,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Template saved.")));
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Save failed: $e")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _importTemplate() async {
    final state = context.read<AppState>();
    final sourceCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    final tagsCtrl = TextEditingController();
    String framework = "general";
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlg) => AlertDialog(
          title: const Text("Import Template (Folder/ZIP)"),
          content: SizedBox(
            width: 500,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: sourceCtrl, decoration: const InputDecoration(labelText: "Source Path")),
                const SizedBox(height: 8),
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: "Template Name (optional)")),
                const SizedBox(height: 8),
                TextField(controller: descCtrl, decoration: const InputDecoration(labelText: "Description")),
                const SizedBox(height: 8),
                TextField(controller: tagsCtrl, decoration: const InputDecoration(labelText: "Tags (comma separated)")),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: framework,
                  items: const [
                    DropdownMenuItem(value: "general", child: Text("general")),
                    DropdownMenuItem(value: "flutter", child: Text("flutter")),
                    DropdownMenuItem(value: "react", child: Text("react")),
                    DropdownMenuItem(value: "vue", child: Text("vue")),
                    DropdownMenuItem(value: "python", child: Text("python")),
                  ],
                  onChanged: (v) => setDlg(() => framework = v ?? "general"),
                  decoration: const InputDecoration(labelText: "Framework"),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
            FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Import")),
          ],
        ),
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final tags = tagsCtrl.text
          .split(",")
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      await state.importTemplateToMarket(
        sourcePath: sourceCtrl.text.trim(),
        name: nameCtrl.text.trim().isEmpty ? null : nameCtrl.text.trim(),
        description: descCtrl.text.trim(),
        tags: tags,
        framework: framework,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Template imported.")));
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Import failed: $e")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openAsProject(TemplateMarketItem item) async {
    final state = context.read<AppState>();
    final nameCtrl = TextEditingController(text: item.name);
    final dstCtrl = TextEditingController();
    String framework = item.projectType;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlg) => AlertDialog(
          title: Text("Open Template: ${item.name}"),
          content: SizedBox(
            width: 500,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: "Project Name")),
                const SizedBox(height: 8),
                TextField(controller: dstCtrl, decoration: const InputDecoration(labelText: "Destination (optional)")),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: framework,
                  items: const [
                    DropdownMenuItem(value: "general", child: Text("general")),
                    DropdownMenuItem(value: "flutter", child: Text("flutter")),
                    DropdownMenuItem(value: "react", child: Text("react")),
                    DropdownMenuItem(value: "vue", child: Text("vue")),
                    DropdownMenuItem(value: "python", child: Text("python")),
                  ],
                  onChanged: (v) => setDlg(() => framework = v ?? item.projectType),
                  decoration: const InputDecoration(labelText: "Project Type"),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
            FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Open")),
          ],
        ),
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await state.openTemplateAsProject(
        templateId: item.id,
        name: nameCtrl.text.trim(),
        destination: dstCtrl.text.trim().isEmpty ? null : dstCtrl.text.trim(),
        projectType: framework,
        framework: framework,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Template opened as project.")));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Open failed: $e")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = context.select<AppState, Project?>((s) => s.activeProject);
    return Container(
      color: const Color(0xFF17181C),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: const BoxDecoration(
              color: Color(0xFF202329),
              border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
            ),
            child: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: [
                const Padding(
                  padding: EdgeInsets.only(right: 8),
                  child: Text("Template Market", style: TextStyle(color: Color(0xFFE8ECF2), fontSize: 14, fontWeight: FontWeight.w700)),
                ),
                SizedBox(
                  width: 280,
                  height: 34,
                  child: TextField(
                    controller: _searchController,
                    onChanged: (v) => setState(() => _query = v.trim()),
                    onSubmitted: (_) => _refresh(),
                    decoration: const InputDecoration(
                      hintText: "Search templates...",
                      contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      filled: true,
                      fillColor: Color(0xFF252A33),
                      border: OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(10))),
                    ),
                    style: const TextStyle(color: Color(0xFFE8ECF2), fontSize: 12),
                  ),
                ),
                FilledButton.icon(
                  onPressed: _busy || active == null ? null : _saveCurrentTemplate,
                  icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                  label: const Text("Save Current"),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _importTemplate,
                  icon: const Icon(Icons.file_open_outlined, size: 16),
                  label: const Text("Import"),
                ),
                IconButton(
                  onPressed: _busy ? null : _refresh,
                  icon: const Icon(Icons.refresh_rounded, color: Color(0xFFAAB3C2), size: 18),
                ),
              ],
            ),
          ),
          Expanded(
            child: FutureBuilder<List<TemplateMarketItem>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                final items = snapshot.data ?? const <TemplateMarketItem>[];
                if (items.isEmpty) {
                  return const Center(
                    child: Text("No templates yet. Save current project or import one.", style: TextStyle(color: Color(0xFF99A1B3))),
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.all(14),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF202329),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF343A46)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.inventory_2_outlined, color: Color(0xFF2A98FF), size: 18),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(item.name, style: const TextStyle(color: Color(0xFFE8ECF2), fontWeight: FontWeight.w700)),
                                const SizedBox(height: 2),
                                Text(
                                  item.description.isEmpty ? "No description" : item.description,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  "type=${item.projectType}  tags=${item.tags.join(", ")}",
                                  style: const TextStyle(color: Color(0xFF7E8797), fontSize: 10),
                                ),
                              ],
                            ),
                          ),
                          FilledButton(
                            onPressed: _busy ? null : () => _openAsProject(item),
                            child: const Text("Open as Project"),
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
