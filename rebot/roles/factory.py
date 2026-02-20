"""Role factory and predefined role templates for multi-role collaboration."""

from __future__ import annotations

from dataclasses import field
from typing import Any, Dict, List, Optional, Type, Callable
from enum import Enum

from rebot.roles.role import Role
from rebot.roles.encoding import LanguageTag, SkillTag, RoleEncoding
from rebot.actions.action import Action


class RoleType(str, Enum):
    """预定义角色类型。"""
    # 管理角色
    PRODUCT_MANAGER = "product_manager"
    PROJECT_MANAGER = "project_manager"
    TECH_LEAD = "tech_lead"
    
    # 设计角色
    ARCHITECT = "architect"
    UI_DESIGNER = "ui_designer"
    UX_DESIGNER = "ux_designer"
    
    # 开发角色
    FRONTEND_DEV = "frontend_developer"
    BACKEND_DEV = "backend_developer"
    FULLSTACK_DEV = "fullstack_developer"
    MOBILE_DEV = "mobile_developer"
    DATA_ENGINEER = "data_engineer"
    ML_ENGINEER = "ml_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    
    # QA角色
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    
    # 文档角色
    TECH_WRITER = "tech_writer"
    
    # 通用角色
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    ASSISTANT = "assistant"


# ============================================================================
# Role Templates - 角色模板定义
# ============================================================================

