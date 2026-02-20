# Rebot Code Agent — 技术评估与升级方案

---

## 第一部分：技术水平评估

### 一、综合评级

| 维度 | 评分 (10分制) | 行业对标 |
|------|:---:|------|
| **Agent 智能架构** | 7.5 | 超越 LangChain 基础、接近 MetaGPT/AutoGen |
| **代码生成能力** | 7.0 | 有异常检测+修复循环，超越多数开源方案 |
| **LLM 适配层** | 8.0 | 20+ Provider、重试/限流/DeepSeek 兼容，工业级 |
| **后端 API 架构** | 5.5 | 功能完整但单文件 2524 行，无认证/版本控制 |
| **前端 UI 架构** | 4.5 | God Object AppState 2554 行，视图文件超大 |
| **测试覆盖** | 3.0 | SDK 有基础测试，后端/前端/关键路径几乎为零 |
| **安全性** | 3.5 | 有路径穿越防护，但 CORS *、shell=True、无认证 |
| **可维护性** | 4.0 | 单文件过大、关注点未分离、大量硬编码 |
| **DevOps 成熟度** | 5.0 | Docker Compose + RabbitMQ + Redis，但无 CI/CD |
| **UI/UX 设计** | 5.5 | 暗色主题专业，但设计令牌未落地、组件未复用 |

**综合评级：5.5/10 — 原型阶段（Prototype-grade），具备独特技术亮点**

---

### 二、核心优势（技术护城河）

#### 1. CountSketch 注意力矩阵 — 业界独创
`rebot/agents/agent.py` 中使用 FNV-1a 哈希 + CountSketch 数据结构实现 O(1) 空间复杂度的上下文重要性追踪。**LangChain/CrewAI/AutoGen/MetaGPT 均无此特性。**

#### 2. 六策略上下文压缩
`none` / `recent_only` / `summary_stub` / `summary_xml` / `head_tail` / `graph_sparse`，其中 `graph_sparse` 结合注意力矩阵实现智能摘要，远超同类框架的 `ConversationSummaryMemory`。

#### 3. 异常检测 + 注意力加权修复循环
`rebot/auto/codegen.py` 实现 `detect_anomalies()` → `refine_with_anomalies()` 闭环，具备缺陷映射（`build_defect_map()`）和元策略（`build_policy()`），是独特的自纠错生成架构。

#### 4. Schema 三级修复
JSON Schema 输出解析失败时：LLM 修复 → 启发式修复 → 降级模板。3 次重试 + debug dump，比 PydanticOutputParser 更鲁棒。

#### 5. Provider 兼容层成熟度
为 DeepSeek 做了 `json_schema` → `json_object` 降级、空 assistant 消息注入等兼容处理，说明有真实生产环境打磨。

---

### 三、核心短板

#### 1. God Object 反模式（最严重）

| 文件 | 行数 | 职责数 |
|------|:---:|:---:|
| `app_state.dart` | 2,554 | ~17 个不同职责 |
| `rest.py` | 2,524 | 全部路由 + 模型 + SSE |
| `main_layout.dart` | 3,166 | 整个工作区壳 + 文件树 + 编辑器 |
| `right_panel.dart` | 3,003 | 预览 + 控制台 + 设备模拟 |
| `codegen.py` | 1,122 | 策略 + 生成 + 异常 + 修复 |
| `worker.py` | 1,168 | 队列 + 执行 + 编排 + 生成 |

单类/单文件承担过多职责，导致：
- 无法独立测试
- 修改一处影响全局
- 新开发者认知负荷极大

#### 2. 测试覆盖几乎为零

| 层级 | 代码行数 | 测试数 | 覆盖率估算 |
|------|:---:|:---:|:---:|
| `rebot/` SDK | ~6,000 | ~200 | ~15% |
| `backend/app/` | ~5,000 | 0 | 0% |
| `flutter_agentgpt/` | ~18,000 | ~37 | <1% |

关键路径 `codegen.py`、`openai_compatible.py`、`multi_agent_scheduler.py`、`AppState` 完全无测试。

