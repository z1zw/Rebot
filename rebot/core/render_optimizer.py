from __future__ import annotations

import asyncio
import hashlib
import json
import time
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Awaitable, Callable, Dict, Generic, List, 
    Optional, Set, Tuple, TypeVar, Union
)
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RenderPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    IDLE = "idle"


@dataclass
class RenderTask:
    id: str
    priority: RenderPriority
    callback: Callable[[], None]
    deadline_ms: float
    created_at: float = field(default_factory=time.time)

    @property
    def priority_value(self) -> int:
        return {
            RenderPriority.CRITICAL: 0,
            RenderPriority.HIGH: 1,
            RenderPriority.NORMAL: 2,
            RenderPriority.LOW: 3,
            RenderPriority.IDLE: 4,
        }[self.priority]


class RenderScheduler:
    FRAME_BUDGET_MS = 16.67
    
    def __init__(self):
        self._tasks: Dict[RenderPriority, List[RenderTask]] = defaultdict(list)
        self._lock = threading.RLock()
        self._frame_start: float = 0
        self._running = False

    def schedule(
        self,
        task_id: str,
        callback: Callable[[], None],
        priority: RenderPriority = RenderPriority.NORMAL,
        deadline_ms: float = 100
    ):
        task = RenderTask(
            id=task_id,
            priority=priority,
            callback=callback,
            deadline_ms=deadline_ms
        )
        with self._lock:
            self._tasks[priority].append(task)

    def _get_next_task(self) -> Optional[RenderTask]:
        with self._lock:
            for priority in RenderPriority:
                if self._tasks[priority]:
                    return self._tasks[priority].pop(0)
        return None

    def _time_remaining(self) -> float:
        return max(0, self.FRAME_BUDGET_MS - (time.time() * 1000 - self._frame_start))

    async def run_frame(self) -> int:
        self._frame_start = time.time() * 1000
        tasks_run = 0
        
        while self._time_remaining() > 1:
            task = self._get_next_task()
            if task is None:
                break
            
            try:
                task.callback()
                tasks_run += 1
            except Exception as e:
                logger.error(f"Render task {task.id} failed: {e}")
        
        return tasks_run

    async def run_loop(self):
        self._running = True
        while self._running:
            await self.run_frame()
            await asyncio.sleep(0.016)

    def stop(self):
        self._running = False


@dataclass
class VirtualNode:
    type: str
    key: Optional[str]
    props: Dict[str, Any]
    children: List[VirtualNode] = field(default_factory=list)

    def __hash__(self):
        return hash((self.type, self.key, json.dumps(self.props, sort_keys=True)))


class DiffType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    REPLACE = "replace"


@dataclass
class DiffOp:
    type: DiffType
    path: List[int]
    old_node: Optional[VirtualNode] = None
    new_node: Optional[VirtualNode] = None
    props_changed: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)