ROLE_TEMPLATES: Dict[RoleType, Dict[str, Any]] = {
    RoleType.PRODUCT_MANAGER: {
        "profile": "Product Manager",
        "goal": "Define product requirements, manage roadmap, and coordinate with stakeholders",
        "constraints": "Focus on user value and business goals",
        "desc": "Experienced product manager who analyzes user needs, defines product requirements, and creates detailed PRDs.",
        "languages": {LanguageTag.EN, LanguageTag.ZH},
        "skills": {SkillTag.PROJECT_MANAGEMENT},
        "watches": ["UserRequirement", "FeedbackAction"],
    },
    
    RoleType.PROJECT_MANAGER: {
        "profile": "Project Manager",
        "goal": "Plan and track project progress, manage resources, and ensure timely delivery",
        "constraints": "Balance scope, time, and resources",
        "desc": "Project manager who creates project plans, tracks progress, and coordinates team activities.",
        "languages": {LanguageTag.EN},
        "skills": {SkillTag.PROJECT_MANAGEMENT, SkillTag.TECHNICAL_LEAD},
        "watches": ["TaskAction", "StatusUpdate"],
    },
    
    RoleType.TECH_LEAD: {
        "profile": "Technical Lead",
        "goal": "Make technical decisions, mentor team, and ensure code quality",
        "constraints": "Balance technical excellence with delivery speed",
        "desc": "Senior technical leader who guides architecture decisions and mentors developers.",
        "languages": {LanguageTag.EN, LanguageTag.PYTHON, LanguageTag.JAVASCRIPT},
        "skills": {SkillTag.TECHNICAL_LEAD, SkillTag.SYSTEM_DESIGN, SkillTag.CODE_REVIEW},
        "watches": ["DesignAction", "CodeAction", "ReviewAction"],
    },
    
    RoleType.ARCHITECT: {
        "profile": "Software Architect",
        "goal": "Design scalable and maintainable system architecture",
        "constraints": "Consider performance, security, and maintainability",
        "desc": "System architect who designs high-level system structure, defines APIs, and creates technical specifications.",
        "languages": {LanguageTag.EN, LanguageTag.PYTHON},
        "skills": {SkillTag.SYSTEM_DESIGN, SkillTag.API_DESIGN, SkillTag.DATABASE, SkillTag.DISTRIBUTED},
        "watches": ["RequirementAction", "DesignAction"],
    },
    
    RoleType.UI_DESIGNER: {
        "profile": "UI Designer",
        "goal": "Create beautiful and intuitive user interfaces",
        "constraints": "Follow design systems and accessibility guidelines",
        "desc": "UI designer who creates visual designs, mockups, and design specifications.",
        "languages": {LanguageTag.EN, LanguageTag.DESIGN},
        "skills": {SkillTag.FRONTEND},
        "watches": ["RequirementAction", "UXDesignAction"],
    },
    
    RoleType.FRONTEND_DEV: {
        "profile": "Frontend Developer",
        "goal": "Build responsive and performant user interfaces",
        "constraints": "Write clean, tested, and accessible code",
        "desc": "Frontend developer skilled in React/Vue, HTML, CSS, and modern JavaScript.",
        "languages": {LanguageTag.JAVASCRIPT, LanguageTag.TYPESCRIPT},
        "skills": {SkillTag.FRONTEND},
        "watches": ["DesignAction", "TaskAction"],
    },
    
    RoleType.BACKEND_DEV: {
        "profile": "Backend Developer",
        "goal": "Build robust and scalable backend services",
        "constraints": "Ensure security, performance, and data integrity",
        "desc": "Backend developer skilled in Python, databases, and API development.",
        "languages": {LanguageTag.PYTHON, LanguageTag.GO},
        "skills": {SkillTag.BACKEND, SkillTag.DATABASE, SkillTag.API_DESIGN},
        "watches": ["DesignAction", "TaskAction"],
    },
    
    RoleType.FULLSTACK_DEV: {
        "profile": "Fullstack Developer",
        "goal": "Build complete web applications from frontend to backend",
        "constraints": "Maintain consistency between frontend and backend",
        "desc": "Fullstack developer with expertise in both frontend and backend technologies.",
        "languages": {LanguageTag.PYTHON, LanguageTag.JAVASCRIPT, LanguageTag.TYPESCRIPT},
        "skills": {SkillTag.FULLSTACK, SkillTag.FRONTEND, SkillTag.BACKEND},
        "watches": ["DesignAction", "TaskAction"],
    },
    
    RoleType.MOBILE_DEV: {
        "profile": "Mobile Developer",
        "goal": "Build native mobile applications for iOS and Android",
        "constraints": "Optimize for mobile performance and battery life",
        "desc": "Mobile developer skilled in Flutter, React Native, or native iOS/Android development.",
        "languages": {LanguageTag.TYPESCRIPT},
        "skills": {SkillTag.MOBILE, SkillTag.FRONTEND},
        "watches": ["DesignAction", "TaskAction"],
    },
    
    RoleType.DATA_ENGINEER: {
        "profile": "Data Engineer",
        "goal": "Build data pipelines and maintain data infrastructure",
        "constraints": "Ensure data quality, security, and compliance",
        "desc": "Data engineer skilled in ETL, data warehousing, and big data technologies.",
        "languages": {LanguageTag.PYTHON, LanguageTag.DATA},
        "skills": {SkillTag.DATABASE},
        "watches": ["DataAction", "TaskAction"],
    },
    
    RoleType.ML_ENGINEER: {
        "profile": "Machine Learning Engineer",
        "goal": "Design and deploy machine learning models",
        "constraints": "Ensure model accuracy, fairness, and efficiency",
        "desc": "ML engineer skilled in model training, MLOps, and inference optimization.",
        "languages": {LanguageTag.PYTHON, LanguageTag.ML},
        "skills": {SkillTag.LLM, SkillTag.NLP, SkillTag.COMPUTER_VISION},
        "watches": ["DataAction", "ModelAction", "TaskAction"],
    },
    
    RoleType.DEVOPS_ENGINEER: {
        "profile": "DevOps Engineer",
        "goal": "Automate deployment and maintain infrastructure",
        "constraints": "Ensure high availability and security",
        "desc": "DevOps engineer skilled in CI/CD, containerization, and cloud platforms.",
        "languages": {LanguageTag.PYTHON, LanguageTag.GO, LanguageTag.DEVOPS},
        "skills": {},
        "watches": ["DeployAction", "TaskAction"],
    },
    
    RoleType.QA_ENGINEER: {
        "profile": "QA Engineer",
        "goal": "Ensure software quality through comprehensive testing",
        "constraints": "Prioritize critical paths and edge cases",
        "desc": "QA engineer who designs test plans, writes automated tests, and reports bugs.",
        "languages": {LanguageTag.PYTHON, LanguageTag.TESTING},
        "skills": {},
        "watches": ["CodeAction", "TaskAction"],
    },
    
    RoleType.SECURITY_ENGINEER: {
        "profile": "Security Engineer",
        "goal": "Identify and mitigate security vulnerabilities",
        "constraints": "Balance security with usability",
        "desc": "Security engineer who performs security audits and implements security measures.",
        "languages": {LanguageTag.PYTHON, LanguageTag.SECURITY},
        "skills": {},
        "watches": ["CodeAction", "DesignAction"],
    },
    
    RoleType.TECH_WRITER: {
        "profile": "Technical Writer",
        "goal": "Create clear and comprehensive documentation",
        "constraints": "Write for the target audience",
        "desc": "Technical writer who creates API docs, user guides, and technical specifications.",
        "languages": {LanguageTag.EN, LanguageTag.ZH},
        "skills": {SkillTag.DOCUMENTATION},
        "watches": ["CodeAction", "DesignAction"],
    },
    
    RoleType.RESEARCHER: {
        "profile": "Researcher",
        "goal": "Research and analyze information to provide insights",
        "constraints": "Verify sources and provide balanced analysis",
        "desc": "Researcher who gathers information, analyzes data, and provides recommendations.",
        "languages": {LanguageTag.EN, LanguageTag.ZH},
        "skills": {SkillTag.NLP},
        "watches": ["ResearchAction", "TaskAction"],
    },
    
    RoleType.REVIEWER: {
        "profile": "Code Reviewer",
        "goal": "Review code for quality, security, and best practices",
        "constraints": "Provide constructive feedback",
        "desc": "Experienced developer who reviews code and provides improvement suggestions.",
        "languages": {LanguageTag.PYTHON, LanguageTag.JAVASCRIPT, LanguageTag.TYPESCRIPT},
        "skills": {SkillTag.CODE_REVIEW},
        "watches": ["CodeAction"],
    },
    
    RoleType.ASSISTANT: {
        "profile": "Assistant",
        "goal": "Help with various tasks and provide support",
        "constraints": "Be helpful and accurate",
        "desc": "General assistant who can help with various tasks.",
        "languages": {LanguageTag.EN, LanguageTag.ZH, LanguageTag.ANY},
        "skills": {},
        "watches": [],
    },
}