#### 3. 安全漏洞

- `CORS allow_origins=["*"]` — 允许任何域名跨域访问
- `subprocess.run(shell=True)` — 命令注入风险
- API 端点无认证/授权
- `print()` 语句可能泄露敏感信息
- 无 Content Security Policy

#### 4. 前端设计令牌未落地

`AppTokens` 定义了完整的设计体系（颜色/圆角/阴影/字体），但视图中有数百处 `Color(0xFF...)` 硬编码，设计令牌形同虚设。

---

### 四、与竞品技术对比

| 能力 | Rebot | Cursor | Windsurf | Devin | bolt.new |
|------|:---:|:---:|:---:|:---:|:---:|
| 多 LLM Provider | ✅ 20+ | ✅ | ✅ | ✅ | ✅ |
| 上下文压缩 | ✅ 6策略 | ✅ | ✅ | ✅ | ❌ |
| 异常自修复 | ✅ | ❌ | ❌ | ✅ | ❌ |
| 代码预览 | ✅ WebView | ✅ | ✅ | ✅ | ✅ |
| 多Agent协作 | ✅ | ❌ | ✅ | ✅ | ❌ |
| 文件级代码生成 | ✅ | ✅ 行级 | ✅ 行级 | ✅ | ✅ |
| 内置终端 | ❌ | ✅ | ✅ | ✅ | ✅ |
| 代码编辑器 | ❌ 基础 | ✅ Monaco | ✅ Monaco | ✅ | ✅ Monaco |
| Git 集成 | ❌ | ✅ | ✅ | ✅ | ❌ |
| 测试覆盖 | ❌ | ✅ | ✅ | ✅ | ✅ |

**结论：Agent 内核技术有独特优势，但工程成熟度和 IDE 能力远落后于竞品。**

---

## 第二部分：技术升级方案

### Phase 1：工程基础加固（4 周）

#### P1.1 — 拆分 God Object

**后端：rest.py → 路由模块化**
```
backend/app/api/
  router_execution.py    # /api/execute, /api/run
  router_project.py      # /api/projects/*
  router_files.py        # /api/files/*
  router_devserver.py    # /api/devserver/*
  router_generate.py     # /api/generate
  router_agents.py       # /api/agents/*
  router_health.py       # /api/health, /api/status
  models/                # Pydantic request/response models
  deps.py                # 依赖注入（ExecutionStore, EventBus）
```

**后端：worker.py → 职责分离**
```
backend/app/
  worker/
    consumer.py          # RabbitMQ 消费者
    executor.py          # 单 Agent 执行
    multi_agent.py       # 多 Agent 编排
    generator.py         # 代码生成
    deduper.py           # 去重锁
```

**后端：codegen.py → 管道模式**
```
rebot/auto/
  codegen/
    pipeline.py          # 主管道编排
    policy.py            # 元策略
    file_generator.py    # 单文件生成
    anomaly.py           # 异常检测
    refiner.py           # 修复循环
    schema_repair.py     # JSON Schema 修复（统一）
```

**前端：AppState → Feature Notifiers**
```dart
// 每个功能域一个 ChangeNotifier
class ProjectState extends ChangeNotifier { ... }
class ConversationState extends ChangeNotifier { ... }
class FileExplorerState extends ChangeNotifier { ... }
class ExecutionState extends ChangeNotifier { ... }
class DevServerState extends ChangeNotifier { ... }
class SettingsState extends ChangeNotifier { ... }
class PreviewState extends ChangeNotifier { ... }

// main.dart 注册
MultiProvider(
  providers: [
    ChangeNotifierProvider(create: (_) => ProjectState()),
    ChangeNotifierProvider(create: (_) => ConversationState()),
    // ...
  ],
)
```

好处：每个 Notifier 的 `notifyListeners()` 只触发关心它的 widget 重建，极大减少不必要重绘。