class VirtualDOMDiffer:
    def diff(
        self, 
        old_tree: Optional[VirtualNode], 
        new_tree: Optional[VirtualNode],
        path: List[int] = None
    ) -> List[DiffOp]:
        if path is None:
            path = []
        
        ops: List[DiffOp] = []
        
        if old_tree is None and new_tree is None:
            return ops
        
        if old_tree is None:
            ops.append(DiffOp(
                type=DiffType.CREATE,
                path=path,
                new_node=new_tree
            ))
            return ops
        
        if new_tree is None:
            ops.append(DiffOp(
                type=DiffType.DELETE,
                path=path,
                old_node=old_tree
            ))
            return ops
        
        if old_tree.type != new_tree.type:
            ops.append(DiffOp(
                type=DiffType.REPLACE,
                path=path,
                old_node=old_tree,
                new_node=new_tree
            ))
            return ops
        
        props_changed = self._diff_props(old_tree.props, new_tree.props)
        if props_changed:
            ops.append(DiffOp(
                type=DiffType.UPDATE,
                path=path,
                old_node=old_tree,
                new_node=new_tree,
                props_changed=props_changed
            ))
        
        child_ops = self._diff_children(
            old_tree.children,
            new_tree.children,
            path
        )
        ops.extend(child_ops)
        
        return ops

    def _diff_props(
        self, 
        old_props: Dict[str, Any], 
        new_props: Dict[str, Any]
    ) -> Dict[str, Tuple[Any, Any]]:
        changed = {}
        all_keys = set(old_props.keys()) | set(new_props.keys())
        
        for key in all_keys:
            old_val = old_props.get(key)
            new_val = new_props.get(key)
            if old_val != new_val:
                changed[key] = (old_val, new_val)
        
        return changed

    def _diff_children(
        self,
        old_children: List[VirtualNode],
        new_children: List[VirtualNode],
        parent_path: List[int]
    ) -> List[DiffOp]:
        ops: List[DiffOp] = []
        
        old_keyed = {
            c.key: (i, c) for i, c in enumerate(old_children) if c.key
        }
        new_keyed = {
            c.key: (i, c) for i, c in enumerate(new_children) if c.key
        }
        
        for key in old_keyed:
            if key not in new_keyed:
                old_idx, old_child = old_keyed[key]
                ops.append(DiffOp(
                    type=DiffType.DELETE,
                    path=parent_path + [old_idx],
                    old_node=old_child
                ))
        
        for key in new_keyed:
            if key not in old_keyed:
                new_idx, new_child = new_keyed[key]
                ops.append(DiffOp(
                    type=DiffType.CREATE,
                    path=parent_path + [new_idx],
                    new_node=new_child
                ))
            else:
                old_idx, old_child = old_keyed[key]
                new_idx, new_child = new_keyed[key]
                
                if old_idx != new_idx:
                    ops.append(DiffOp(
                        type=DiffType.MOVE,
                        path=parent_path + [new_idx],
                        old_node=old_child,
                        new_node=new_child
                    ))
                
                child_ops = self.diff(
                    old_child, 
                    new_child, 
                    parent_path + [new_idx]
                )
                ops.extend(child_ops)
        
        old_unkeyed = [c for c in old_children if not c.key]
        new_unkeyed = [c for c in new_children if not c.key]
        
        max_len = max(len(old_unkeyed), len(new_unkeyed))
        for i in range(max_len):
            old_child = old_unkeyed[i] if i < len(old_unkeyed) else None
            new_child = new_unkeyed[i] if i < len(new_unkeyed) else None
            
            child_path = parent_path + [len(old_keyed) + i]
            child_ops = self.diff(old_child, new_child, child_path)
            ops.extend(child_ops)
        
        return ops


class PatchOperation:
    def __init__(self, ops: List[DiffOp]):
        self.ops = sorted(ops, key=self._op_priority)

    def _op_priority(self, op: DiffOp) -> Tuple[int, int]:
        type_priority = {
            DiffType.DELETE: 0,
            DiffType.MOVE: 1,
            DiffType.CREATE: 2,
            DiffType.REPLACE: 3,
            DiffType.UPDATE: 4,
        }
        depth = len(op.path)
        return (type_priority[op.type], -depth if op.type == DiffType.DELETE else depth)

    def apply(self, apply_fn: Callable[[DiffOp], None]):
        for op in self.ops:
            try:
                apply_fn(op)
            except Exception as e:
                logger.error(f"Patch operation failed: {op.type} at {op.path}: {e}")


@dataclass
class AnimationConfig:
    duration_ms: float = 200
    easing: str = "ease-out"
    delay_ms: float = 0


class AnimationType(str, Enum):
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    TYPING = "typing"
    SHIMMER = "shimmer"