# ============================================================================
# Role Factory
# ============================================================================

class RoleFactory:
    """角色工厂 - 创建和管理角色实例。"""
    
    _custom_templates: Dict[str, Dict[str, Any]] = {}
    _role_classes: Dict[str, Type[Role]] = {}
    
    @classmethod
    def create(
        cls,
        role_type: RoleType | str,
        name: str = "",
        actions: List[Action] = None,
        llm: Any = None,
        **overrides
    ) -> Role:
        """创建角色实例。
        
        Args:
            role_type: 角色类型或自定义模板名
            name: 角色名称
            actions: Actions列表
            llm: LLM实例
            **overrides: 覆盖模板的属性
        
        Returns:
            Role实例
        """
        # 获取模板
        template = cls._get_template(role_type)
        
        # 合并属性
        role_kwargs = {
            "name": name or template.get("profile", ""),
            "profile": template.get("profile", ""),
            "goal": template.get("goal", ""),
            "constraints": template.get("constraints", ""),
            "desc": template.get("desc", ""),
            "actions": actions or [],
            "llm": llm,
        }
        role_kwargs.update(overrides)
        
        # 获取角色类
        role_class = cls._role_classes.get(str(role_type), Role)
        
        # 创建实例
        role = role_class(**role_kwargs)
        
        # 设置watches
        watches = template.get("watches", [])
        for watch in watches:
            role.watch(watch)
        
        return role
    
    @classmethod
    def _get_template(cls, role_type: RoleType | str) -> Dict[str, Any]:
        """获取角色模板。"""
        if isinstance(role_type, RoleType):
            return ROLE_TEMPLATES.get(role_type, {})
        
        # 尝试自定义模板
        if role_type in cls._custom_templates:
            return cls._custom_templates[role_type]
        
        # 尝试转换为RoleType
        try:
            rt = RoleType(role_type)
            return ROLE_TEMPLATES.get(rt, {})
        except ValueError:
            return {}
    
    @classmethod
    def register_template(cls, name: str, template: Dict[str, Any]) -> None:
        """注册自定义模板。"""
        cls._custom_templates[name] = template
    
    @classmethod
    def register_role_class(cls, role_type: str, role_class: Type[Role]) -> None:
        """注册自定义角色类。"""
        cls._role_classes[role_type] = role_class
    
    @classmethod
    def create_team(
        cls,
        team_config: List[Dict[str, Any]],
        llm: Any = None
    ) -> List[Role]:
        """批量创建团队角色。
        
        Args:
            team_config: 角色配置列表
            llm: 共享的LLM实例
        
        Example:
            team_config = [
                {"role_type": RoleType.PRODUCT_MANAGER, "name": "Alice"},
                {"role_type": RoleType.ARCHITECT, "name": "Bob"},
                {"role_type": RoleType.BACKEND_DEV, "name": "Charlie"},
            ]
        """
        roles = []
        for config in team_config:
            role_type = config.pop("role_type")
            role_llm = config.pop("llm", llm)
            role = cls.create(role_type, llm=role_llm, **config)
            roles.append(role)
        return roles
    
    @classmethod
    def create_software_team(cls, llm: Any = None) -> List[Role]:
        """创建标准软件开发团队。"""
        return cls.create_team([
            {"role_type": RoleType.PRODUCT_MANAGER, "name": "PM"},
            {"role_type": RoleType.ARCHITECT, "name": "Architect"},
            {"role_type": RoleType.FRONTEND_DEV, "name": "FE Developer"},
            {"role_type": RoleType.BACKEND_DEV, "name": "BE Developer"},
            {"role_type": RoleType.QA_ENGINEER, "name": "QA"},
        ], llm=llm)
    
    @classmethod
    def create_research_team(cls, llm: Any = None) -> List[Role]:
        """创建研究团队。"""
        return cls.create_team([
            {"role_type": RoleType.RESEARCHER, "name": "Lead Researcher"},
            {"role_type": RoleType.RESEARCHER, "name": "Data Analyst"},
            {"role_type": RoleType.TECH_WRITER, "name": "Writer"},
        ], llm=llm)
    
    @classmethod
    def create_ml_team(cls, llm: Any = None) -> List[Role]:
        """创建机器学习团队。"""
        return cls.create_team([
            {"role_type": RoleType.TECH_LEAD, "name": "ML Lead"},
            {"role_type": RoleType.DATA_ENGINEER, "name": "Data Engineer"},
            {"role_type": RoleType.ML_ENGINEER, "name": "ML Engineer"},
            {"role_type": RoleType.DEVOPS_ENGINEER, "name": "MLOps"},
        ], llm=llm)
    
    @classmethod
    def list_available_types(cls) -> List[str]:
        """列出所有可用的角色类型。"""
        types = [rt.value for rt in RoleType]
        types.extend(cls._custom_templates.keys())
        return types


