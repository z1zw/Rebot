"""Example demonstrating multi-role collaboration with language tags.

This example shows:
1. Creating roles with RoleFactory
2. Using language tags for many-to-many routing
3. Setting up pipelines for sequential processing
4. Using delegation for task assignment
"""

from rebot.roles import (
    Role, RoleFactory, RoleType,
    LanguageTag, SkillTag, TaggedInput,
    Pipeline, MultiRoleCoordinator, CollaborationPattern,
)
from rebot.environment.base import Environment
from rebot.schema import RoutedMessage, MessageType
from rebot.core.messages import Message
from rebot.context import Context


def example_basic_roles():
    """基本角色创建示例。"""
    print("=== 基本角色创建 ===")
    
    # 使用工厂创建预定义角色
    pm = RoleFactory.create(RoleType.PRODUCT_MANAGER, name="Alice")
    architect = RoleFactory.create(RoleType.ARCHITECT, name="Bob")
    backend = RoleFactory.create(RoleType.BACKEND_DEV, name="Charlie")
    
    print(f"PM: {pm.profile} - {pm.goal}")
    print(f"Architect: {architect.profile} - {architect.goal}")
    print(f"Backend: {backend.profile} - {backend.goal}")
    
    # 获取角色编码
    encoding = pm.get_encoding()
    print(f"PM Languages: {encoding.languages}")
    print(f"PM Skills: {encoding.skills}")


def example_language_tags():
    """语言标签示例 - 实现多对多路由。"""
    print("\n=== 语言标签路由 ===")
    
    # 创建带标签的输入
    # 中文需求 -> Python代码
    tagged1 = TaggedInput(
        content="实现一个用户登录功能，支持邮箱和手机号登录",
        source_tag=LanguageTag.ZH,
        target_tag=LanguageTag.PYTHON
    )
    print(f"Tagged Input 1: {tagged1.to_prompt()}")
    
    # Python代码 -> JavaScript代码
    tagged2 = TaggedInput(
        content="def hello(): print('Hello World')",
        source_tag=LanguageTag.PYTHON,
        target_tag=LanguageTag.JAVASCRIPT
    )
    print(f"Tagged Input 2: {tagged2.to_prompt()}")
    
    # 解析带标签的文本
    parsed = TaggedInput.parse("[en_XX] Hello World [zh_CN]")
    print(f"Parsed: source={parsed.source_tag}, target={parsed.target_tag}")
    
    # 创建带标签的消息
    msg = RoutedMessage.from_tagged_format("[py_code] print('hello') [js_code]")
    print(f"Message source_tag: {msg.source_tag}, target_tag: {msg.target_tag}")


def example_pipeline():
    """管道模式示例。"""
    print("\n=== 管道模式 ===")
    
    # 创建环境和角色
    env = Environment()
    
    pm = RoleFactory.create(RoleType.PRODUCT_MANAGER, name="PM")
    architect = RoleFactory.create(RoleType.ARCHITECT, name="Arch")
    backend = RoleFactory.create(RoleType.BACKEND_DEV, name="Dev")
    qa = RoleFactory.create(RoleType.QA_ENGINEER, name="QA")
    
    env.register_role(pm)
    env.register_role(architect)
    env.register_role(backend)
    env.register_role(qa)
    
    # 创建协调器
    coordinator = MultiRoleCoordinator(env)
    
    # 创建开发管道
    pipeline = coordinator.create_pipeline("software_dev")
    pipeline.add_stage(
        name="requirement",
        role_addresses=["Product Manager_PM"],
        output_tags=["requirement"]
    )
    pipeline.add_stage(
        name="design",
        role_addresses=["Software Architect_Arch"],
        input_tags=["requirement"],
        output_tags=["design"]
    )
    pipeline.add_stage(
        name="implement",
        role_addresses=["Backend Developer_Dev"],
        input_tags=["design"],
        output_tags=["code"]
    )
    pipeline.add_stage(
        name="test",
        role_addresses=["QA Engineer_QA"],
        input_tags=["code"],
        output_tags=["test_result"]
    )
    
    print(f"Pipeline stages: {[s.name for s in pipeline.stages]}")


def example_delegation():
    """委托模式示例。"""
    print("\n=== 委托模式 ===")
    
    from rebot.roles.collaboration import DelegationManager, DelegationRequest
    from rebot.roles.encoding import RoleEncoder
    
    # 创建角色
    roles = RoleFactory.create_software_team()
    
    # 创建委托管理器
    encoder = RoleEncoder()
    delegation = DelegationManager(encoder)
    
    # 创建任务请求
    request = DelegationRequest(
        task_id="task_001",
        task_description="Implement REST API for user authentication",
        delegator="PM",
        required_skills={SkillTag.BACKEND.value, SkillTag.API_DESIGN.value}
    )
    
    # 委托任务
    assignee = delegation.delegate(request, roles)
    print(f"Task delegated to: {assignee}")


