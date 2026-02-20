import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "../app_state.dart";
import "../core/l10n.dart";

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView>
    with SingleTickerProviderStateMixin {
  final _apiKey = TextEditingController();
  final _backendApiKey = TextEditingController();
  final _model = TextEditingController();
  final _llmBase = TextEditingController();
  final _backendBase = TextEditingController();
  final _modelConc = TextEditingController();
  final _runPriority = TextEditingController();
  final _maxTokenBudget = TextEditingController();
  final _maxCostBudget = TextEditingController();
  final _smokeReworkBudget = TextEditingController();
  final _plannerModel = TextEditingController();
  final _coderModel = TextEditingController();
  final _reviewerModel = TextEditingController();
  final _fixerModel = TextEditingController();
  final _splitConc = TextEditingController();
  final _maxCtx = TextEditingController();
  final _headRatio = TextEditingController();

  bool _synced = false;
  bool _hasChanges = false;
  bool _probing = false;
  late AnimationController _fadeController;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    )..forward();
  }

  @override
  void dispose() {
    _apiKey.dispose();
    _backendApiKey.dispose();
    _model.dispose();
    _llmBase.dispose();
    _backendBase.dispose();
    _modelConc.dispose();
    _runPriority.dispose();
    _maxTokenBudget.dispose();
    _maxCostBudget.dispose();
    _smokeReworkBudget.dispose();
    _plannerModel.dispose();
    _coderModel.dispose();
    _reviewerModel.dispose();
    _fixerModel.dispose();
    _splitConc.dispose();
    _maxCtx.dispose();
    _headRatio.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  void _syncFromState(AppState s) {
    if (!_synced || _apiKey.text != s.apiKey) _apiKey.text = s.apiKey;
    if (!_synced || _backendApiKey.text != s.backendApiKey) {
      _backendApiKey.text = s.backendApiKey;
    }
    if (!_synced || _model.text != s.model) _model.text = s.model;
    if (!_synced || _llmBase.text != s.llmBaseUrl) _llmBase.text = s.llmBaseUrl;
    if (!_synced || _backendBase.text != s.baseUrl) _backendBase.text = s.baseUrl;
    if (!_synced || _modelConc.text != s.modelMaxConcurrency.toString()) {
      _modelConc.text = s.modelMaxConcurrency.toString();
    }
    if (!_synced || _runPriority.text != s.runPriority.toString()) {
      _runPriority.text = s.runPriority.toString();
    }
    final tokenText = s.maxTokenBudget?.toString() ?? "";
    if (!_synced || _maxTokenBudget.text != tokenText) {
      _maxTokenBudget.text = tokenText;
    }
    final costText = s.maxCostBudget?.toString() ?? "";
    if (!_synced || _maxCostBudget.text != costText) {
      _maxCostBudget.text = costText;
    }
    final smokeBudgetText = s.smokeReworkBudget.toString();
    if (!_synced || _smokeReworkBudget.text != smokeBudgetText) {
      _smokeReworkBudget.text = smokeBudgetText;
    }
    final plannerModel = ((s.roleModelOverrides["planner"] as Map?)?["model"] ?? "").toString();
    final coderModel = ((s.roleModelOverrides["coder"] as Map?)?["model"] ?? "").toString();
    final reviewerModel = ((s.roleModelOverrides["reviewer"] as Map?)?["model"] ?? "").toString();
    final fixerModel = ((s.roleModelOverrides["fixer"] as Map?)?["model"] ?? "").toString();
    if (!_synced || _plannerModel.text != plannerModel) _plannerModel.text = plannerModel;
    if (!_synced || _coderModel.text != coderModel) _coderModel.text = coderModel;
    if (!_synced || _reviewerModel.text != reviewerModel) _reviewerModel.text = reviewerModel;
    if (!_synced || _fixerModel.text != fixerModel) _fixerModel.text = fixerModel;
    if (!_synced || _splitConc.text != s.splitMaxConcurrency.toString()) {
      _splitConc.text = s.splitMaxConcurrency.toString();
    }
    if (!_synced || _maxCtx.text != s.maxContextTokens.toString()) {
      _maxCtx.text = s.maxContextTokens.toString();
    }
    final ratio = s.contextHeadRatio.toStringAsFixed(2);
    if (!_synced || _headRatio.text != ratio) _headRatio.text = ratio;
    _synced = true;
  }

  void _markChanged() {
    if (!_hasChanges) setState(() => _hasChanges = true);
  }

  Future<void> _probeLlm(AppState state) async {
    if (_probing) return;
    setState(() => _probing = true);
    final resp = await state.api.probeLlm(
      apiKey: state.apiKey,
      provider: state.llmProvider,
      model: state.model,
      baseUrl: state.llmBaseUrl,
    );
    if (!mounted) return;
    setState(() => _probing = false);
    final ok = resp?["ok"] == true;
    final msg = ok
        ? "LLM probe success: ${resp?["provider"] ?? state.llmProvider}/${resp?["model"] ?? state.model}"
        : "LLM probe failed";
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: ok ? const Color(0xFF047857) : const Color(0xFFB91C1C),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Select only the properties that actually affect the rendered UI.
    // Mutations use context.read<AppState>() captured at call-time.
    final provider = context.select<AppState, String>((s) => s.llmProvider);
    final model = context.select<AppState, String>((s) => s.model);
    final currentModels = context.select<AppState, List<String>>((s) => s.currentModels);
    final currentApiEndpoint = context.select<AppState, String>((s) => s.currentApiEndpoint);
    final currentProviderDocUrl = context.select<AppState, String>((s) => s.currentProviderDocUrl);
    final contextCompressType = context.select<AppState, String>((s) => s.contextCompressType);
    final contextCompressTypes = context.select<AppState, List<String>>((s) => s.contextCompressTypes);
    final providerKeys = context.select<AppState, List<String>>((s) => s.providerBaseUrls.keys.toList());
    final checkpointEnabled = context.select<AppState, bool>((s) => s.checkpointEnabled);
    final smokeCheckEnabled = context.select<AppState, bool>((s) => s.smokeCheckEnabled);

    // Sync text controllers from state (only first time or on external changes)
    final state = context.read<AppState>();
    _syncFromState(state);

    return Container(
      color: const Color(0xFF171717),
      child: Column(
        children: [
          _SettingsHeader(hasChanges: _hasChanges),
          Expanded(
            child: FadeTransition(
              opacity: _fadeController,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _Section(
                      title: "LLM Configuration",
                      icon: Icons.smart_toy_outlined,
                      description: "Configure AI model and provider settings",
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const _FieldLabel("API Key"),
                          _StyledTextField(
                            controller: _apiKey,
                            obscureText: true,
                            hintText: "sk-...",
                            suffixIcon: Icons.visibility_off_outlined,
                            onChanged: (v) {
                              state.setApiKey(v);
                              _markChanged();
                            },
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Provider"),
                                    _StyledDropdown<String>(
                                      value: provider,
                                      items: providerKeys,
                                      onChanged: (v) {
                                        if (v != null) {
                                          state.setProvider(v);
                                          _llmBase.text = state.llmBaseUrl;
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Model"),
                                    _StyledDropdown<String>(
                                      value: currentModels.contains(model)
                                          ? model
                                          : currentModels.first,
                                      items: currentModels,
                                      onChanged: (v) {
                                        if (v != null) {
                                          state.setModel(v);
                                          _model.text = v;
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Model Concurrency"),
                                    _StyledTextField(
                                      controller: _modelConc,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.speed,
                                      onChanged: (v) {
                                        final n = int.tryParse(v);
                                        if (n != null) {
                                          state.setModelMaxConcurrency(n);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Split Concurrency"),
                                    _StyledTextField(
                                      controller: _splitConc,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.call_split,
                                      onChanged: (v) {
                                        final n = int.tryParse(v);
                                        if (n != null) {
                                          state.setSplitMaxConcurrency(n);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _Section(
                      title: "Endpoints",
                      icon: Icons.link,
                      description: "API endpoints and connection settings",
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const _FieldLabel("LLM Base URL"),
                          _StyledTextField(
                            controller: _llmBase,
                            hintText: "https://api.openai.com/v1",
                            prefixIcon: Icons.cloud_outlined,
                            onChanged: (v) {
                              state.setLlmBaseUrl(v);
                              _markChanged();
                            },
                          ),
                          const SizedBox(height: 12),
                          const _FieldLabel("Actual Request Endpoint"),
                          _CodeBox(text: "POST $currentApiEndpoint"),
                          if (currentProviderDocUrl.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            _HintBox(text: "Docs: $currentProviderDocUrl"),
                          ],
                          const SizedBox(height: 16),
                          const _FieldLabel("Backend API Key"),
                          _StyledTextField(
                            controller: _backendApiKey,
                            obscureText: true,
                            hintText: "Optional: server auth key",
                            suffixIcon: Icons.visibility_off_outlined,
                            onChanged: (v) {
                              state.setBackendApiKey(v);
                              _markChanged();
                            },
                          ),
                          const SizedBox(height: 16),
                          const _FieldLabel("Backend Base URL"),
                          _StyledTextField(
                            controller: _backendBase,
                            hintText: "http://localhost:8001",
                            prefixIcon: Icons.storage_outlined,
                            onChanged: (v) {
                              state.setBaseUrl(v);
                              _markChanged();
                            },
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Context Compress Type"),
                                    _StyledDropdown<String>(
                                      value: contextCompressTypes.contains(contextCompressType)
                                          ? contextCompressType
                                          : contextCompressTypes.first,
                                      items: contextCompressTypes,
                                      onChanged: (v) {
                                        if (v != null) {
                                          state.setContextCompressType(v);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Max Context Tokens"),
                                    _StyledTextField(
                                      controller: _maxCtx,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.token_outlined,
                                      onChanged: (v) {
                                        final n = int.tryParse(v);
                                        if (n != null) {
                                          state.setMaxContextTokens(n);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          const _FieldLabel("Context Head Ratio"),
                          _StyledTextField(
                            controller: _headRatio,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            prefixIcon: Icons.tune,
                            onChanged: (v) {
                              final n = double.tryParse(v);
                              if (n != null) {
                                state.setContextHeadRatio(n);
                                _markChanged();
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _Section(
                      title: "Multi-Agent Runtime",
                      icon: Icons.hub_outlined,
                      description: "Priority, budget guardrails, checkpoint and role model routing",
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Run Priority (0-10)"),
                                    _StyledTextField(
                                      controller: _runPriority,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.low_priority,
                                      onChanged: (v) {
                                        final n = int.tryParse(v);
                                        if (n != null) {
                                          state.setRunPriority(n);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Row(
                                  children: [
                                    const Icon(Icons.save_outlined, color: Color(0xFF9CA3AF), size: 16),
                                    const SizedBox(width: 8),
                                    const Text(
                                      "Enable Checkpoint",
                                      style: TextStyle(color: Color(0xFFE5E7EB), fontSize: 12, fontWeight: FontWeight.w500),
                                    ),
                                    const Spacer(),
                                    Switch(
                                      value: checkpointEnabled,
                                      onChanged: (v) {
                                        state.setCheckpointEnabled(v);
                                        _markChanged();
                                      },
                                      activeThumbColor: const Color(0xFF10A37F),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Row(
                                  children: [
                                    const Icon(Icons.science_outlined, color: Color(0xFF9CA3AF), size: 16),
                                    const SizedBox(width: 8),
                                    const Text(
                                      "Enable Smoke Gate",
                                      style: TextStyle(color: Color(0xFFE5E7EB), fontSize: 12, fontWeight: FontWeight.w500),
                                    ),
                                    const Spacer(),
                                    Switch(
                                      value: smokeCheckEnabled,
                                      onChanged: (v) {
                                        state.setSmokeCheckEnabled(v);
                                        _markChanged();
                                      },
                                      activeThumbColor: const Color(0xFF10A37F),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Smoke Rework Budget (0-3)"),
                                    _StyledTextField(
                                      controller: _smokeReworkBudget,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.restart_alt,
                                      onChanged: (v) {
                                        final n = int.tryParse(v);
                                        if (n != null) {
                                          state.setSmokeReworkBudget(n);
                                          _markChanged();
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Token Budget (optional)"),
                                    _StyledTextField(
                                      controller: _maxTokenBudget,
                                      keyboardType: TextInputType.number,
                                      prefixIcon: Icons.token_outlined,
                                      hintText: "empty = unlimited",
                                      onChanged: (v) {
                                        final raw = v.trim();
                                        final n = raw.isEmpty ? null : int.tryParse(raw);
                                        state.setMaxTokenBudget(n);
                                        _markChanged();
                                      },
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const _FieldLabel("Cost Budget USD (optional)"),
                                    _StyledTextField(
                                      controller: _maxCostBudget,
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                      prefixIcon: Icons.attach_money,
                                      hintText: "empty = unlimited",
                                      onChanged: (v) {
                                        final raw = v.trim();
                                        final n = raw.isEmpty ? null : double.tryParse(raw);
                                        state.setMaxCostBudget(n);
                                        _markChanged();
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          const _FieldLabel("Role Model Override (optional)"),
                          Row(
                            children: [
                              Expanded(
                                child: _StyledTextField(
                                  controller: _plannerModel,
                                  hintText: "planner model",
                                  onChanged: (v) {
                                    state.setRoleModelOverride("planner", v);
                                    _markChanged();
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _StyledTextField(
                                  controller: _coderModel,
                                  hintText: "coder model",
                                  onChanged: (v) {
                                    state.setRoleModelOverride("coder", v);
                                    _markChanged();
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              Expanded(
                                child: _StyledTextField(
                                  controller: _reviewerModel,
                                  hintText: "reviewer model",
                                  onChanged: (v) {
                                    state.setRoleModelOverride("reviewer", v);
                                    _markChanged();
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _StyledTextField(
                                  controller: _fixerModel,
                                  hintText: "fixer model",
                                  onChanged: (v) {
                                    state.setRoleModelOverride("fixer", v);
                                    _markChanged();
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: OutlinedButton.icon(
                              onPressed: _probing ? null : () => _probeLlm(state),
                              icon: Icon(_probing ? Icons.sync : Icons.network_check, size: 16),
                              label: Text(_probing ? "Probing..." : "Probe Current LLM"),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF10A37F),
                                side: const BorderSide(color: Color(0xFF10A37F)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    const _InfoCard(),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsHeader extends StatelessWidget {
  const _SettingsHeader({required this.hasChanges});
  final bool hasChanges;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: Color(0xFF212121),
        border: Border(bottom: BorderSide(color: Color(0xFF2A2A2A))),
      ),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: const Color(0xFF10A37F).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.settings_outlined, color: Color(0xFF10A37F), size: 18),
          ),
          const SizedBox(width: 12),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Settings",
                style: TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              Text(
                hasChanges ? S.unsavedChanges : "Configure your workspace",
                style: TextStyle(
                  color: hasChanges ? const Color(0xFFFACC15) : const Color(0xFF6E6E6E),
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const Spacer(),
          if (hasChanges)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFFFACC15).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFFACC15).withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: Color(0xFFFACC15),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    "Auto-saved",
                    style: TextStyle(color: Color(0xFFFACC15), fontSize: 11, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Section extends StatefulWidget {
  const _Section({
    required this.title,
    required this.icon,
    required this.child,
    this.description,
  });

  final String title;
  final IconData icon;
  final Widget child;
  final String? description;

  @override
  State<_Section> createState() => _SectionState();
}

class _SectionState extends State<_Section> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _hovered ? const Color(0xFF252525) : const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _hovered ? const Color(0xFF333333) : const Color(0xFF2A2A2A),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: const Color(0xFF10A37F).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(widget.icon, size: 14, color: const Color(0xFF10A37F)),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFFFFFFF),
                      ),
                    ),
                    if (widget.description != null)
                      Text(
                        widget.description!,
                        style: const TextStyle(fontSize: 11, color: Color(0xFF6E6E6E)),
                      ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 18),
            widget.child,
          ],
        ),
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: Color(0xFF9CA3AF),
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}

class _StyledTextField extends StatefulWidget {
  const _StyledTextField({
    required this.controller,
    this.hintText,
    this.obscureText = false,
    this.keyboardType,
    this.onChanged,
    this.prefixIcon,
    this.suffixIcon,
  });

  final TextEditingController controller;
  final String? hintText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;
  final IconData? prefixIcon;
  final IconData? suffixIcon;

  @override
  State<_StyledTextField> createState() => _StyledTextFieldState();
}

class _StyledTextFieldState extends State<_StyledTextField> {
  bool _focused = false;
  bool _hovered = false;
  bool _obscured = true;

  @override
  void initState() {
    super.initState();
    _obscured = widget.obscureText;
  }

  @override
  Widget build(BuildContext context) {
    final borderColor = _focused
        ? const Color(0xFF0A84FF)
        : _hovered
            ? const Color(0xFF4D5564)
            : const Color(0xFF3A3F48);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Focus(
        onFocusChange: (f) => setState(() => _focused = f),
        child: Container(
          decoration: BoxDecoration(
            color: _focused ? const Color(0xFF31343A) : const Color(0xFF262930),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: borderColor, width: _focused ? 1.5 : 1),
            boxShadow: _focused
                ? const [
                    BoxShadow(
                      color: Color(0x330A84FF),
                      blurRadius: 16,
                      offset: Offset(0, 0),
                    ),
                  ]
                : const [],
          ),
          child: TextField(
            controller: widget.controller,
            obscureText: widget.obscureText && _obscured,
            keyboardType: widget.keyboardType,
            onChanged: widget.onChanged,
            cursorColor: const Color(0xFF0A84FF),
            cursorWidth: 1.5,
            style: const TextStyle(fontSize: 13, color: Color(0xFFE6E8EE), letterSpacing: 0.2),
            decoration: InputDecoration(
              hintText: widget.hintText,
              hintStyle: const TextStyle(fontSize: 13, color: Color(0xFF8E94A3)),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              disabledBorder: InputBorder.none,
              errorBorder: InputBorder.none,
              focusedErrorBorder: InputBorder.none,
              contentPadding: EdgeInsets.only(
                left: widget.prefixIcon != null ? 0 : 14,
                right: widget.suffixIcon != null ? 0 : 14,
                top: 14,
                bottom: 14,
              ),
              isDense: true,
              prefixIcon: widget.prefixIcon != null
                  ? Icon(widget.prefixIcon, size: 16, color: const Color(0xFF8E94A3))
                  : null,
              suffixIcon: widget.obscureText
                  ? GestureDetector(
                      onTap: () => setState(() => _obscured = !_obscured),
                      child: Icon(
                        _obscured ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                        size: 16,
                        color: const Color(0xFF8E94A3),
                      ),
                    )
                  : null,
            ),
          ),
        ),
      ),
    );
  }
}

class _StyledDropdown<T> extends StatefulWidget {
  const _StyledDropdown({
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final T value;
  final List<T> items;
  final ValueChanged<T?> onChanged;

  @override
  State<_StyledDropdown<T>> createState() => _StyledDropdownState<T>();
}

class _StyledDropdownState<T> extends State<_StyledDropdown<T>> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        decoration: BoxDecoration(
          color: _hovered ? const Color(0xFF262626) : const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: _hovered ? const Color(0xFF444444) : const Color(0xFF2A2A2A)),
        ),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<T>(
            value: widget.value,
            isExpanded: true,
            dropdownColor: const Color(0xFF262626),
            icon: const Icon(Icons.expand_more, size: 18, color: Color(0xFF6E6E6E)),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            borderRadius: BorderRadius.circular(8),
            items: widget.items
                .map((item) => DropdownMenuItem(
                      value: item,
                      child: Text(
                        item.toString(),
                        style: const TextStyle(fontSize: 13, color: Color(0xFFDCDCDC)),
                      ),
                    ))
                .toList(),
            onChanged: widget.onChanged,
          ),
        ),
      ),
    );
  }
}

class _CodeBox extends StatefulWidget {
  const _CodeBox({required this.text});
  final String text;

  @override
  State<_CodeBox> createState() => _CodeBoxState();
}

class _CodeBoxState extends State<_CodeBox> {
  bool _hovered = false;
  bool _copied = false;

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.text));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: _copy,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF1E1E1E) : const Color(0xFF171717),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: _hovered ? const Color(0xFF333333) : const Color(0xFF2A2A2A)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.text,
                  style: const TextStyle(
                    fontSize: 12,
                    fontFamily: "JetBrains Mono",
                    color: Color(0xFFD1D5DB),
                  ),
                ),
              ),
              Icon(
                _copied ? Icons.check : Icons.copy_outlined,
                size: 14,
                color: _copied ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HintBox extends StatelessWidget {
  const _HintBox({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF10A37F).withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF10A37F).withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.open_in_new, size: 14, color: Color(0xFF10A37F)),
          const SizedBox(width: 8),
          Expanded(
            child: SelectableText(
              text,
              style: const TextStyle(fontSize: 12, color: Color(0xFF6EE7B7)),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFACC15).withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFACC15).withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: const Color(0xFFFACC15).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Icon(Icons.info_outline, size: 14, color: Color(0xFFFACC15)),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Auto-save enabled",
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFFFACC15)),
                ),
                SizedBox(height: 4),
                Text(
                  "Changes take effect immediately. Keys are stored locally in your desktop profile.",
                  style: TextStyle(fontSize: 11, height: 1.5, color: Color(0xFFD1A208)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

