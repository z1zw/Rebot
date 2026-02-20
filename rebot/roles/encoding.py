"""Multi-role encoding and language tags for many-to-many collaboration.

This module implements:
1. Role encoding - Embedding representations for roles
2. Target language tags - Multi-modal routing with language/skill tags
3. Multi-role communication protocols
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from enum import Enum
import logging
import hashlib

if TYPE_CHECKING:
    from rebot.roles.role import Role

logger = logging.getLogger(__name__)


# ============================================================================
# Language/Skill Tags - 类似mBART的语言标签实现多对多路由
# ============================================================================

class LanguageTag(str, Enum):
    """语言标签 - 用于多语言/多领域路由。"""
    # 自然语言
    EN = "en_XX"      # English
    ZH = "zh_CN"      # Chinese
    JA = "ja_XX"      # Japanese
    KO = "ko_KR"      # Korean
    ES = "es_XX"      # Spanish
    FR = "fr_XX"      # French
    DE = "de_DE"      # German
    RU = "ru_RU"      # Russian
    
    # 编程语言
    PYTHON = "py_code"
    JAVASCRIPT = "js_code"
    TYPESCRIPT = "ts_code"
    JAVA = "java_code"
    CPP = "cpp_code"
    RUST = "rust_code"
    GO = "go_code"
    
    # 专业领域
    DESIGN = "design_domain"
    ARCHITECTURE = "arch_domain"
    TESTING = "test_domain"
    DEVOPS = "devops_domain"
    DATA = "data_domain"
    ML = "ml_domain"
    SECURITY = "security_domain"
    
    # 通用
    ANY = "any_XX"


class SkillTag(str, Enum):
    """技能标签 - 角色能力标识。"""
    # 开发技能
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    EMBEDDED = "embedded"
    
    # 架构技能
    SYSTEM_DESIGN = "system_design"
    API_DESIGN = "api_design"
    DATABASE = "database"
    DISTRIBUTED = "distributed"
    
    # AI技能
    LLM = "llm"
    COMPUTER_VISION = "cv"
    NLP = "nlp"
    RL = "rl"
    
    # 管理技能
    PROJECT_MANAGEMENT = "pm"
    TECHNICAL_LEAD = "tech_lead"
    CODE_REVIEW = "review"
    DOCUMENTATION = "doc"


@dataclass
class TaggedInput:
    """带标签的输入 - 实现多对多路由。
    
    格式: [source_tag] content [target_tag]
    例如: [zh_CN] 你好世界 [en_XX] -> 翻译为英文
          [py_code] def hello(): pass [js_code] -> Python转JavaScript
    """
    content: str
    source_tag: LanguageTag | SkillTag | str = LanguageTag.ANY
    target_tag: LanguageTag | SkillTag | str = LanguageTag.ANY
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt(self) -> str:
        """转换为带标签的prompt格式。"""
        src = self.source_tag.value if hasattr(self.source_tag, 'value') else str(self.source_tag)
        tgt = self.target_tag.value if hasattr(self.target_tag, 'value') else str(self.target_tag)
        return f"[{src}] {self.content} [{tgt}]"
    
    @classmethod
    def parse(cls, text: str) -> "TaggedInput":
        """从带标签的文本解析。"""
        import re
        # 匹配 [tag] content [tag] 格式
        pattern = r'\[([^\]]+)\]\s*(.+?)\s*\[([^\]]+)\]$'
        match = re.match(pattern, text.strip(), re.DOTALL)
        
        if match:
            source_tag = match.group(1)
            content = match.group(2)
            target_tag = match.group(3)
            return cls(content=content, source_tag=source_tag, target_tag=target_tag)
        
        # 没有标签，返回原始内容
        return cls(content=text)


@dataclass
class MultiTaggedInput:
    """多目标标签输入 - 支持一对多路由。"""
    content: str
    source_tag: str = "any"
    target_tags: List[str] = field(default_factory=list)
    
    def to_prompts(self) -> List[TaggedInput]:
        """生成多个单目标输入。"""
        return [
            TaggedInput(content=self.content, source_tag=self.source_tag, target_tag=tgt)
            for tgt in self.target_tags
        ]


# ============================================================================
# Role Encoding - 角色编码/嵌入
# ============================================================================

@dataclass
class RoleEncoding:
    """角色编码 - 角色的向量表示。
    
    用于：
    1. 角色匹配 - 找到最适合任务的角色
    2. 角色相似度 - 判断角色能力重叠
    3. 团队组建 - 根据互补性组建团队
    """
    role_id: str
    name: str
    profile: str
    
    # 向量表示
    embedding: List[float] = field(default_factory=list)
    
    # 技能标签
    languages: Set[LanguageTag] = field(default_factory=set)
    skills: Set[SkillTag] = field(default_factory=set)
    
    # 能力评分 (0-1)
    capability_scores: Dict[str, float] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def similarity(self, other: "RoleEncoding") -> float:
        """计算与另一个角色的相似度。"""
        if not self.embedding or not other.embedding:
            # 没有embedding时使用标签重叠度
            lang_overlap = len(self.languages & other.languages) / max(len(self.languages | other.languages), 1)
            skill_overlap = len(self.skills & other.skills) / max(len(self.skills | other.skills), 1)
            return (lang_overlap + skill_overlap) / 2
        
        # 余弦相似度
        import math
        dot = sum(a * b for a, b in zip(self.embedding, other.embedding))
        norm_a = math.sqrt(sum(a * a for a in self.embedding))
        norm_b = math.sqrt(sum(b * b for b in other.embedding))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def matches_tag(self, tag: LanguageTag | SkillTag | str) -> bool:
        """检查是否匹配标签。"""
        if isinstance(tag, LanguageTag):
            return tag in self.languages or LanguageTag.ANY in self.languages
        if isinstance(tag, SkillTag):
            return tag in self.skills
        # 字符串匹配
        tag_str = str(tag)
        return (
            any(tag_str == l.value for l in self.languages) or
            any(tag_str == s.value for s in self.skills) or
            tag_str in self.capability_scores
        )
    
    def capability_for(self, skill: str) -> float:
        """获取特定技能的能力分数。"""
        return self.capability_scores.get(skill, 0.0)


class RoleEncoder:
    """角色编码器 - 生成角色的向量表示。"""
    
    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
        dimension: int = 768
    ):
        self.embedding_fn = embedding_fn
        self.dimension = dimension
        self._cache: Dict[str, RoleEncoding] = {}
    
    def encode(self, role: "Role") -> RoleEncoding:
        """编码角色。"""
        # 检查缓存
        role_hash = self._hash_role(role)
        if role_hash in self._cache:
            return self._cache[role_hash]
        
        # 构建描述文本
        desc_parts = [
            f"Role: {role.profile}",
            f"Name: {role.name}" if role.name else "",
            f"Goal: {role.goal}" if role.goal else "",
            f"Description: {role.desc}" if role.desc else "",
            f"Actions: {', '.join(str(a) for a in role.actions)}" if role.actions else "",
        ]
        description = "\n".join(p for p in desc_parts if p)
        
        # 生成embedding
        embedding = []
        if self.embedding_fn:
            try:
                embedding = self.embedding_fn(description)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
        
        # 推断语言和技能标签
        languages = self._infer_languages(role)
        skills = self._infer_skills(role)
        
        # 生成能力评分
        capabilities = self._estimate_capabilities(role)
        
        encoding = RoleEncoding(
            role_id=role.address,
            name=role.name,
            profile=role.profile,
            embedding=embedding,
            languages=languages,
            skills=skills,
            capability_scores=capabilities,
        )
        
        self._cache[role_hash] = encoding
        return encoding
    
    def _hash_role(self, role: "Role") -> str:
        """生成角色哈希。"""
        key = f"{role.address}:{role.profile}:{role.goal}:{len(role.actions)}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _infer_languages(self, role: "Role") -> Set[LanguageTag]:
        """推断角色支持的语言。"""
        languages = {LanguageTag.ANY}
        
        profile_lower = role.profile.lower() if role.profile else ""
        desc_lower = role.desc.lower() if role.desc else ""
        combined = profile_lower + " " + desc_lower
        
        # 自然语言
        if any(w in combined for w in ["chinese", "中文", "汉语"]):
            languages.add(LanguageTag.ZH)
        if any(w in combined for w in ["english", "英文"]):
            languages.add(LanguageTag.EN)
        if any(w in combined for w in ["japanese", "日本語"]):
            languages.add(LanguageTag.JA)
        
        # 编程语言
        if any(w in combined for w in ["python", "py"]):
            languages.add(LanguageTag.PYTHON)
        if any(w in combined for w in ["javascript", "js", "node"]):
            languages.add(LanguageTag.JAVASCRIPT)
        if any(w in combined for w in ["typescript", "ts"]):
            languages.add(LanguageTag.TYPESCRIPT)
        if any(w in combined for w in ["java "]):
            languages.add(LanguageTag.JAVA)
        if any(w in combined for w in ["c++", "cpp"]):
            languages.add(LanguageTag.CPP)
        if any(w in combined for w in ["rust"]):
            languages.add(LanguageTag.RUST)
        if any(w in combined for w in ["go ", "golang"]):
            languages.add(LanguageTag.GO)
        
        return languages
    
    def _infer_skills(self, role: "Role") -> Set[SkillTag]:
        """推断角色技能。"""
        skills = set()
        
        profile_lower = role.profile.lower() if role.profile else ""
        desc_lower = role.desc.lower() if role.desc else ""
        goal_lower = role.goal.lower() if role.goal else ""
        combined = profile_lower + " " + desc_lower + " " + goal_lower
        
        if any(w in combined for w in ["frontend", "ui", "react", "vue", "css"]):
            skills.add(SkillTag.FRONTEND)
        if any(w in combined for w in ["backend", "server", "api", "database"]):
            skills.add(SkillTag.BACKEND)
        if any(w in combined for w in ["fullstack", "full-stack"]):
            skills.add(SkillTag.FULLSTACK)
        if any(w in combined for w in ["mobile", "ios", "android", "flutter"]):
            skills.add(SkillTag.MOBILE)
        
        if any(w in combined for w in ["architect", "design system", "architecture"]):
            skills.add(SkillTag.SYSTEM_DESIGN)
        if any(w in combined for w in ["api design", "interface"]):
            skills.add(SkillTag.API_DESIGN)
        if any(w in combined for w in ["database", "sql", "nosql"]):
            skills.add(SkillTag.DATABASE)
        
        if any(w in combined for w in ["llm", "language model", "gpt", "ai"]):
            skills.add(SkillTag.LLM)
        if any(w in combined for w in ["computer vision", "cv", "image"]):
            skills.add(SkillTag.COMPUTER_VISION)
        if any(w in combined for w in ["nlp", "natural language"]):
            skills.add(SkillTag.NLP)
        
        if any(w in combined for w in ["manager", "管理", "pm"]):
            skills.add(SkillTag.PROJECT_MANAGEMENT)
        if any(w in combined for w in ["lead", "leader", "tech lead"]):
            skills.add(SkillTag.TECHNICAL_LEAD)
        if any(w in combined for w in ["review", "评审"]):
            skills.add(SkillTag.CODE_REVIEW)
        if any(w in combined for w in ["document", "文档", "doc"]):
            skills.add(SkillTag.DOCUMENTATION)
        
        return skills
    
    def _estimate_capabilities(self, role: "Role") -> Dict[str, float]:
        """估算能力评分。"""
        capabilities = {}
        
        # 根据Actions估算
        action_count = len(role.actions) if role.actions else 0
        capabilities["action_capacity"] = min(action_count / 10, 1.0)
        
        # 根据描述详细程度
        desc_len = len(role.desc) if role.desc else 0
        capabilities["specification"] = min(desc_len / 500, 1.0)
        
        return capabilities
    
    def find_best_role(
        self,
        roles: List["Role"],
        target_tag: LanguageTag | SkillTag | str
    ) -> Optional["Role"]:
        """找到最适合目标标签的角色。"""
        best_role = None
        best_score = -1
        
        for role in roles:
            encoding = self.encode(role)
            if encoding.matches_tag(target_tag):
                # 计算匹配分数
                score = encoding.capability_for("action_capacity")
                if score > best_score:
                    best_score = score
                    best_role = role
        
        return best_role
    
    def find_complementary_roles(
        self,
        roles: List["Role"],
        required_skills: Set[SkillTag],
        max_team_size: int = 5
    ) -> List["Role"]:
        """找到互补的角色组建团队。"""
        covered_skills: Set[SkillTag] = set()
        team: List["Role"] = []
        
        # 按技能覆盖度排序
        role_encodings = [(role, self.encode(role)) for role in roles]
        
        while covered_skills != required_skills and len(team) < max_team_size:
            best_role = None
            best_new_skills = 0
            
            for role, encoding in role_encodings:
                if role in team:
                    continue
                
                new_skills = len(encoding.skills & required_skills - covered_skills)
                if new_skills > best_new_skills:
                    best_new_skills = new_skills
                    best_role = role
            
            if best_role is None:
                break
            
            team.append(best_role)
            enc = self.encode(best_role)
            covered_skills |= enc.skills & required_skills
        
        return team


# ============================================================================
# Multi-Role Communication Protocol
# ============================================================================

class CommunicationProtocol(str, Enum):
    """通信协议。"""
    BROADCAST = "broadcast"           # 广播给所有人
    UNICAST = "unicast"               # 点对点
    MULTICAST = "multicast"           # 组播
    TAGGED_ROUTE = "tagged_route"     # 基于标签路由
    PIPELINE = "pipeline"             # 管道模式
    PUBLISH_SUBSCRIBE = "pub_sub"     # 发布订阅


@dataclass
class TaggedMessage:
    """带标签的消息 - 支持多对多路由。"""
    content: str
    source_role: str
    source_tag: str = "any"
    target_tags: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    protocol: CommunicationProtocol = CommunicationProtocol.TAGGED_ROUTE
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_role(self, role_encoding: RoleEncoding) -> bool:
        """检查消息是否匹配角色。"""
        # 直接指定了角色
        if self.target_roles and role_encoding.role_id in self.target_roles:
            return True
        
        # 基于标签匹配
        if self.target_tags:
            for tag in self.target_tags:
                if role_encoding.matches_tag(tag):
                    return True
            return False
        
        # 广播
        if self.protocol == CommunicationProtocol.BROADCAST:
            return True
        
        return False


@dataclass
class RoleRelation:
    """角色关系定义。"""
    source_role: str
    target_role: str
    relation_type: str  # "leader", "subordinate", "peer", "consultant"
    weight: float = 1.0
    bidirectional: bool = False


class RoleGraph:
    """角色关系图 - 管理角色间的协作关系。"""
    
    def __init__(self):
        self.roles: Dict[str, "Role"] = {}
        self.relations: List[RoleRelation] = []
        self.encoder = RoleEncoder()
    
    def add_role(self, role: "Role") -> None:
        """添加角色。"""
        self.roles[role.address] = role
    
    def remove_role(self, address: str) -> None:
        """移除角色。"""
        self.roles.pop(address, None)
        self.relations = [r for r in self.relations 
                          if r.source_role != address and r.target_role != address]
    
    def add_relation(self, relation: RoleRelation) -> None:
        """添加关系。"""
        self.relations.append(relation)
        if relation.bidirectional:
            reverse = RoleRelation(
                source_role=relation.target_role,
                target_role=relation.source_role,
                relation_type=relation.relation_type,
                weight=relation.weight,
                bidirectional=False
            )
            self.relations.append(reverse)
    
    def set_leader(self, leader: str, subordinate: str) -> None:
        """设置上下级关系。"""
        self.add_relation(RoleRelation(
            source_role=leader,
            target_role=subordinate,
            relation_type="leader"
        ))
        self.add_relation(RoleRelation(
            source_role=subordinate,
            target_role=leader,
            relation_type="subordinate"
        ))
    
    def get_subordinates(self, leader_address: str) -> List["Role"]:
        """获取下属。"""
        subordinates = []
        for rel in self.relations:
            if rel.source_role == leader_address and rel.relation_type == "leader":
                if rel.target_role in self.roles:
                    subordinates.append(self.roles[rel.target_role])
        return subordinates
    
    def get_leader(self, role_address: str) -> Optional["Role"]:
        """获取上级。"""
        for rel in self.relations:
            if rel.source_role == role_address and rel.relation_type == "subordinate":
                if rel.target_role in self.roles:
                    return self.roles[rel.target_role]
        return None
    
    def get_peers(self, role_address: str) -> List["Role"]:
        """获取同级角色。"""
        peers = []
        for rel in self.relations:
            if rel.source_role == role_address and rel.relation_type == "peer":
                if rel.target_role in self.roles:
                    peers.append(self.roles[rel.target_role])
        return peers
    
    def route_by_tag(self, message: TaggedMessage) -> List["Role"]:
        """根据标签路由消息到目标角色。"""
        targets = []
        for role in self.roles.values():
            encoding = self.encoder.encode(role)
            if message.matches_role(encoding):
                targets.append(role)
        return targets
    
    def find_path(self, source: str, target: str) -> List[str]:
        """找到两个角色之间的路径。"""
        if source not in self.roles or target not in self.roles:
            return []
        
        # BFS
        visited = {source}
        queue = [(source, [source])]
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target:
                return path
            
            for rel in self.relations:
                if rel.source_role == current and rel.target_role not in visited:
                    visited.add(rel.target_role)
                    queue.append((rel.target_role, path + [rel.target_role]))
        
        return []
    
    def get_communication_order(self) -> List["Role"]:
        """获取通信顺序（拓扑排序）。"""
        # 计算入度
        in_degree = {addr: 0 for addr in self.roles}
        for rel in self.relations:
            if rel.relation_type == "leader" and rel.target_role in in_degree:
                in_degree[rel.target_role] += 1
        
        # 拓扑排序
        queue = [addr for addr, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            addr = queue.pop(0)
            order.append(self.roles[addr])
            
            for rel in self.relations:
                if rel.source_role == addr and rel.relation_type == "leader":
                    if rel.target_role in in_degree:
                        in_degree[rel.target_role] -= 1
                        if in_degree[rel.target_role] == 0:
                            queue.append(rel.target_role)
        
        return order
    
    def serialize(self) -> Dict[str, Any]:
        """序列化。"""
        return {
            "roles": list(self.roles.keys()),
            "relations": [
                {
                    "source": r.source_role,
                    "target": r.target_role,
                    "type": r.relation_type,
                    "weight": r.weight,
                }
                for r in self.relations
            ]
        }
