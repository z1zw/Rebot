"""Multi-role collaboration patterns and coordination strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

if TYPE_CHECKING:
    from rebot.roles.role import Role
    from rebot.environment.base import Environment
    from rebot.roles.encoding import RoleEncoding

from rebot.schema import RoutedMessage, MessageType, Task, TaskResult, Plan
from rebot.core.messages import Message
from rebot.roles.encoding import (
    TaggedInput, TaggedMessage, LanguageTag, SkillTag,
    RoleEncoder, RoleGraph, CommunicationProtocol
)

logger = logging.getLogger(__name__)


# ============================================================================
# Collaboration Patterns - 协作模式
# ============================================================================

class CollaborationPattern(str, Enum):
    """协作模式。"""
    SEQUENTIAL = "sequential"           # 顺序执行
    PARALLEL = "parallel"               # 并行执行
    PIPELINE = "pipeline"               # 管道模式
    HIERARCHICAL = "hierarchical"       # 层级模式
    CONSENSUS = "consensus"             # 共识模式
    DELEGATION = "delegation"           # 委托模式
    DEBATE = "debate"                   # 辩论模式
    REVIEW_CHAIN = "review_chain"       # 评审链


@dataclass
class CollaborationConfig:
    """协作配置。"""
    pattern: CollaborationPattern = CollaborationPattern.SEQUENTIAL
    max_iterations: int = 10
    timeout_seconds: float = 300.0
    require_unanimous: bool = False     # 是否需要一致同意
    min_approval_ratio: float = 0.5     # 最小批准比例
    allow_delegation: bool = True
    enable_feedback_loop: bool = True


# ============================================================================
# Pipeline - 管道模式
# ============================================================================

@dataclass
class PipelineStage:
    """管道阶段。"""
    name: str
    role_addresses: List[str]
    input_tags: List[str] = field(default_factory=list)
    output_tags: List[str] = field(default_factory=list)
    transformer: Optional[Callable[[Any], Any]] = None
    validator: Optional[Callable[[Any], bool]] = None
    
    def can_process(self, input_tag: str) -> bool:
        """检查是否能处理输入标签。"""
        if not self.input_tags:
            return True
        return input_tag in self.input_tags


@dataclass
class PipelineResult:
    """管道执行结果。"""
    success: bool
    stages_completed: int
    outputs: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """管道 - 多阶段处理流程。
    
    Example:
        pipeline = Pipeline()
        pipeline.add_stage("requirement", ["PM"])
        pipeline.add_stage("design", ["Architect"], input_tags=["requirement"])
        pipeline.add_stage("implement", ["Frontend", "Backend"], input_tags=["design"])
        pipeline.add_stage("test", ["QA"], input_tags=["code"])
        
        result = pipeline.execute(initial_input, env)
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.stages: List[PipelineStage] = []
        self.context: Dict[str, Any] = {}
    
    def add_stage(
        self,
        name: str,
        role_addresses: List[str],
        input_tags: List[str] = None,
        output_tags: List[str] = None,
        transformer: Callable[[Any], Any] = None,
        validator: Callable[[Any], bool] = None
    ) -> "Pipeline":
        """添加管道阶段。"""
        self.stages.append(PipelineStage(
            name=name,
            role_addresses=role_addresses,
            input_tags=input_tags or [],
            output_tags=output_tags or [],
            transformer=transformer,
            validator=validator
        ))
        return self
    
    def execute(
        self,
        initial_input: str | TaggedInput,
        env: "Environment"
    ) -> PipelineResult:
        """执行管道。"""
        result = PipelineResult(success=True, stages_completed=0)
        
        # 准备输入
        if isinstance(initial_input, str):
            current_input = TaggedInput(content=initial_input)
        else:
            current_input = initial_input
        
        current_output = current_input.content
        
        for stage in self.stages:
            logger.info(f"Pipeline stage: {stage.name}")
            
            # 检查输入标签匹配
            if stage.input_tags:
                src_tag = str(current_input.source_tag) if hasattr(current_input, 'source_tag') else "any"
                if not stage.can_process(src_tag):
                    logger.warning(f"Stage {stage.name} cannot process input tag: {src_tag}")
                    continue
            
            # 转换输入
            if stage.transformer:
                current_output = stage.transformer(current_output)
            
            # 创建消息并发送给角色
            msg = RoutedMessage(
                message=Message(role="system", content=str(current_output)),
                sent_from=f"pipeline:{self.name}",
                send_to=stage.role_addresses,
                cause_by=f"Pipeline_{stage.name}",
                msg_type=MessageType.TASK,
            )
            
            env.publish(msg)
            
            # 运行环境直到这些角色完成
            max_steps = 10
            for _ in range(max_steps):
                env.run(max_steps=1)
                
                # 检查角色是否完成
                all_idle = all(
                    env.roles.get(addr, None) is None or env.roles[addr].is_idle()
                    for addr in stage.role_addresses
                )
                if all_idle:
                    break
            
            # 收集输出
            stage_outputs = []
            for addr in stage.role_addresses:
                role = env.roles.get(addr)
                if role and role.rc.memory.count() > 0:
                    last_msg = role.rc.memory.get(1)
                    if last_msg:
                        stage_outputs.append(last_msg[-1].message.content)
            
            if stage_outputs:
                current_output = "\n".join(stage_outputs)
                result.outputs.append(current_output)
                
                # 更新输入标签
                if stage.output_tags:
                    current_input = TaggedInput(
                        content=current_output,
                        source_tag=stage.output_tags[0]
                    )
            
            # 验证
            if stage.validator and not stage.validator(current_output):
                result.success = False
                result.errors.append(f"Validation failed at stage: {stage.name}")
                break
            
            result.stages_completed += 1
        
        return result
    
    def serialize(self) -> Dict[str, Any]:
        """序列化管道定义。"""
        return {
            "name": self.name,
            "stages": [
                {
                    "name": s.name,
                    "role_addresses": s.role_addresses,
                    "input_tags": s.input_tags,
                    "output_tags": s.output_tags,
                }
                for s in self.stages
            ]
        }


