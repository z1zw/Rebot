"""Rebot Roles Module - Multi-role collaboration framework.

This module provides:
1. Role - Base role class with observe-think-act loop
2. RoleContext - Role state and memory management
3. RoleFactory - Factory for creating predefined roles
4. RoleEncoder - Role encoding and embedding
5. Collaboration - Multi-role coordination patterns

Example usage:
    from rebot.roles import Role, RoleFactory, RoleType
    from rebot.roles.encoding import LanguageTag, TaggedInput
    from rebot.roles.collaboration import MultiRoleCoordinator, Pipeline
    
    # Create roles
    pm = RoleFactory.create(RoleType.PRODUCT_MANAGER, name="Alice")
    dev = RoleFactory.create(RoleType.BACKEND_DEV, name="Bob")
    
    # Use tagged input for many-to-many routing
    tagged = TaggedInput(
        content="实现用户登录功能",
        source_tag=LanguageTag.ZH,
        target_tag=LanguageTag.PYTHON
    )
    
    # Create pipeline
    coordinator = MultiRoleCoordinator(env)
    pipeline = coordinator.create_pipeline("dev")
    pipeline.add_stage("requirement", ["PM"])
    pipeline.add_stage("implement", ["Developer"])
"""

from rebot.roles.role import Role
from rebot.roles.context import RoleContext, RoleReactMode, Memory
from rebot.roles.factory import RoleFactory, RoleType, CapabilityMatrix
from rebot.roles.encoding import (
    LanguageTag,
    SkillTag,
    TaggedInput,
    MultiTaggedInput,
    TaggedMessage,
    RoleEncoding,
    RoleEncoder,
    RoleGraph,
    RoleRelation,
    CommunicationProtocol,
)
from rebot.roles.collaboration import (
    CollaborationPattern,
    CollaborationConfig,
    Pipeline,
    PipelineStage,
    PipelineResult,
    DelegationRequest,
    DelegationResult,
    DelegationManager,
    ConsensusManager,
    ConsensusResult,
    Vote,
    DebateManager,
    DebateResult,
    ReviewChain,
    ReviewComment,
    ReviewResult,
    MultiRoleCoordinator,
)

__all__ = [
    # Core
    "Role",
    "RoleContext",
    "RoleReactMode",
    "Memory",
    
    # Factory
    "RoleFactory",
    "RoleType",
    "CapabilityMatrix",
    
    # Encoding & Tags
    "LanguageTag",
    "SkillTag",
    "TaggedInput",
    "MultiTaggedInput",
    "TaggedMessage",
    "RoleEncoding",
    "RoleEncoder",
    "RoleGraph",
    "RoleRelation",
    "CommunicationProtocol",
    
    # Collaboration
    "CollaborationPattern",
    "CollaborationConfig",
    "Pipeline",
    "PipelineStage",
    "PipelineResult",
    "DelegationRequest",
    "DelegationResult",
    "DelegationManager",
    "ConsensusManager",
    "ConsensusResult",
    "Vote",
    "DebateManager",
    "DebateResult",
    "ReviewChain",
    "ReviewComment",
    "ReviewResult",
    "MultiRoleCoordinator",
]