# ============================================================================
# Role Capability Matrix
# ============================================================================

class CapabilityMatrix:
    """能力矩阵 - 管理角色能力配置。"""
    
    def __init__(self):
        self.matrix: Dict[str, Dict[str, float]] = {}
    
    def set_capability(self, role_id: str, capability: str, score: float) -> None:
        """设置角色能力分数。"""
        if role_id not in self.matrix:
            self.matrix[role_id] = {}
        self.matrix[role_id][capability] = max(0.0, min(1.0, score))
    
    def get_capability(self, role_id: str, capability: str) -> float:
        """获取角色能力分数。"""
        return self.matrix.get(role_id, {}).get(capability, 0.0)
    
    def get_best_role_for(self, capability: str, roles: List[str]) -> Optional[str]:
        """找到最擅长指定能力的角色。"""
        best_role = None
        best_score = 0.0
        
        for role_id in roles:
            score = self.get_capability(role_id, capability)
            if score > best_score:
                best_score = score
                best_role = role_id
        
        return best_role
    
    def get_coverage(self, roles: List[str], capabilities: List[str]) -> float:
        """计算角色集合对能力需求的覆盖度。"""
        if not capabilities:
            return 1.0
        
        covered = 0
        for cap in capabilities:
            max_score = max(
                (self.get_capability(r, cap) for r in roles),
                default=0.0
            )
            if max_score >= 0.5:  # 阈值
                covered += 1
        
        return covered / len(capabilities)
    
    def serialize(self) -> Dict[str, Dict[str, float]]:
        """序列化。"""
        return dict(self.matrix)
    
    @classmethod
    def deserialize(cls, data: Dict[str, Dict[str, float]]) -> "CapabilityMatrix":
        """反序列化。"""
        matrix = cls()
        matrix.matrix = data
        return matrix