# ============================================================================
# Delegation - 委托模式
# ============================================================================

@dataclass
class DelegationRequest:
    """委托请求。"""
    task_id: str
    task_description: str
    delegator: str
    required_skills: Set[str] = field(default_factory=set)
    priority: int = 0
    deadline: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    """委托结果。"""
    task_id: str
    assignee: str
    success: bool
    output: Any = None
    feedback: str = ""


class DelegationManager:
    """委托管理器 - 管理任务委托和分配。"""
    
    def __init__(self, role_encoder: Optional[RoleEncoder] = None):
        self.encoder = role_encoder or RoleEncoder()
        self.pending_requests: Dict[str, DelegationRequest] = {}
        self.assignments: Dict[str, str] = {}  # task_id -> role_address
        self.results: Dict[str, DelegationResult] = {}
    
    def delegate(
        self,
        request: DelegationRequest,
        candidate_roles: List["Role"]
    ) -> Optional[str]:
        """委托任务给最合适的角色。"""
        self.pending_requests[request.task_id] = request
        
        # 找到最适合的角色
        best_role = None
        best_score = -1
        
        for role in candidate_roles:
            if role.address == request.delegator:
                continue  # 不能委托给自己
            
            encoding = self.encoder.encode(role)
            
            # 计算匹配分数
            score = self._compute_match_score(request, encoding)
            
            if score > best_score:
                best_score = score
                best_role = role
        
        if best_role and best_score > 0:
            self.assignments[request.task_id] = best_role.address
            logger.info(f"Delegated task {request.task_id} to {best_role.address}")
            return best_role.address
        
        return None
    
    def _compute_match_score(
        self,
        request: DelegationRequest,
        encoding: "RoleEncoding"
    ) -> float:
        """计算角色与任务的匹配分数。"""
        score = 0.0
        
        # 技能匹配
        if request.required_skills:
            skill_match = sum(
                1 for skill in request.required_skills
                if encoding.matches_tag(skill)
            )
            score += skill_match / len(request.required_skills)
        else:
            score += 0.5
        
        # 能力分数
        score += encoding.capability_for("action_capacity") * 0.5
        
        return score
    
    def report_completion(
        self,
        task_id: str,
        assignee: str,
        success: bool,
        output: Any = None,
        feedback: str = ""
    ) -> None:
        """报告任务完成。"""
        self.results[task_id] = DelegationResult(
            task_id=task_id,
            assignee=assignee,
            success=success,
            output=output,
            feedback=feedback
        )
        
        # 清理
        self.pending_requests.pop(task_id, None)
        self.assignments.pop(task_id, None)
    
    def get_assignment(self, task_id: str) -> Optional[str]:
        """获取任务的分配角色。"""
        return self.assignments.get(task_id)
    
    def get_pending_for_role(self, role_address: str) -> List[DelegationRequest]:
        """获取分配给角色的待处理任务。"""
        return [
            req for task_id, req in self.pending_requests.items()
            if self.assignments.get(task_id) == role_address
        ]