def example_team_collaboration():
    """团队协作示例。"""
    print("\n=== 团队协作 ===")
    
    from rebot.team import Team, ScheduleStrategy
    
    # 创建上下文
    context = Context()
    
    # 创建团队
    team = Team(context=context)
    
    # 使用工厂创建标准软件团队
    roles = RoleFactory.create_software_team()
    for role in roles:
        team.hire(role)
    
    print(f"Team roles: {team.list_roles()}")
    
    # 设置调度策略
    team.config.schedule = ScheduleStrategy.DEPENDENCY
    
    # 运行项目
    # result = team.run_project("开发一个在线商城系统")


def example_consensus():
    """共识投票示例。"""
    print("\n=== 共识投票 ===")
    
    from rebot.roles.collaboration import ConsensusManager
    
    # 创建共识管理器
    consensus = ConsensusManager(
        require_unanimous=False,
        min_approval_ratio=0.6
    )
    
    # 开始投票
    voters = ["PM", "Architect", "Dev1", "Dev2", "QA"]
    consensus.start_vote("api_design_v2", voters)
    
    # 投票
    consensus.cast_vote("api_design_v2", "PM", "approve")
    consensus.cast_vote("api_design_v2", "Architect", "approve")
    consensus.cast_vote("api_design_v2", "Dev1", "approve")
    consensus.cast_vote("api_design_v2", "Dev2", "reject", reason="性能问题")
    consensus.cast_vote("api_design_v2", "QA", "approve")
    
    # 获取结果
    result = consensus.get_result("api_design_v2")
    if result:
        print(f"Consensus achieved: {result.achieved}")
        print(f"Decision: {result.decision}")
        print(f"Approval ratio: {result.approval_ratio:.2%}")


def example_review_chain():
    """评审链示例。"""
    print("\n=== 评审链 ===")
    
    from rebot.roles.collaboration import ReviewChain, ReviewComment
    
    # 创建评审链：Dev -> Tech Lead -> Architect
    reviewers = ["TechLead", "Architect"]
    chain = ReviewChain(reviewers)
    
    # 提交评审
    artifact_id = "PR_001"
    first_reviewer = chain.submit_for_review(artifact_id, "code content", "Developer")
    print(f"First reviewer: {first_reviewer}")
    
    # Tech Lead 评审
    comments = [
        ReviewComment(reviewer="TechLead", content="Add error handling", severity="warning"),
        ReviewComment(reviewer="TechLead", content="Good structure", severity="info")
    ]
    next_reviewer = chain.submit_review(artifact_id, "TechLead", True, comments)
    print(f"Next reviewer: {next_reviewer}")
    
    # Architect 评审
    chain.submit_review(artifact_id, "Architect", True)
    
    # 检查是否完全通过
    fully_approved = chain.is_fully_approved(artifact_id)
    print(f"Fully approved: {fully_approved}")
    
    # 获取所有评论
    all_comments = chain.get_all_comments(artifact_id)
    print(f"Total comments: {len(all_comments)}")


def example_role_graph():
    """角色关系图示例。"""
    print("\n=== 角色关系图 ===")
    
    from rebot.roles.encoding import RoleGraph
    
    # 创建角色
    cto = RoleFactory.create(RoleType.TECH_LEAD, name="CTO")
    architect = RoleFactory.create(RoleType.ARCHITECT, name="Architect")
    dev1 = RoleFactory.create(RoleType.BACKEND_DEV, name="Dev1")
    dev2 = RoleFactory.create(RoleType.FRONTEND_DEV, name="Dev2")
    
    # 创建关系图
    graph = RoleGraph()
    graph.add_role(cto)
    graph.add_role(architect)
    graph.add_role(dev1)
    graph.add_role(dev2)
    
    # 设置层级关系
    # CTO -> Architect -> Dev1, Dev2
    graph.set_leader(cto.address, architect.address)
    graph.set_leader(architect.address, dev1.address)
    graph.set_leader(architect.address, dev2.address)
    
    # 获取通信顺序
    order = graph.get_communication_order()
    print(f"Communication order: {[r.name for r in order]}")
    
    # 获取下属
    subordinates = graph.get_subordinates(architect.address)
    print(f"Architect's subordinates: {[r.name for r in subordinates]}")
    
    # 查找路径
    path = graph.find_path(cto.address, dev1.address)
    print(f"Path from CTO to Dev1: {path}")


if __name__ == "__main__":
    example_basic_roles()
    example_language_tags()
    example_pipeline()
    example_delegation()
    example_consensus()
    example_review_chain()
    example_role_graph()
    # example_team_collaboration()  # 需要完整的环境配置