@dataclass
class Animation:
    type: AnimationType
    target_id: str
    config: AnimationConfig = field(default_factory=AnimationConfig)
    start_time: float = field(default_factory=time.time)
    progress: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.start_time) * 1000 - self.config.delay_ms

    @property
    def is_complete(self) -> bool:
        return self.elapsed_ms >= self.config.duration_ms

    def calculate_progress(self) -> float:
        if self.elapsed_ms < 0:
            return 0.0
        t = min(1.0, self.elapsed_ms / self.config.duration_ms)
        return self._apply_easing(t)

    def _apply_easing(self, t: float) -> float:
        if self.config.easing == "linear":
            return t
        elif self.config.easing == "ease-in":
            return t * t
        elif self.config.easing == "ease-out":
            return 1 - (1 - t) ** 2
        elif self.config.easing == "ease-in-out":
            return 3 * t ** 2 - 2 * t ** 3
        elif self.config.easing == "bounce":
            if t < 0.5:
                return 4 * t ** 3
            else:
                return 1 - ((-2 * t + 2) ** 3) / 2
        return t


class AnimationController:
    def __init__(self):
        self._active: Dict[str, Animation] = {}
        self._queued: List[Animation] = []
        self._lock = threading.RLock()

    def start(
        self,
        animation_type: AnimationType,
        target_id: str,
        config: Optional[AnimationConfig] = None
    ) -> Animation:
        animation = Animation(
            type=animation_type,
            target_id=target_id,
            config=config or AnimationConfig()
        )
        with self._lock:
            self._active[target_id] = animation
        return animation

    def queue(
        self,
        animation_type: AnimationType,
        target_id: str,
        config: Optional[AnimationConfig] = None
    ):
        animation = Animation(
            type=animation_type,
            target_id=target_id,
            config=config or AnimationConfig()
        )
        with self._lock:
            self._queued.append(animation)

    def tick(self) -> List[Animation]:
        completed = []
        with self._lock:
            for target_id, anim in list(self._active.items()):
                anim.progress = anim.calculate_progress()
                if anim.is_complete:
                    completed.append(anim)
                    del self._active[target_id]
            
            if self._queued and not self._active:
                next_anim = self._queued.pop(0)
                next_anim.start_time = time.time()
                self._active[next_anim.target_id] = next_anim
        
        return completed

    def get_progress(self, target_id: str) -> Optional[float]:
        with self._lock:
            if target_id in self._active:
                return self._active[target_id].progress
        return None

    def cancel(self, target_id: str) -> bool:
        with self._lock:
            if target_id in self._active:
                del self._active[target_id]
                return True
        return False

    def cancel_all(self):
        with self._lock:
            self._active.clear()
            self._queued.clear()


class TypingAnimator:
    def __init__(self, chars_per_second: float = 50):
        self.chars_per_second = chars_per_second
        self._active: Dict[str, Tuple[str, int, float]] = {}
        self._lock = threading.RLock()

    def start(self, target_id: str, full_text: str):
        with self._lock:
            self._active[target_id] = (full_text, 0, time.time())

    def tick(self, target_id: str) -> Optional[str]:
        with self._lock:
            if target_id not in self._active:
                return None
            
            full_text, last_pos, start_time = self._active[target_id]
            elapsed = time.time() - start_time
            target_pos = int(elapsed * self.chars_per_second)
            
            if target_pos >= len(full_text):
                del self._active[target_id]
                return full_text
            
            if target_pos > last_pos:
                self._active[target_id] = (full_text, target_pos, start_time)
                return full_text[:target_pos]
            
            return None

    def get_current(self, target_id: str) -> Optional[str]:
        with self._lock:
            if target_id not in self._active:
                return None
            full_text, pos, _ = self._active[target_id]
            return full_text[:pos]

    def is_complete(self, target_id: str) -> bool:
        with self._lock:
            return target_id not in self._active


