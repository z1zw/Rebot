import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../app_state.dart";
import "../services/api_service.dart";

class PluginMarketView extends StatefulWidget {
  const PluginMarketView({super.key});

  @override
  State<PluginMarketView> createState() => _PluginMarketViewState();
}

class _PluginMarketViewState extends State<PluginMarketView> {
  late Future<_PluginMarketData> _future;
  final TextEditingController _searchController = TextEditingController();
  String _query = "";
  bool _busy = false;

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

  Future<_PluginMarketData> _load() async {
    final api = context.read<AppState>().api;
    final providers = await api.getProviderCapabilities();
    final tools = await api.getToolCapabilities();
    final resources = await api.getResourceCapabilities();
    final plugins = await api.listInstalledPlugins();
    return _PluginMarketData(
      providers: providers,
      tools: tools,
      resources: resources,
      plugins: plugins,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
  }

  Future<void> _installPlugin() async {
    final app = context.read<AppState>();
    final sourceCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Install Plugin"),
        content: TextField(
          controller: sourceCtrl,
          decoration: const InputDecoration(
            labelText: "Plugin source path",
            hintText: r"C:\plugins\my-plugin or C:\plugins\my-plugin.zip",
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Install")),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final result = await app.api.installPlugin(sourcePath: sourceCtrl.text.trim());
      if (!mounted) return;
      if (result?["ok"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Plugin installed.")));
        await _refresh();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Install failed: ${result?["error"] ?? "unknown"}")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _initPluginSdk() async {
    final app = context.read<AppState>();
    final destinationCtrl = TextEditingController();
    final pluginIdCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final versionCtrl = TextEditingController(text: "0.1.0");
    final descCtrl = TextEditingController();
    final permsCtrl = TextEditingController(text: "fs.read");
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Init Plugin SDK Template"),
        content: SizedBox(
          width: 520,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: destinationCtrl, decoration: const InputDecoration(labelText: "Destination Folder")),
              const SizedBox(height: 8),
              TextField(controller: pluginIdCtrl, decoration: const InputDecoration(labelText: "Plugin ID")),
              const SizedBox(height: 8),
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: "Plugin Name")),
              const SizedBox(height: 8),
              TextField(controller: versionCtrl, decoration: const InputDecoration(labelText: "Version")),
              const SizedBox(height: 8),
              TextField(controller: descCtrl, decoration: const InputDecoration(labelText: "Description")),
              const SizedBox(height: 8),
              TextField(controller: permsCtrl, decoration: const InputDecoration(labelText: "Permissions (comma separated)")),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Init")),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final perms = permsCtrl.text
          .split(",")
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      final result = await app.api.initPluginSdk(
            destination: destinationCtrl.text.trim(),
            pluginId: pluginIdCtrl.text.trim(),
            name: nameCtrl.text.trim(),
            version: versionCtrl.text.trim().isEmpty ? "0.1.0" : versionCtrl.text.trim(),
            description: descCtrl.text.trim(),
            permissions: perms,
          );
      if (!mounted) return;
      if (result?["ok"] == true) {
        final dest = (result?["destination"] ?? "").toString();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("SDK template created: $dest")));
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Init SDK failed: ${result?["error"] ?? "unknown"}")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _upgradePlugin(InstalledPlugin plugin) async {
    final app = context.read<AppState>();
    final sourceCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text("Upgrade ${plugin.name}"),
        content: TextField(
          controller: sourceCtrl,
          decoration: const InputDecoration(
            labelText: "New package path",
            hintText: r"C:\plugins\my-plugin-v2",
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Upgrade")),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final result = await app.api.upgradePlugin(
            pluginId: plugin.id,
            sourcePath: sourceCtrl.text.trim(),
          );
      if (!mounted) return;
      if (result?["ok"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Plugin upgraded.")));
        await _refresh();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Upgrade failed: ${result?["error"] ?? "unknown"}")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rollbackPlugin(InstalledPlugin plugin) async {
    setState(() => _busy = true);
    try {
      final result = await context.read<AppState>().api.rollbackPlugin(pluginId: plugin.id);
      if (!mounted) return;
      if (result?["ok"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Plugin rolled back.")));
        await _refresh();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Rollback failed: ${result?["error"] ?? "unknown"}")));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _togglePlugin(InstalledPlugin plugin, bool enabled) async {
    final result = await context.read<AppState>().api.togglePlugin(pluginId: plugin.id, enabled: enabled);
    if (!mounted) return;
    if (result?["ok"] == true) {
      await _refresh();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Toggle failed: ${result?["error"] ?? "unknown"}")));
    }
  }

  @override
  Widget build(BuildContext context) {
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
                  child: Text(
                    "Plugin Market",
                    style: TextStyle(
                      color: Color(0xFFE8ECF2),
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                SizedBox(
                  width: 300,
                  height: 34,
                  child: TextField(
                    controller: _searchController,
                    onChanged: (v) => setState(() => _query = v.trim().toLowerCase()),
                    style: const TextStyle(color: Color(0xFFE8ECF2), fontSize: 12),
                    decoration: InputDecoration(
                      hintText: "Search plugin/provider/tool...",
                      hintStyle: const TextStyle(color: Color(0xFF99A1B3), fontSize: 12),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      filled: true,
                      fillColor: const Color(0xFF252A33),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: Color(0xFF343A46)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: Color(0xFF343A46)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: Color(0xFF0A84FF), width: 1.2),
                      ),
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _installPlugin,
                  icon: const Icon(Icons.add_box_outlined, size: 16),
                  label: const Text("Install Local"),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _initPluginSdk,
                  icon: const Icon(Icons.data_object_outlined, size: 16),
                  label: const Text("Init SDK"),
                ),
                IconButton(
                  onPressed: _busy ? null : _refresh,
                  icon: const Icon(Icons.refresh_rounded, color: Color(0xFFAAB3C2), size: 18),
                  tooltip: "Refresh",
                ),
              ],
            ),
          ),
          Expanded(
            child: FutureBuilder<_PluginMarketData>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator(color: Color(0xFF0A84FF)));
                }
                if (snapshot.hasError || !snapshot.hasData) {
                  return const Center(
                    child: Text("Failed to load plugin capabilities.", style: TextStyle(color: Color(0xFF99A1B3))),
                  );
                }
                final data = snapshot.data!;
                final providers = data.providers.where((p) {
                  if (_query.isEmpty) return true;
                  return p.name.toLowerCase().contains(_query) || p.id.toLowerCase().contains(_query);
                }).toList();
                final tools = data.tools.where((t) {
                  if (_query.isEmpty) return true;
                  return t.name.toLowerCase().contains(_query) ||
                      t.id.toLowerCase().contains(_query) ||
                      t.category.toLowerCase().contains(_query);
                }).toList();
                final plugins = data.plugins.where((p) {
                  if (_query.isEmpty) return true;
                  return p.name.toLowerCase().contains(_query) ||
                      p.id.toLowerCase().contains(_query) ||
                      p.version.toLowerCase().contains(_query);
                }).toList();

                return ListView(
                  padding: const EdgeInsets.all(14),
                  children: [
                    _ResourceCard(resources: data.resources),
                    const SizedBox(height: 12),
                    const _SectionTitle(title: "Installed Plugins"),
                    const SizedBox(height: 8),
                    if (plugins.isEmpty)
                      const _EmptyText(text: "No installed plugins.")
                    else
                      ...plugins.map((p) => _InstalledPluginCard(
                            plugin: p,
                            onToggle: (enabled) => _togglePlugin(p, enabled),
                            onUpgrade: () => _upgradePlugin(p),
                            onRollback: () => _rollbackPlugin(p),
                          )),
                    const SizedBox(height: 12),
                    const _SectionTitle(title: "LLM Providers"),
                    const SizedBox(height: 8),
                    ...providers.map((p) => _ProviderCard(provider: p)),
                    const SizedBox(height: 12),
                    const _SectionTitle(title: "Tool Capabilities"),
                    const SizedBox(height: 8),
                    ...tools.map((t) => _ToolCard(tool: t)),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _PluginMarketData {
  const _PluginMarketData({
    required this.providers,
    required this.tools,
    required this.resources,
    required this.plugins,
  });

  final List<ProviderCapability> providers;
  final List<ToolCapability> tools;
  final Map<String, dynamic> resources;
  final List<InstalledPlugin> plugins;
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(
        color: Color(0xFFE8ECF2),
        fontSize: 13,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _EmptyText extends StatelessWidget {
  const _EmptyText({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Text(text, style: const TextStyle(color: Color(0xFF99A1B3))),
    );
  }
}

class _ResourceCard extends StatelessWidget {
  const _ResourceCard({required this.resources});
  final Map<String, dynamic> resources;

  @override
  Widget build(BuildContext context) {
    final modelConc = resources["max_model_concurrency"] ?? "-";
    final splitConc = resources["max_split_concurrency"] ?? "-";
    final queueMode = resources["task_queue_mode"] ?? "-";
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        children: [
          const Icon(Icons.tune_rounded, color: Color(0xFF2A98FF), size: 18),
          const SizedBox(width: 10),
          Text("Model Concurrency: $modelConc", style: const TextStyle(color: Color(0xFFAAB3C2), fontSize: 12)),
          const SizedBox(width: 14),
          Text("Split Concurrency: $splitConc", style: const TextStyle(color: Color(0xFFAAB3C2), fontSize: 12)),
          const SizedBox(width: 14),
          Text("Queue: $queueMode", style: const TextStyle(color: Color(0xFFAAB3C2), fontSize: 12)),
        ],
      ),
    );
  }
}

class _InstalledPluginCard extends StatelessWidget {
  const _InstalledPluginCard({
    required this.plugin,
    required this.onToggle,
    required this.onUpgrade,
    required this.onRollback,
  });

  final InstalledPlugin plugin;
  final ValueChanged<bool> onToggle;
  final VoidCallback onUpgrade;
  final VoidCallback onRollback;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        children: [
          const Icon(Icons.extension_rounded, color: Color(0xFF2A98FF), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("${plugin.name}  v${plugin.version}", style: const TextStyle(color: Color(0xFFE8ECF2), fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(plugin.description.isEmpty ? plugin.id : plugin.description, style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11)),
                const SizedBox(height: 4),
                Text("Permissions: ${plugin.permissions.join(", ")}", style: const TextStyle(color: Color(0xFF7E8797), fontSize: 10)),
                const SizedBox(height: 2),
                Text("Signature: ${plugin.indexStatus}", style: const TextStyle(color: Color(0xFF7E8797), fontSize: 10)),
              ],
            ),
          ),
          Switch(
            value: plugin.enabled,
            onChanged: onToggle,
            activeThumbColor: const Color(0xFF10A37F),
          ),
          const SizedBox(width: 8),
          OutlinedButton(onPressed: onUpgrade, child: const Text("Upgrade")),
          const SizedBox(width: 6),
          OutlinedButton(onPressed: onRollback, child: const Text("Rollback")),
        ],
      ),
    );
  }
}

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({required this.provider});
  final ProviderCapability provider;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        children: [
          const Icon(Icons.hub_rounded, color: Color(0xFF2A98FF), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(provider.name, style: const TextStyle(color: Color(0xFFE8ECF2), fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(provider.defaultBaseUrl, style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11)),
              ],
            ),
          ),
          _Badge(text: provider.enabled ? "Enabled" : "Disabled"),
        ],
      ),
    );
  }
}

class _ToolCard extends StatelessWidget {
  const _ToolCard({required this.tool});
  final ToolCapability tool;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF202329),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Row(
        children: [
          const Icon(Icons.build_circle_outlined, color: Color(0xFF2A98FF), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tool.name, style: const TextStyle(color: Color(0xFFE8ECF2), fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(tool.description, style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11)),
              ],
            ),
          ),
          _Badge(text: tool.category),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF2A2E36),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFF3A3F48)),
      ),
      child: Text(
        text,
        style: const TextStyle(color: Color(0xFFAAB3C2), fontSize: 10, fontWeight: FontWeight.w700),
      ),
    );
  }
}