**前端：视图文件拆分**
```
lib/views/
  workspace/
    workspace_shell.dart       # 三栏布局壳
    navigation_rail.dart       # 左侧导航
    activity_bar.dart          # 工具栏
    global_header.dart         # 顶部头
  editor/
    file_explorer.dart         # 文件树（从 main_layout 拆出）
    code_editor.dart           # 代码编辑区
    breadcrumbs.dart           # 路径导航
    editor_tabs.dart           # 文件标签页
  preview/
    preview_panel.dart         # WebView 预览
    device_simulator.dart      # 设备模拟器
    console_panel.dart         # 控制台输出
  chat/
    chat_view.dart             # 消息列表壳
    message_row.dart           # 单条消息
    message_composer.dart      # 输入框
    code_block.dart            # 代码高亮块
```

#### P1.2 — 安全加固

| 问题 | 修复 | 优先级 |
|------|------|:---:|
| CORS `*` | 改为 `["http://localhost:*"]` + 生产域名白名单 | P0 |
| shell=True | 改为 `shell=False` + `shlex.split()` 参数列表 | P0 |
| 无 API 认证 | 添加 API Key 中间件（`X-API-Key` header） | P0 |
| print() 泄露 | 替换为 `logging.debug()`，配置生产日志级别 | P1 |
| 无 CSP | 添加 `Content-Security-Policy` 响应头 | P1 |

#### P1.3 — 测试框架搭建

**后端：pytest + httpx + fixtures**
```
tests/
  backend/
    test_router_execution.py   # FastAPI TestClient
    test_worker_executor.py    # Mock LLM + 工具
    test_codegen_pipeline.py   # Mock 模型输出
    test_openai_adapter.py     # Mock httpx
    conftest.py                # 通用 fixtures
```

目标覆盖率：关键路径 > 60%。

**前端：flutter_test + mocktail**
```
test/
  state/
    test_project_state.dart
    test_conversation_state.dart
  views/
    test_chat_view.dart        # pumpWidget + mock state
    test_project_home.dart
  services/
    test_api_service.dart      # Mock HTTP
    test_sse_service.dart      # Mock stream
```

#### P1.4 — 依赖锁定与 CI

```bash
# 后端
pip-compile requirements.in -o requirements.txt   # 锁定版本
# 或迁移到 poetry

# 前端
# pubspec.lock 已自动生成，确保提交到 Git

# CI Pipeline (GitHub Actions)
# - lint (ruff / flutter analyze)
# - test (pytest / flutter test)
# - build (flutter build windows)
# - security scan (trivy)
```

---

### Phase 2：Agent 能力升级（6 周）

#### P2.1 — 结构化工具调用升级

当前工具系统是 Protocol-based，功能完整但缺少：

**a) 工具沙箱**
```python
# rebot/tools/sandbox.py
class DockerSandbox:
    """在 Docker 容器中执行用户代码/命令"""
    async def run_command(self, cmd: str, timeout: int = 30) -> str:
        # 替代 shell=True 的 subprocess
        # 资源限制：CPU 1 核、内存 512MB、网络隔离
```

**b) MCP（Model Context Protocol）支持**
```python
# rebot/tools/mcp_client.py
class MCPToolProvider:
    """从外部 MCP Server 动态发现工具"""
    async def discover_tools(self, server_url: str) -> List[BaseTool]
    async def invoke(self, tool_name: str, args: dict) -> str
```

**c) 工具调用链追踪**
```python
# rebot/tools/trace.py
class ToolTrace:
    tool_name: str
    args: dict
    result: str
    duration_ms: float
    error: Optional[str]
    parent_trace_id: Optional[str]  # 嵌套调用
```

#### P2.2 — 多 Agent 升级

当前的 `MultiAgentScheduler` 是线性管道（Planner→Coder→Reviewer）。升级为：

**a) Agent-as-Graph（图计算模型）**
```
用户任务
  ↓
[Planner Agent] ─── 生成任务 DAG
  ↓
[Router] ─── 根据任务类型分发
  ├── [Frontend Agent] ──→ UI 代码
  ├── [Backend Agent]  ──→ API/DB 代码
  ├── [Test Agent]     ──→ 测试代码
  └── [DevOps Agent]   ──→ 配置文件
  ↓
[Integrator Agent] ─── 合并 + 解冲突
  ↓
[Reviewer Agent] ─── 代码审查 + 修复建议
  ↓
[Runner Agent] ─── 执行测试 + 验证
```