# ============================================================================
# Consensus - 共识模式
# ============================================================================

@dataclass
class Vote:
    """投票。"""
    voter: str
    decision: str  # "approve", "reject", "abstain"
    confidence: float = 1.0
    reason: str = ""


@dataclass
class ConsensusResult:
    """共识结果。"""
    achieved: bool
    decision: str
    votes: List[Vote] = field(default_factory=list)
    approval_ratio: float = 0.0


class ConsensusManager:
    """共识管理器 - 管理多角色投票决策。"""
    
    def __init__(
        self,
        require_unanimous: bool = False,
        min_approval_ratio: float = 0.5
    ):
        self.require_unanimous = require_unanimous
        self.min_approval_ratio = min_approval_ratio
        self.pending_votes: Dict[str, List[Vote]] = {}
        self.required_voters: Dict[str, Set[str]] = {}
    
    def start_vote(
        self,
        topic_id: str,
        voters: List[str]
    ) -> None:
        """开始投票。"""
        self.pending_votes[topic_id] = []
        self.required_voters[topic_id] = set(voters)
    
    def cast_vote(
        self,
        topic_id: str,
        voter: str,
        decision: str,
        confidence: float = 1.0,
        reason: str = ""
    ) -> bool:
        """投票。"""
        if topic_id not in self.pending_votes:
            return False
        
        if voter not in self.required_voters.get(topic_id, set()):
            return False
        
        # 检查是否已投票
        existing = [v for v in self.pending_votes[topic_id] if v.voter == voter]
        if existing:
            return False
        
        self.pending_votes[topic_id].append(Vote(
            voter=voter,
            decision=decision,
            confidence=confidence,
            reason=reason
        ))
        return True
    
    def get_result(self, topic_id: str) -> Optional[ConsensusResult]:
        """获取投票结果。"""
        if topic_id not in self.pending_votes:
            return None
        
        votes = self.pending_votes[topic_id]
        required = self.required_voters.get(topic_id, set())
        
        # 检查是否所有人都投票了
        voters_voted = {v.voter for v in votes}
        if voters_voted != required:
            return None  # 投票未完成
        
        # 计算结果
        approve_votes = [v for v in votes if v.decision == "approve"]
        reject_votes = [v for v in votes if v.decision == "reject"]
        
        total_weight = sum(v.confidence for v in votes if v.decision != "abstain")
        approve_weight = sum(v.confidence for v in approve_votes)
        
        approval_ratio = approve_weight / total_weight if total_weight > 0 else 0
        
        if self.require_unanimous:
            achieved = len(reject_votes) == 0 and len(approve_votes) == len(votes)
        else:
            achieved = approval_ratio >= self.min_approval_ratio
        
        decision = "approved" if achieved else "rejected"
        
        return ConsensusResult(
            achieved=achieved,
            decision=decision,
            votes=votes,
            approval_ratio=approval_ratio
        )
    
    def cleanup(self, topic_id: str) -> None:
        """清理投票数据。"""
        self.pending_votes.pop(topic_id, None)
        self.required_voters.pop(topic_id, None)


