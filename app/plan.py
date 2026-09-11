import errno
import hashlib
import json
import os
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from .project import get_project_state_directory
from .settings import settings

PlanReviewOutcome = Literal["completed", "retry", "failed", "skipped"]
_REVIEW_OUTCOMES = frozenset({"completed", "retry", "failed", "skipped"})
_FINISHED_STEP_STATUSES = frozenset({"completed", "skipped"})
_REVISION_SKIP_STATUSES = frozenset({"pending", "in_progress", "failed"})


class PlanStateError(RuntimeError):
    """Raised when plan state or a requested state transition is invalid."""


def _now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


def _text(value: object, name: str) -> str:
    """Validate and normalize a required non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise PlanStateError(f"{name} must be a non-empty string.")
    return value.strip()


def _optional_text(value: object) -> str | None:
    """Normalize optional text and collapse blank values to None."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _positive_int(value: object, name: str) -> int:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PlanStateError(f"{name} must be a positive integer.")
    return value


@contextmanager
def _interprocess_lock(target: Path) -> Iterator[None]:
    """Serialize plan-state transactions across OS processes."""
    lock_path = target.with_name(f".{target.name}.lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
    except OSError as exc:
        raise PlanStateError(f"Cannot open plan lock {lock_path}: {exc}") from exc
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    # Existing Windows locks surface as EACCES/EAGAIN; retry only those.
                    if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                        raise
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise PlanStateError(f"Cannot lock plan state {target}: {exc}") from exc
    finally:
        handle.close()


def _normalize_steps(value: object, *, revised: bool = False) -> list[tuple[str, str]]:
    """Validate and normalize plan step definitions."""
    label = "A revised plan" if revised else "A plan"
    if not isinstance(value, list) or not value:
        raise PlanStateError(f"{label} must contain at least one step.")
    normalized = []
    for index, step in enumerate(value, start=1):
        if not isinstance(step, dict):
            raise PlanStateError(f"Step {index} must be an object.")
        normalized.append(
            (
                _text(step.get("title"), f"step {index}.title"),
                _text(step.get("expected_result"), f"step {index}.expected_result"),
            )
        )
    return normalized


class PlanStore:
    """Persistent state machine for the current session's execution plan."""

    # Shared by every PlanStore instance in this interpreter. The file lock below
    # provides the corresponding cross-process protection.
    _lock = threading.RLock()

    def __init__(self, *, session_id: str | None = None) -> None:
        """Create a plan store optionally bound to a specific session ID."""
        self._session_id = session_id

    @property
    def path(self) -> Path:
        """Return the persisted state path for the current session."""
        session_id = _text(
            self._session_id or getattr(settings, "session_id", None),
            "session_id",
        )
        # Preserve the original 16-hex filename for persisted-state compatibility.
        session_key = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return Path(get_project_state_directory()) / f"plan-{session_key}.json"

    @contextmanager
    def _state_lock(self) -> Iterator[None]:
        """Lock state access across both threads and processes."""
        with self._lock, _interprocess_lock(self.path):
            yield

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        """Return a new empty version-1 plan state."""
        return {
            "version": 1,
            "active_plan": None,
            "history": [],
            "current_request": None,
        }

    def _load(self) -> dict[str, Any]:
        """Load and minimally normalize persisted plan state."""
        path = self.path
        if not path.exists():
            return self._empty_state()
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanStateError(f"Cannot read plan state from {path}: {exc}") from exc
        if not isinstance(state, dict):
            raise PlanStateError("Plan state must be a JSON object.")
        # Keep version-1 files readable when optional top-level keys are missing.
        state.setdefault("version", 1)
        state.setdefault("active_plan", None)
        state.setdefault("history", [])
        state.setdefault("current_request", None)
        if not isinstance(state["history"], list):
            raise PlanStateError("Plan history must be a list.")
        return state

    def _save(self, state: dict[str, Any]) -> None:
        """Atomically persist plan state to disk."""
        path = self.path
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            raise PlanStateError(f"Cannot save plan state to {path}: {exc}") from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _active_plan(state: dict[str, Any]) -> dict[str, Any]:
        """Return the active plan after validating its request link."""
        plan = state.get("active_plan")
        if not isinstance(plan, dict) or plan.get("status") != "active":
            raise PlanStateError("There is no active plan. Create a plan first.")
        request = state.get("current_request")
        if not isinstance(request, dict) or request.get("plan_id") != plan.get("id"):
            raise PlanStateError("The active request is not connected to this plan.")
        return plan

    @staticmethod
    def _find_step(plan: dict[str, Any], step_id: int) -> dict[str, Any]:
        """Return a plan step by ID or raise when it does not exist."""
        for step in plan.get("steps", []):
            if isinstance(step, dict) and step.get("id") == step_id:
                return step
        raise PlanStateError(f"Plan step {step_id} does not exist.")

    @staticmethod
    def _new_step(step_id: int, title: str, expected_result: str) -> dict[str, Any]:
        """Build a new pending plan step."""
        return {
            "id": step_id,
            "title": title,
            "expected_result": expected_result,
            "status": "pending",
            "attempts": [],
            "result_summary": None,
            "evidence": None,
        }

    @staticmethod
    def _latest_attempt(step: dict[str, Any]) -> dict[str, Any] | None:
        """Return the latest valid execution attempt for a step."""
        attempts = step.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            return None
        latest = attempts[-1]
        return latest if isinstance(latest, dict) else None

    @classmethod
    def _compact_step(cls, step: dict[str, Any]) -> dict[str, Any]:
        """Build the compact step representation used in prompt snapshots."""
        latest = cls._latest_attempt(step)
        result = latest.get("result") if latest else None
        return {
            "id": step["id"],
            "title": step["title"],
            "expected_result": step["expected_result"],
            "status": step["status"],
            "attempt_count": len(step.get("attempts", [])),
            "latest_exit_code": (
                result.get("exit_code") if isinstance(result, dict) else None
            ),
            "result_summary": step.get("result_summary"),
        }

    def begin_request(self, user_input: str) -> dict[str, Any]:
        """Start a new user request and recover interrupted execution state."""
        user_input = _text(user_input, "user_input")
        with self._state_lock():
            state = self._load()
            active = state.get("active_plan")
            if isinstance(active, dict) and active.get("status") == "completed":
                state["history"].append(active)
                state["active_plan"] = None
                active = None
            elif isinstance(active, dict) and active.get("status") == "active":
                current_id = active.get("current_step_id")
                if isinstance(current_id, int):
                    current = self._find_step(active, current_id)
                    latest = self._latest_attempt(current)
                    if latest and latest.get("status") == "running":
                        timestamp = _now()
                        latest.update(
                            status="failed",
                            finished_at=timestamp,
                            result={
                                "ok": False,
                                "exit_code": None,
                                "launch_error": (
                                    "The application stopped before this command "
                                    "returned a result."
                                ),
                                "finished_at": timestamp,
                            },
                        )
                        current["status"] = "awaiting_review"
                        active["updated_at"] = timestamp
            state["current_request"] = {
                "id": uuid.uuid4().hex,
                "input": user_input,
                "started_at": _now(),
                "plan_id": active.get("id") if isinstance(active, dict) else None,
            }
            self._save(state)
            return deepcopy(state)

    def create_plan(self, goal: str, steps: list[dict[str, str]]) -> dict[str, Any]:
        """Create a new active plan for the current request."""
        goal = _text(goal, "goal")
        normalized_steps = _normalize_steps(steps)
        with self._state_lock():
            state = self._load()
            request = state.get("current_request")
            if not isinstance(request, dict):
                raise PlanStateError("No active user request exists.")
            active = state.get("active_plan")
            if active is not None:
                if not isinstance(active, dict):
                    raise PlanStateError("Active plan state is invalid.")
                if active.get("status") == "active":
                    raise PlanStateError(
                        "An unfinished plan already exists. Revise it instead."
                    )
                if active.get("status") == "completed":
                    raise PlanStateError(
                        "The previous plan is completed. Begin a new request before "
                        "creating another plan."
                    )
                raise PlanStateError(
                    f"Existing plan has invalid status: {active.get('status')!r}."
                )
            plan_id = uuid.uuid4().hex
            timestamp = _now()
            state["active_plan"] = {
                "id": plan_id,
                "goal": goal,
                "status": "active",
                "revision": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
                "current_step_id": None,
                "steps": [
                    self._new_step(index, title, expected_result)
                    for index, (title, expected_result) in enumerate(
                        normalized_steps, start=1
                    )
                ],
                "final_summary": None,
            }
            request["plan_id"] = plan_id
            self._save(state)
            return deepcopy(state)

    def start_step(self, step_id: int) -> dict[str, Any]:
        """Start the next pending step in plan order."""
        step_id = _positive_int(step_id, "step_id")
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            current_id = plan.get("current_step_id")
            if current_id is not None:
                raise PlanStateError(
                    f"Step {current_id} is already current and must be resolved first."
                )
            failed_steps = [
                step["id"] for step in plan["steps"] if step.get("status") == "failed"
            ]
            if failed_steps:
                raise PlanStateError(
                    f"Failed steps {failed_steps} must be resolved by revising "
                    "the plan."
                )
            step = self._find_step(plan, step_id)
            if step.get("status") != "pending":
                raise PlanStateError(
                    f"Step {step_id} cannot start from status {step.get('status')}."
                )
            next_pending = next(
                (
                    candidate
                    for candidate in plan["steps"]
                    if candidate.get("status") == "pending"
                ),
                None,
            )
            if next_pending is None:
                raise PlanStateError("There is no pending step.")
            if next_pending["id"] != step_id:
                raise PlanStateError(
                    f"Step {step_id} is out of order. Start step "
                    f"{next_pending['id']} next."
                )
            timestamp = _now()
            step["status"] = "in_progress"
            step["started_at"] = timestamp
            plan["current_step_id"] = step_id
            plan["updated_at"] = timestamp
            self._save(state)
            return deepcopy(state)

    def revise_plan(
        self,
        reason: str,
        steps: list[dict[str, str]],
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Supersede unfinished steps and append a revised plan."""
        reason = _text(reason, "reason")
        normalized_steps = _normalize_steps(steps, revised=True)
        goal = None if goal is None else _text(goal, "goal")
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            current_id = plan.get("current_step_id")
            if isinstance(current_id, int):
                current = self._find_step(plan, current_id)
                if current.get("status") == "awaiting_review":
                    raise PlanStateError(
                        "Review the latest command result before revising the plan."
                    )
                latest = self._latest_attempt(current)
                if latest and latest.get("status") == "running":
                    raise PlanStateError(
                        "Finish the running command before revising the plan."
                    )
            timestamp = _now()
            for step in plan["steps"]:
                if step.get("status") not in _REVISION_SKIP_STATUSES:
                    continue
                step["status"] = "skipped"
                step["result_summary"] = f"Superseded by revision: {reason}"
                step["completed_at"] = timestamp
            next_id = max((step["id"] for step in plan["steps"]), default=0) + 1
            plan["steps"].extend(
                self._new_step(next_id + offset, title, expected_result)
                for offset, (title, expected_result) in enumerate(normalized_steps)
            )
            if goal is not None:
                plan["goal"] = goal
            plan["revision"] += 1
            plan["revision_reason"] = reason
            plan["current_step_id"] = None
            plan["updated_at"] = timestamp
            self._save(state)
            return deepcopy(state)

    def begin_execution(
        self,
        step_id: int,
        tool_name: str,
        action: str,
        purpose: str,
        expected_result: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Record a new running execution attempt for the current step."""
        step_id = _positive_int(step_id, "step_id")
        tool_name = _text(tool_name, "tool_name")
        action = _text(action, "action")
        purpose = _text(purpose, "purpose")
        expected_result = _text(expected_result, "expected_result")
        if not isinstance(details, dict):
            raise PlanStateError("details must be an object.")
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            if plan.get("current_step_id") != step_id:
                raise PlanStateError(
                    f"Step {step_id} is not current. Current step: "
                    f"{plan.get('current_step_id')}."
                )
            step = self._find_step(plan, step_id)
            if step.get("status") != "in_progress":
                raise PlanStateError(
                    f"Step {step_id} is {step.get('status')}; it must be in_progress."
                )
            latest = self._latest_attempt(step)
            if latest and latest.get("status") == "running":
                raise PlanStateError(
                    f"Step {step_id} already has a running command attempt."
                )
            attempts = step.get("attempts")
            if not isinstance(attempts, list):
                raise PlanStateError(f"Step {step_id} attempts are invalid.")
            attempt = {
                "number": len(attempts) + 1,
                "tool": tool_name,
                "action": action,
                "purpose": purpose,
                "expected_result": expected_result,
                "status": "running",
                "started_at": _now(),
                "request": deepcopy(details),
                "result": None,
            }
            attempts.append(attempt)
            plan["updated_at"] = _now()
            self._save(state)
            return {
                "plan_id": plan["id"],
                "step_id": step_id,
                "attempt_number": attempt["number"],
            }

    def finish_execution(
        self,
        step_id: int,
        attempt_number: int,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Finish the latest execution attempt and queue it for review."""
        step_id = _positive_int(step_id, "step_id")
        attempt_number = _positive_int(attempt_number, "attempt_number")
        if not isinstance(result, dict):
            raise PlanStateError("result must be an object.")
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            if plan.get("current_step_id") != step_id:
                raise PlanStateError(f"Step {step_id} is not the current step.")
            step = self._find_step(plan, step_id)
            if step.get("status") != "in_progress":
                raise PlanStateError(f"Step {step_id} has no running execution.")
            attempts = step.get("attempts")
            if not isinstance(attempts, list) or attempt_number > len(attempts):
                raise PlanStateError(
                    f"Attempt {attempt_number} does not exist for step {step_id}."
                )
            if attempt_number != len(attempts):
                raise PlanStateError(
                    f"Attempt {attempt_number} is stale for step {step_id}."
                )
            attempt = attempts[attempt_number - 1]
            if not isinstance(attempt, dict) or attempt.get("status") != "running":
                raise PlanStateError(
                    f"Attempt {attempt_number} for step {step_id} is not running."
                )
            timestamp = _now()
            attempt["status"] = (
                "succeeded" if result.get("exit_code") == 0 else "failed"
            )
            attempt["finished_at"] = timestamp
            attempt["result"] = deepcopy(result)
            step["status"] = "awaiting_review"
            plan["updated_at"] = timestamp
            self._save(state)
            return deepcopy(state)

    def review_step(
        self,
        step_id: int,
        outcome: PlanReviewOutcome,
        summary: str,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        """Apply a review outcome to the current step."""
        step_id = _positive_int(step_id, "step_id")
        if outcome not in _REVIEW_OUTCOMES:
            raise PlanStateError(f"Invalid review outcome: {outcome!r}.")
        summary = _text(summary, "summary")
        evidence = _optional_text(evidence)
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            if plan.get("current_step_id") != step_id:
                raise PlanStateError(f"Step {step_id} is not the current step.")
            step = self._find_step(plan, step_id)
            if step.get("status") != "awaiting_review":
                raise PlanStateError(
                    f"Step {step_id} has no command result awaiting review."
                )
            timestamp = _now()
            step["result_summary"] = summary
            step["evidence"] = evidence
            if outcome == "retry":
                step["status"] = "in_progress"
            else:
                step["status"] = outcome
                step["completed_at"] = timestamp
                plan["current_step_id"] = None
            plan["updated_at"] = timestamp
            self._save(state)
            return deepcopy(state)

    def finish_plan(self, summary: str) -> dict[str, Any]:
        """Complete an active plan after all steps are resolved."""
        summary = _text(summary, "summary")
        with self._state_lock():
            state = self._load()
            plan = self._active_plan(state)
            if plan.get("current_step_id") is not None:
                raise PlanStateError(
                    "Resolve the current step before finishing the plan."
                )
            unfinished = [
                step["id"]
                for step in plan["steps"]
                if step.get("status") not in _FINISHED_STEP_STATUSES
            ]
            if unfinished:
                raise PlanStateError(f"Unfinished plan steps: {unfinished}")
            has_completed_execution = any(
                step.get("status") == "completed" and step.get("attempts")
                for step in plan["steps"]
            )
            if not has_completed_execution:
                raise PlanStateError(
                    "At least one completed step with a command result is required."
                )
            timestamp = _now()
            plan["status"] = "completed"
            plan["final_summary"] = summary
            plan["completed_at"] = timestamp
            plan["updated_at"] = timestamp
            self._save(state)
            return deepcopy(state)

    def snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the current persisted state."""
        with self._state_lock():
            return deepcopy(self._load())

    def prompt_snapshot(self) -> str:
        """Return a compact JSON snapshot suitable for prompt context."""
        state = self.snapshot()
        plan = state.get("active_plan")
        request = state.get("current_request")
        request_id = request.get("id") if isinstance(request, dict) else None
        if not isinstance(plan, dict):
            value = {"current_request_id": request_id, "plan": None}
        else:
            value = {
                "current_request_id": request_id,
                "plan_id": plan["id"],
                "goal": plan["goal"],
                "status": plan["status"],
                "revision": plan["revision"],
                "current_step_id": plan["current_step_id"],
                "steps": [self._compact_step(step) for step in plan["steps"]],
            }
        return json.dumps(value, ensure_ascii=False, indent=2)

    def current_request_is_complete(self) -> bool:
        """Return whether the current request is linked to a completed plan."""
        state = self.snapshot()
        request = state.get("current_request")
        plan = state.get("active_plan")
        return (
            isinstance(request, dict)
            and isinstance(plan, dict)
            and request.get("plan_id") == plan.get("id")
            and plan.get("status") == "completed"
        )


plan_store = PlanStore()