**b) Agent 间通信协议**
```python
@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    type: Literal["task", "result", "review", "fix_request"]
    content: str
    artifacts: List[FileArtifact]
    trace_id: str
```

**c) 人在回路（Human-in-the-Loop）**
```python
class HumanApprovalGate:
    """在关键节点暂停，等待用户确认"""
    async def request_approval(self, context: str) -> bool
    # 前端通过 SSE 收到 approval_request 事件
    # 用户点击"确认"/"拒绝"后继续
```

#### P2.3 — 代码理解升级

**a) AST 级代码分析**
```python
# rebot/tools/code_analysis.py
class CodeAnalysisTool(BaseTool):
    """使用 tree-sitter 解析代码结构"""
    def run(self, file_path: str) -> str:
        # 返回：函数列表、类继承、导入关系、调用图
        # 让 Agent 理解项目结构后再修改
```

**b) 项目索引（Code Intelligence）**
```python
# rebot/intel/project_index.py
class ProjectIndex:
    """建立项目级代码索引"""
    symbols: Dict[str, Symbol]       # 符号表
    references: Dict[str, List[Location]]  # 引用关系
    call_graph: DiGraph              # 调用图
    
    async def find_definition(self, symbol: str) -> Location
    async def find_references(self, symbol: str) -> List[Location]
    async def get_context_for_edit(self, file: str, line: int) -> str
```

**c) Diff-based 精准编辑（替代全文件覆写）**
```python
# 升级 ReplaceInFileTool 为智能编辑
class SmartEditTool(BaseTool):
    """AST-aware 的代码编辑"""
    def run(self, file: str, edit_instruction: str) -> str:
        # 1. 解析 AST
        # 2. 定位编辑范围
        # 3. 只修改目标节点
        # 4. 保持格式/缩进/注释
```

#### P2.4 — 记忆系统升级

**a) 长期项目记忆**
```python
# rebot/memory/project_memory.py
class ProjectMemory:
    """跨会话的项目级记忆"""
    # 记住：项目架构决策、技术栈偏好、代码风格
    # 记住：过去的错误和修复方式
    # 记住：用户偏好（命名规范、注释风格）
    
    async def remember(self, key: str, knowledge: str)
    async def recall(self, query: str, top_k: int = 5) -> List[str]
```

**b) 向量存储升级（纯 Python → FAISS/Qdrant）**
```python
# 当前的 HNSWIndex 是纯 Python 实现，性能差 100x
# 升级为 FAISS（本地）或 Qdrant（分布式）
class FAISSVectorStore(VectorStore):
    """基于 FAISS 的高性能向量存储"""
    # 支持 GPU 加速
    # 支持增量更新
    # 支持元数据过滤
```

---

### Phase 3：可观测性与生产化（3 周）

#### P3.1 — 结构化日志

```python
# 替代 print() 和零散 logging
import structlog
logger = structlog.get_logger()

# 每个请求绑定 trace_id
logger.info("execution_started", 
    trace_id=trace_id, 
    model=model_name,
    task_length=len(task))
```

#### P3.2 — Metrics（Prometheus）

```python
# rebot/core/metrics.py
from prometheus_client import Counter, Histogram

llm_requests = Counter("llm_requests_total", "LLM API requests", ["provider", "model", "status"])
llm_latency = Histogram("llm_request_seconds", "LLM latency", ["provider", "model"])
codegen_files = Counter("codegen_files_total", "Files generated", ["status"])
tool_invocations = Counter("tool_invocations_total", "Tool calls", ["tool_name", "status"])
```

#### P3.3 — OpenTelemetry Tracing