# ============================================================================
# Debate - 辩论模式
# ============================================================================

@dataclass
class DebateRound:
    """辩论回合。"""
    round_number: int
    proposer: str
    proposition: str
    responses: List[Tuple[str, str]] = field(default_factory=list)  # (role, response)


@dataclass
class DebateResult:
    """辩论结果。"""
    topic: str
    rounds: List[DebateRound] = field(default_factory=list)
    conclusion: str = ""
    winner: Optional[str] = None


class DebateManager:
    """辩论管理器 - 管理多角色辩论。"""
    
    def __init__(
        self,
        max_rounds: int = 3,
        judge: Optional[str] = None
    ):
        self.max_rounds = max_rounds
        self.judge = judge
        self.active_debates: Dict[str, DebateResult] = {}
    
    def start_debate(
        self,
        topic_id: str,
        topic: str,
        initial_proposition: str,
        proposer: str
    ) -> None:
        """开始辩论。"""
        self.active_debates[topic_id] = DebateResult(
            topic=topic,
            rounds=[DebateRound(
                round_number=1,
                proposer=proposer,
                proposition=initial_proposition
            )]
        )
    
    def add_response(
        self,
        topic_id: str,
        responder: str,
        response: str
    ) -> bool:
        """添加回应。"""
        if topic_id not in self.active_debates:
            return False
        
        debate = self.active_debates[topic_id]
        if debate.rounds:
            debate.rounds[-1].responses.append((responder, response))
        return True
    
    def start_new_round(
        self,
        topic_id: str,
        proposer: str,
        proposition: str
    ) -> bool:
        """开始新回合。"""
        if topic_id not in self.active_debates:
            return False
        
        debate = self.active_debates[topic_id]
        if len(debate.rounds) >= self.max_rounds:
            return False
        
        debate.rounds.append(DebateRound(
            round_number=len(debate.rounds) + 1,
            proposer=proposer,
            proposition=proposition
        ))
        return True
    
    def conclude_debate(
        self,
        topic_id: str,
        conclusion: str,
        winner: Optional[str] = None
    ) -> Optional[DebateResult]:
        """结束辩论。"""
        if topic_id not in self.active_debates:
            return None
        
        debate = self.active_debates[topic_id]
        debate.conclusion = conclusion
        debate.winner = winner
        
        return self.active_debates.pop(topic_id)


# ============================================================================
# Review Chain - 评审链
# ============================================================================

@dataclass
class ReviewComment:
    """评审意见。"""
    reviewer: str
    content: str
    severity: str = "info"  # info, warning, error, blocker
    line_ref: Optional[str] = None


@dataclass
class ReviewResult:
    """评审结果。"""
    artifact_id: str
    approved: bool
    comments: List[ReviewComment] = field(default_factory=list)
    revisions_required: bool = False