class IncrementalRenderer:
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.differ = VirtualDOMDiffer()
        self.scheduler = RenderScheduler()
        self.animations = AnimationController()
        self._current_tree: Optional[VirtualNode] = None

    def render(
        self,
        new_tree: VirtualNode,
        apply_fn: Callable[[DiffOp], None]
    ) -> int:
        ops = self.differ.diff(self._current_tree, new_tree)
        self._current_tree = new_tree
        
        if not ops:
            return 0
        
        patch = PatchOperation(ops)
        
        applied = 0
        for i, op in enumerate(patch.ops):
            priority = RenderPriority.CRITICAL if i < 3 else RenderPriority.NORMAL
            
            def create_task(operation=op):
                apply_fn(operation)
            
            self.scheduler.schedule(
                task_id=f"patch_{i}",
                callback=create_task,
                priority=priority
            )
            applied += 1
        
        return applied

    async def render_async(
        self,
        new_tree: VirtualNode,
        apply_fn: Callable[[DiffOp], None]
    ) -> int:
        count = self.render(new_tree, apply_fn)
        await self.scheduler.run_frame()
        return count


class MessageStreamRenderer:
    def __init__(
        self,
        typing_speed: float = 60,
        batch_delay_ms: float = 16.67
    ):
        self.typing = TypingAnimator(chars_per_second=typing_speed)
        self.animations = AnimationController()
        self.batch_delay_ms = batch_delay_ms
        self._buffer: Dict[str, str] = {}
        self._rendered: Dict[str, str] = {}
        self._lock = threading.RLock()

    def append(self, message_id: str, content: str):
        with self._lock:
            self._buffer[message_id] = self._buffer.get(message_id, "") + content

    def get_display_content(self, message_id: str) -> str:
        with self._lock:
            buffered = self._buffer.get(message_id, "")
            rendered = self._rendered.get(message_id, "")
            
            if len(buffered) > len(rendered):
                chunk_size = max(1, int(60 * self.batch_delay_ms / 1000))
                new_rendered = buffered[:len(rendered) + chunk_size]
                self._rendered[message_id] = new_rendered
                return new_rendered
            
            return rendered

    def is_complete(self, message_id: str) -> bool:
        with self._lock:
            return (
                message_id in self._buffer and
                self._buffer.get(message_id, "") == self._rendered.get(message_id, "")
            )

    def complete(self, message_id: str):
        with self._lock:
            if message_id in self._buffer:
                self._rendered[message_id] = self._buffer[message_id]


def create_render_scheduler() -> RenderScheduler:
    return RenderScheduler()


def create_dom_differ() -> VirtualDOMDiffer:
    return VirtualDOMDiffer()


def create_animation_controller() -> AnimationController:
    return AnimationController()


def create_incremental_renderer() -> IncrementalRenderer:
    return IncrementalRenderer()


def create_message_renderer(typing_speed: float = 60) -> MessageStreamRenderer:
    return MessageStreamRenderer(typing_speed=typing_speed)


class RenderOptimizationSuite:
    def __init__(self):
        self.scheduler = create_render_scheduler()
        self.differ = create_dom_differ()
        self.animations = create_animation_controller()
        self.incremental = create_incremental_renderer()
        self.message_renderer = create_message_renderer()

    def optimize_tree_update(
        self,
        old_tree: Optional[VirtualNode],
        new_tree: VirtualNode,
        apply_fn: Callable[[DiffOp], None]
    ) -> List[DiffOp]:
        ops = self.differ.diff(old_tree, new_tree)
        patch = PatchOperation(ops)
        
        for op in patch.ops:
            if op.type == DiffType.CREATE:
                self.animations.start(
                    AnimationType.FADE_IN,
                    f"node_{op.path}",
                    AnimationConfig(duration_ms=150)
                )
            elif op.type == DiffType.DELETE:
                self.animations.start(
                    AnimationType.FADE_OUT,
                    f"node_{op.path}",
                    AnimationConfig(duration_ms=100)
                )
        
        patch.apply(apply_fn)
        return ops

    def render_streaming_message(
        self,
        message_id: str,
        delta: str
    ) -> str:
        self.message_renderer.append(message_id, delta)
        return self.message_renderer.get_display_content(message_id)

    def tick_animations(self) -> List[Animation]:
        return self.animations.tick()


def create_optimization_suite() -> RenderOptimizationSuite:
    return RenderOptimizationSuite()