```python
# 链路追踪：用户请求 → API → Worker → Agent Loop → LLM Call → Tool Call
from opentelemetry import trace
tracer = trace.get_tracer("rebot")

with tracer.start_as_current_span("agent_run") as span:
    span.set_attribute("agent.type", "coding")
    span.set_attribute("model.name", model_name)
    # ... agent loop
    with tracer.start_as_current_span("llm_call"):
        # ... LLM 调用
    with tracer.start_as_current_span("tool_execution"):
        # ... 工具执行
```

---

### Phase 4：性能与规模化（4 周）

#### P4.1 — 数据库连接池

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)
```

#### P4.2 — 缓存层

```python
# Redis 缓存热点数据
class CacheService:
    async def get_or_set(self, key: str, factory, ttl: int = 300):
        cached = await redis.get(key)
        if cached: return json.loads(cached)
        value = await factory()
        await redis.setex(key, ttl, json.dumps(value))
        return value
```

#### P4.3 — 流式生成优化

```python
# 当前是文件级生成后一次性返回
# 升级为 token 级流式输出到前端
async def generate_file_streaming(self, spec: FileSpec):
    async for chunk in self.model.astream(prompt):
        yield {"type": "file_chunk", "path": spec.path, "content": chunk}
        # 前端实时显示正在生成的文件内容
```

---

## 第三部分：UI 升级方案

### 一、现状问题分析（基于截图 + 代码）

从截图可以看到当前 UI 状态：
- 左侧：会话列表面板，显示 "New Conversation with GPT-5"
- 中间：空白主区域，只有 "Open Quickly" 搜索框
- 右侧：空白面板显示 "Not Applicable"
- 底部：消息输入框 "Message GPT-5"
- 顶部：工具栏（Tismart / main / iPhone 17 Pro / Build Succeeded）

**问题清单：**

| # | 问题 | 严重度 |
|---|------|:---:|
| 1 | 空状态无引导 — 中间、右侧大片空白，无 onboarding | 高 |
| 2 | "Not Applicable" 文案不友好 | 中 |
| 3 | 无代码编辑器 — 无法直接查看/编辑生成的代码 | 高 |
| 4 | 无内置终端 — 无法运行命令 | 高 |
| 5 | 文件树在 workspace 内才可见，首页看不到 | 中 |
| 6 | 设计令牌未落地 — 数百处硬编码颜色 | 中 |
| 7 | 无共享组件库 — 按钮/卡片/输入框各文件重复定义 | 中 |
| 8 | 无 i18n — 英文界面但代码注释是中文 | 低 |
| 9 | 预览面板右下角有残留的小窗口 | 中 |
| 10 | 三栏比例视觉不均衡 | 低 |

---

### 二、UI 升级路线图

#### Phase UI-1：空状态与 Onboarding（1 周）

**a) 首页欢迎引导**
```
┌─────────────────────────────────────────────────┐
│                                                   │
│          ✨ Welcome to Rebot IDE                  │
│                                                   │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│   │  📝 New   │  │  📂 Open  │  │  🔗 Clone │      │
│   │  Project  │  │  Project  │  │  from Git │      │
│   └──────────┘  └──────────┘  └──────────┘      │
│                                                   │
│   Recent Projects:                                │
│   ┌─────────────────────────────────────────┐    │
│   │ 🟢 Tismart       Flutter    2 min ago   │    │
│   │ ⚪ MyWebApp       React      1 hour ago  │    │
│   │ ⚪ ApiServer      FastAPI    Yesterday   │    │
│   └─────────────────────────────────────────┘    │
│                                                   │
│   💡 Tip: Describe your app idea and Rebot will  │
│      generate the entire project for you.         │
│                                                   │
└─────────────────────────────────────────────────┘
```

**b) 工作区空状态**
- 中间面板：当无文件打开时，显示快捷键提示、最近文件列表
- 右侧面板：当无预览时，显示 "Run your project to see a live preview" 而不是 "Not Applicable"
- Chat 空状态：显示 prompt 模板卡片（"Build a todo app" / "Fix the login bug" / "Add dark mode"）

**c) 生成进度可视化**
```
┌─────────────────────────────────────┐
│  🔄 Generating Project...           │
│                                     │
│  ✅ Spec compiled                   │
│  ✅ Architecture designed           │
│  🔄 Generating files... (3/12)      │
│     ├── ✅ index.html               │
│     ├── ✅ style.css                │
│     ├── 🔄 app.js    ████░░ 60%    │
│     ├── ⏳ api.py                   │
│     └── ⏳ ...8 more                │
│                                     │
│  [Cancel]                           │
└─────────────────────────────────────┘
```

#### Phase UI-2：代码编辑器集成（3 周）

**目标：集成真正的代码编辑器，对标 Cursor/Windsurf**

**方案选择：**

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|:---:|
| WebView + Monaco | 功能完整、VS Code 体验 | 需要本地 web server | ⭐ |
| flutter_code_editor | 原生 Flutter | 功能有限 | |
| re_editor | 新兴、性能好 | 社区小 | |
| WebView + CodeMirror 6 | 轻量、快 | 功能少于 Monaco | |

**推荐方案：WebView + Monaco Editor**
```
lib/views/editor/
  monaco_editor.dart       # WebView 封装 Monaco
  editor_toolbar.dart      # 撤销/重做/格式化/搜索
  editor_tabs.dart         # 多文件标签页
  diff_view.dart           # AI 修改 diff 视图
  minimap.dart             # 代码缩略图