class ReviewChain:
    """评审链 - 多级评审流程。"""
    
    def __init__(self, reviewers: List[str]):
        self.reviewers = reviewers
        self.current_reviewer_idx = 0
        self.reviews: Dict[str, List[ReviewResult]] = {}
    
    def submit_for_review(
        self,
        artifact_id: str,
        content: str,
        author: str
    ) -> str:
        """提交评审。"""
        self.reviews[artifact_id] = []
        self.current_reviewer_idx = 0
        return self.get_current_reviewer()
    
    def get_current_reviewer(self) -> Optional[str]:
        """获取当前评审者。"""
        if self.current_reviewer_idx < len(self.reviewers):
            return self.reviewers[self.current_reviewer_idx]
        return None
    
    def submit_review(
        self,
        artifact_id: str,
        reviewer: str,
        approved: bool,
        comments: List[ReviewComment] = None
    ) -> Optional[str]:
        """提交评审结果，返回下一个评审者。"""
        if artifact_id not in self.reviews:
            return None
        
        self.reviews[artifact_id].append(ReviewResult(
            artifact_id=artifact_id,
            approved=approved,
            comments=comments or [],
            revisions_required=not approved
        ))
        
        if not approved:
            # 需要修订，不继续
            return None
        
        # 下一个评审者
        self.current_reviewer_idx += 1
        return self.get_current_reviewer()
    
    def is_fully_approved(self, artifact_id: str) -> bool:
        """检查是否完全通过。"""
        if artifact_id not in self.reviews:
            return False
        
        reviews = self.reviews[artifact_id]
        if len(reviews) < len(self.reviewers):
            return False
        
        return all(r.approved for r in reviews)
    
    def get_all_comments(self, artifact_id: str) -> List[ReviewComment]:
        """获取所有评审意见。"""
        if artifact_id not in self.reviews:
            return []
        
        comments = []
        for review in self.reviews[artifact_id]:
            comments.extend(review.comments)
        return comments


# ============================================================================
# Multi-Role Coordinator - 多角色协调器
# ============================================================================