```

**关键特性：**
- 语法高亮：200+ 语言
- IntelliSense 自动补全
- Diff 视图：AI 修改前后对比
- 行内 AI 建议（类似 Copilot inline suggestion）
- 多游标编辑
- 代码折叠

#### Phase UI-3：内置终端（2 周）

**方案：xterm.js via WebView**
```
lib/views/terminal/
  embedded_terminal.dart   # xterm.js WebView
  terminal_tabs.dart       # 多终端标签
  terminal_service.dart    # PTY 后端通信
```

后端新增：
```python
# backend/app/api/router_terminal.py
@router.websocket("/ws/terminal/{session_id}")
async def terminal_ws(ws: WebSocket, session_id: str):
    # 创建 PTY 子进程
    # 双向转发 stdin/stdout
```

#### Phase UI-4：共享组件库（2 周）

**创建 `lib/widgets/` 公共组件库：**

```
lib/widgets/
  buttons/
    rebot_button.dart          # 主按钮（实心/轮廓/Ghost）
    icon_button.dart           # 图标按钮（带 tooltip + hover）
    action_button.dart         # 小操作按钮（复制/删除/刷新）
  inputs/
    styled_text_field.dart     # 统一文本输入框
    styled_dropdown.dart       # 统一下拉框
    search_bar.dart            # 搜索栏
  layout/
    section_card.dart          # 卡片容器
    section_header.dart        # 区域标题
    empty_state.dart           # 空状态占位
    loading_skeleton.dart      # 骨架屏加载
  feedback/
    toast.dart                 # 轻提示
    error_banner.dart          # 错误横幅
    progress_indicator.dart    # 进度条
  data_display/
    status_badge.dart          # 状态徽标（运行中/成功/失败）
    file_icon.dart             # 文件类型图标
    code_block.dart            # 代码块（带复制按钮）
```

**设计令牌全面落地：**
```dart
// Before（当前状态）
Container(
  decoration: BoxDecoration(
    color: Color(0xFF212121),            // ❌ 硬编码
    borderRadius: BorderRadius.circular(8),
    border: Border.all(color: Color(0xFF333333)),
  ),
)

// After（升级后）
Container(
  decoration: BoxDecoration(
    color: AppTokens.bg,                  // ✅ 设计令牌
    borderRadius: AppTokens.radiusMd,
    border: Border.all(color: AppTokens.border),
  ),
)
```

#### Phase UI-5：交互升级（2 周）

**a) AI Diff 对话模式**
```
用户：给登录页添加记住密码功能

Agent：我将修改以下文件：

  login_page.dart  (+12 -3)
  ┌────────────────────────────────────────┐
  │ - child: ElevatedButton(              │ 红色背景
  │ + child: Column(children: [           │ 绿色背景
  │ +   CheckboxListTile(                 │
  │ +     title: Text("Remember me"),     │
  │ +     value: _rememberMe,             │
  │ +     onChanged: (v) => ...           │
  │ +   ),                                │
  │ +   ElevatedButton(                   │
  │    onPressed: _login,                  │
  └────────────────────────────────────────┘
  
  [✅ Accept All]  [❌ Reject]  [📝 Edit]
```

**b) 上下文面包屑**
```
Project: Tismart > lib > views > login_page.dart > LoginPage > build()
```

**c) Agent 思考过程可视化**
```
┌─ Agent Thinking ─────────────────────────┐
│ 🧠 Analyzing task...                     │
│ 📂 Reading login_page.dart              │
│ 🔍 Found LoginPage class at line 15     │
│ 📝 Planning: Add checkbox + state       │
│ ✏️  Editing login_page.dart (+12 -3)     │
│ 🧪 Running tests...                      │
│ ✅ All tests passed                      │
└──────────────────────────────────────────┘
```

**d) 右键上下文菜单强化**
```
文件树右键：
  ├── Edit with AI        → 打开 chat 并附加文件上下文
  ├── Explain this file   → AI 解释文件功能
  ├── Generate tests      → AI 自动生成测试
  ├── ──────────────
  ├── New File
  ├── New Folder
  ├── Rename
  └── Delete
```

#### Phase UI-6：响应式与多平台（2 周）

**a) 响应式布局**
```dart
// 根据窗口宽度自适应
if (width > 1400) → 三栏（文件树 + 编辑器 + 预览）
if (width > 1000) → 双栏（编辑器 + 预览/chat 切换）
if (width > 600)  → 单栏 + 底部导航
```

**b) macOS 适配**
- 替换 `bitsdojo_window` 为 `macos_window_utils`（或条件导入）
- 使用 `Platform.isMacOS` 切换 Cmd/Ctrl 快捷键
- 替换 `USERPROFILE` → `HOME`
- 替换 `\\` → `Platform.pathSeparator`

---

### 三、UI 升级优先级矩阵

```
         高价值
           │
    P1空状态  │  P2编辑器
    P4组件库  │  P3终端
           │  P5交互升级
  ─────────┼──────────
           │
    P6多平台 │
           │
         低价值
    低成本        高成本
```

**推荐执行顺序：**
1. **P1 空状态与 Onboarding**（1周，高价值低成本）
2. **P4 共享组件库 + 设计令牌落地**（2周，高价值中成本）
3. **P2 Monaco 代码编辑器**（3周，高价值高成本）
4. **P5 AI Diff + 思考过程可视化**（2周，高价值中成本）
5. **P3 内置终端**（2周，中价值中成本）
6. **P6 响应式与多平台**（2周，看需求）

---

### 四、总时间线

```
Month 1: 工程基础（拆分 God Object + 安全 + 测试 + CI）
Month 2: UI P1 空状态 + P4 组件库 + 开始 P2 编辑器
Month 3: UI P2 编辑器完成 + P5 AI Diff + Agent P2.1 工具沙箱
Month 4: Agent P2.2 多Agent图 + P2.3 代码理解 + UI P3 终端
Month 5: Agent P2.4 记忆系统 + Phase 3 可观测性
Month 6: Phase 4 性能优化 + UI P6 多平台 + 全面测试
```

**里程碑：**
- **M1（第4周）：** 代码质量达标 — God Object 拆分完成、测试覆盖 > 30%、安全漏洞关闭
- **M2（第8周）：** IDE 体验突破 — Monaco 编辑器 + 组件库 + 空状态引导上线
- **M3（第12周）：** Agent 能力跃升 — 工具沙箱 + AST 代码理解 + 多 Agent 图调度
- **M4（第16周）：** 生产就绪 — 可观测性 + 性能优化 + 端到端测试 > 60% 覆盖率
- **M5（第20周）：** 多平台 + 终端 — macOS 支持 + 内置终端
- **M6（第24周）：** 竞品水平 — 全面追平 Cursor/Windsurf 核心体验