class MultiRoleCoordinator:
    """多角色协调器 - 统一管理各种协作模式。"""
    
    def __init__(
        self,
        env: "Environment",
        config: CollaborationConfig = None
    ):
        self.env = env
        self.config = config or CollaborationConfig()
        self.encoder = RoleEncoder()
        self.role_graph = RoleGraph()
        
        # 管理器
        self.delegation_manager = DelegationManager(self.encoder)
        self.consensus_manager = ConsensusManager(
            require_unanimous=self.config.require_unanimous,
            min_approval_ratio=self.config.min_approval_ratio
        )
        self.debate_manager = DebateManager()
        
        # 管道
        self.pipelines: Dict[str, Pipeline] = {}
        
        # 评审链
        self.review_chains: Dict[str, ReviewChain] = {}
    
    def register_role(self, role: "Role") -> None:
        """注册角色。"""
        self.role_graph.add_role(role)
        self.env.register_role(role)
    
    def set_hierarchy(self, leader: str, subordinate: str) -> None:
        """设置层级关系。"""
        self.role_graph.set_leader(leader, subordinate)
    
    def create_pipeline(self, name: str) -> Pipeline:
        """创建管道。"""
        pipeline = Pipeline(name)
        self.pipelines[name] = pipeline
        return pipeline
    
    def run_pipeline(
        self,
        pipeline_name: str,
        input_data: str | TaggedInput
    ) -> PipelineResult:
        """运行管道。"""
        if pipeline_name not in self.pipelines:
            return PipelineResult(success=False, stages_completed=0, 
                                  errors=[f"Pipeline not found: {pipeline_name}"])
        
        return self.pipelines[pipeline_name].execute(input_data, self.env)
    
    def delegate_task(
        self,
        task_description: str,
        delegator: str,
        required_skills: Set[str] = None
    ) -> Optional[str]:
        """委托任务。"""
        import uuid
        request = DelegationRequest(
            task_id=str(uuid.uuid4())[:8],
            task_description=task_description,
            delegator=delegator,
            required_skills=required_skills or set()
        )
        
        candidates = list(self.env.roles.values())
        return self.delegation_manager.delegate(request, candidates)
    
    def start_consensus_vote(
        self,
        topic_id: str,
        voters: List[str] = None
    ) -> None:
        """开始共识投票。"""
        if voters is None:
            voters = list(self.env.roles.keys())
        self.consensus_manager.start_vote(topic_id, voters)
    
    def execute_by_pattern(
        self,
        input_data: str | TaggedInput,
        roles: List[str] = None,
        pattern: CollaborationPattern = None
    ) -> Dict[str, Any]:
        """按指定模式执行协作。"""
        pattern = pattern or self.config.pattern
        roles = roles or list(self.env.roles.keys())
        
        if pattern == CollaborationPattern.SEQUENTIAL:
            return self._execute_sequential(input_data, roles)
        elif pattern == CollaborationPattern.PARALLEL:
            return self._execute_parallel(input_data, roles)
        elif pattern == CollaborationPattern.HIERARCHICAL:
            return self._execute_hierarchical(input_data, roles)
        elif pattern == CollaborationPattern.CONSENSUS:
            return self._execute_consensus(input_data, roles)
        else:
            return self._execute_sequential(input_data, roles)
    
    def _execute_sequential(
        self,
        input_data: str | TaggedInput,
        roles: List[str]
    ) -> Dict[str, Any]:
        """顺序执行。"""
        results = []
        current_input = input_data if isinstance(input_data, str) else input_data.content
        
        for role_addr in roles:
            role = self.env.roles.get(role_addr)
            if not role:
                continue
            
            msg = RoutedMessage(
                message=Message(role="user", content=current_input),
                sent_from="coordinator",
                send_to=[role_addr],
                msg_type=MessageType.TASK,
            )
            self.env.publish(msg)
            self.env.run(max_steps=5)
            
            # 收集输出
            if role.rc.memory.count() > 0:
                last = role.rc.memory.get(1)
                if last:
                    current_input = last[-1].message.content
                    results.append({"role": role_addr, "output": current_input})
        
        return {"pattern": "sequential", "results": results}
    
    def _execute_parallel(
        self,
        input_data: str | TaggedInput,
        roles: List[str]
    ) -> Dict[str, Any]:
        """并行执行。"""
        content = input_data if isinstance(input_data, str) else input_data.content
        
        # 发送给所有角色
        for role_addr in roles:
            msg = RoutedMessage(
                message=Message(role="user", content=content),
                sent_from="coordinator",
                send_to=[role_addr],
                msg_type=MessageType.TASK,
            )
            self.env.publish(msg)
        
        # 运行直到所有完成
        self.env.run(max_steps=10)
        
        # 收集结果
        results = []
        for role_addr in roles:
            role = self.env.roles.get(role_addr)
            if role and role.rc.memory.count() > 0:
                last = role.rc.memory.get(1)
                if last:
                    results.append({"role": role_addr, "output": last[-1].message.content})
        
        return {"pattern": "parallel", "results": results}
    
    def _execute_hierarchical(
        self,
        input_data: str | TaggedInput,
        roles: List[str]
    ) -> Dict[str, Any]:
        """层级执行。"""
        # 获取通信顺序
        order = self.role_graph.get_communication_order()
        ordered_addrs = [r.address for r in order if r.address in roles]
        
        # 按顺序执行
        return self._execute_sequential(input_data, ordered_addrs)
    
    def _execute_consensus(
        self,
        input_data: str | TaggedInput,
        roles: List[str]
    ) -> Dict[str, Any]:
        """共识执行。"""
        import uuid
        topic_id = str(uuid.uuid4())[:8]
        
        # 并行执行获取各角色意见
        parallel_result = self._execute_parallel(input_data, roles)
        
        # 开始投票
        self.consensus_manager.start_vote(topic_id, roles)
        
        # 模拟投票（实际场景中应由角色决定）
        for role_addr in roles:
            # 简单策略：有输出就批准
            role_results = [r for r in parallel_result["results"] 
                          if r["role"] == role_addr]
            decision = "approve" if role_results else "abstain"
            self.consensus_manager.cast_vote(topic_id, role_addr, decision)
        
        # 获取结果
        consensus_result = self.consensus_manager.get_result(topic_id)
        self.consensus_manager.cleanup(topic_id)
        
        return {
            "pattern": "consensus",
            "results": parallel_result["results"],
            "consensus": {
                "achieved": consensus_result.achieved if consensus_result else False,
                "decision": consensus_result.decision if consensus_result else "unknown",
                "approval_ratio": consensus_result.approval_ratio if consensus_result else 0,
            }
        }
