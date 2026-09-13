import time
import json
import hashlib
from pathlib import Path
from functools import lru_cache
from contextlib import contextmanager
from typing import Any, Iterator, Literal
from sqlalchemy import event, update
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, SQLModel, create_engine, select
from .plan_models import (
    AttemptStatus,
    ExecutionPlan,
    PlanAttempt,
    PlanPointer,
    PlanRequest,
    PlanRevision,
    PlanStatus,
    PlanStep,
    RequestInput,
    StepStatus,
    utc_now,
)
from .project import get_project_state_directory
from .settings import settings

PlanReviewOutcome = Literal["completed", "retry", "failed", "skipped"]
_REVIEW_OUTCOMES = frozenset({"completed", "retry", "failed", "skipped"})
_LEASE_SECONDS = 20


class PlanStateError(RuntimeError):
    """The requested transition is not valid for the current plan."""


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanStateError(f"{name} must be a non-empty string.")
    return value.strip()


def _positive_number(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PlanStateError(f"{name} must be a positive integer.")
    return value


def _step_definitions(steps: object) -> list[tuple[str, str]]:
    if not isinstance(steps, list) or not steps:
        raise PlanStateError("A plan must contain at least one step.")
    definitions: list[tuple[str, str]] = []
    for number, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise PlanStateError(f"Step {number} must be an object.")
        definitions.append(
            (
                _required_text(step.get("title"), f"step {number}.title"),
                _required_text(
                    step.get("expected_result"), f"step {number}.expected_result"
                ),
            )
        )
    return definitions


def _json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PlanStateError(f"Execution data cannot be stored as JSON: {exc}") from exc


@lru_cache(maxsize=64)
def _engine(path: Path) -> Engine:
    """Build one engine per session database; old sample databases are untouched."""
    engine = create_engine(
        URL.create("sqlite", database=str(path)), connect_args={"timeout": 10}
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: Any, _record: Any) -> None:
        # SQLAlchemy emits BEGIN below, including for reads. WAL keeps those reads
        # separate from the short write transactions used by plan transitions.
        connection.isolation_level = None
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout = 10000")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
        finally:
            cursor.close()

    @event.listens_for(engine, "begin")
    def begin_transaction(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.exec(
            sqlite_insert(PlanPointer)
            .values(id=1, version=0)
            .on_conflict_do_nothing(index_elements=["id"])
        )
    return engine


class PlanStore:
    """Enforce one ordered, reviewable execution plan per SESSION_ID."""

    def __init__(self, *, session_id: str | None = None) -> None:
        self._session_id = session_id

    @property
    def path(self) -> Path:
        session_id = _required_text(
            self._session_id or settings.session_id, "session_id"
        )
        key = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return get_project_state_directory() / f"plan-sqlmodel-{key}.db"

    @contextmanager
    def _session(self, *, write: bool = False) -> Iterator[Session]:
        try:
            with Session(_engine(self.path), expire_on_commit=False) as session:
                with session.begin():
                    if write:
                        # The first statement acquires SQLite's writer reservation.
                        # Read/check/update transitions then stay atomic across processes.
                        session.exec(
                            update(PlanPointer)
                            .where(PlanPointer.id == 1)
                            .values(version=PlanPointer.version + 1)
                        )
                    yield session
        except SQLAlchemyError as exc:
            raise PlanStateError(
                f"Cannot access plan database {self.path}: {exc}"
            ) from exc

    @staticmethod
    def _pointer(session: Session) -> PlanPointer:
        pointer = session.get(PlanPointer, 1)
        if pointer is None:
            raise PlanStateError("Plan database has no session pointer.")
        return pointer

    @classmethod
    def _active_plan(cls, session: Session) -> ExecutionPlan:
        pointer = cls._pointer(session)
        plan = session.get(ExecutionPlan, pointer.plan_id) if pointer.plan_id else None
        if plan is None or plan.status != PlanStatus.active:
            raise PlanStateError("There is no active plan. Create a plan first.")
        return plan

    @staticmethod
    def _step(session: Session, plan: ExecutionPlan, number: int) -> PlanStep:
        step = session.exec(
            select(PlanStep).where(
                PlanStep.plan_id == plan.id, PlanStep.number == number
            )
        ).one_or_none()
        if step is None:
            raise PlanStateError(f"Plan step {number} does not exist.")
        return step

    @staticmethod
    def _steps(session: Session, plan: ExecutionPlan) -> list[PlanStep]:
        return list(
            session.exec(
                select(PlanStep)
                .where(PlanStep.plan_id == plan.id)
                .order_by(PlanStep.number)
            )
        )

    @staticmethod
    def _latest_attempt(session: Session, step: PlanStep) -> PlanAttempt | None:
        return session.exec(
            select(PlanAttempt)
            .where(PlanAttempt.step_id == step.id)
            .order_by(PlanAttempt.number.desc())
            .limit(1)
        ).first()

    def begin_request(self, user_input: str) -> dict[str, Any]:
        """Resume unfinished work, or open a fresh request after a terminal plan."""
        user_input = _required_text(user_input, "user_input")
        with self._session(write=True) as session:
            pointer = self._pointer(session)
            plan = (
                session.get(ExecutionPlan, pointer.plan_id) if pointer.plan_id else None
            )
            request = (
                session.get(PlanRequest, pointer.request_id)
                if pointer.request_id
                else None
            )
            continuing = request is not None and request.status == PlanStatus.active

            if continuing and plan is not None and plan.current_step_number is not None:
                step = self._step(session, plan, plan.current_step_number)
                attempt = self._latest_attempt(session, step)
                if attempt is not None and attempt.status == AttemptStatus.running:
                    if (attempt.lease_until or 0) > time.time():
                        raise PlanStateError(
                            "This session has a live command. Wait for it to finish."
                        )
                    attempt.status = AttemptStatus.interrupted
                    attempt.finished_at = utc_now()
                    attempt.lease_until = None
                    attempt.result_json = _json(
                        {
                            "ok": False,
                            "exit_code": None,
                            "launch_error": "The previous execution stopped before returning a result.",
                            "finished_at": attempt.finished_at,
                        }
                    )
                    step.status = StepStatus.awaiting_review
                    plan.updated_at = attempt.finished_at

            if not continuing:
                request = PlanRequest(input=user_input)
                session.add(request)
                pointer.request_id = request.id
                pointer.plan_id = None

            session.add(RequestInput(request_id=request.id, input=user_input))
        return self.snapshot()

    def create_plan(self, goal: str, steps: list[dict[str, str]]) -> dict[str, Any]:
        goal = _required_text(goal, "goal")
        definitions = _step_definitions(steps)
        with self._session(write=True) as session:
            pointer = self._pointer(session)
            request = (
                session.get(PlanRequest, pointer.request_id)
                if pointer.request_id
                else None
            )
            if request is None or request.status != PlanStatus.active:
                raise PlanStateError("No active user request exists.")
            if pointer.plan_id is not None:
                raise PlanStateError("A plan already exists. Revise it instead.")

            plan = ExecutionPlan(request_id=request.id, goal=goal)
            session.add(plan)
            session.add_all(
                PlanStep(
                    plan_id=plan.id,
                    number=number,
                    title=title,
                    expected_result=expected,
                )
                for number, (title, expected) in enumerate(definitions, start=1)
            )
            session.add(
                PlanRevision(
                    plan_id=plan.id, number=1, reason="Initial plan", goal=goal
                )
            )
            pointer.plan_id = plan.id
        return self.compact_snapshot()

    def start_step(self, step_id: int) -> dict[str, Any]:
        step_id = _positive_number(step_id, "step_id")
        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                raise PlanStateError(
                    f"Step {plan.current_step_number} is already current and must be resolved first."
                )
            steps = self._steps(session, plan)
            if any(step.status == StepStatus.failed for step in steps):
                raise PlanStateError(
                    "Failed steps must be resolved by revising the plan."
                )
            step = self._step(session, plan, step_id)
            if step.status != StepStatus.pending:
                raise PlanStateError(
                    f"Step {step_id} cannot start from status {step.status}."
                )
            next_pending = next(
                (item for item in steps if item.status == StepStatus.pending), None
            )
            if next_pending is None or next_pending.number != step_id:
                raise PlanStateError(
                    f"Step {step_id} is out of order. Start step {next_pending.number if next_pending else 'none'} next."
                )
            step.status = StepStatus.in_progress
            step.started_at = utc_now()
            plan.current_step_number = step_id
            plan.updated_at = step.started_at
        return self.compact_snapshot()

    def begin_execution(
        self,
        step_id: int,
        tool_name: str,
        action: str,
        purpose: str,
        expected_result: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        step_id = _positive_number(step_id, "step_id")
        tool_name = _required_text(tool_name, "tool_name")
        action = _required_text(action, "action")
        purpose = _required_text(purpose, "purpose")
        expected_result = _required_text(expected_result, "expected_result")
        if not isinstance(details, dict):
            raise PlanStateError("details must be an object.")
        request_json = _json(details)

        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number != step_id:
                raise PlanStateError(
                    f"Step {step_id} is not current. Current step: {plan.current_step_number}."
                )
            step = self._step(session, plan, step_id)
            if step.status != StepStatus.in_progress:
                raise PlanStateError(
                    f"Step {step_id} is {step.status}; it must be in_progress."
                )
            latest = self._latest_attempt(session, step)
            if latest is not None and latest.status == AttemptStatus.running:
                raise PlanStateError(
                    f"Step {step_id} already has a running command attempt."
                )

            step.attempt_count += 1
            attempt = PlanAttempt(
                step_id=step.id,
                number=step.attempt_count,
                tool=tool_name,
                action=action,
                purpose=purpose,
                expected_result=expected_result,
                request_json=request_json,
                lease_until=time.time() + _LEASE_SECONDS,
            )
            session.add(attempt)
            plan.updated_at = utc_now()
            reservation = {
                "plan_id": plan.id,
                "step_id": step_id,
                "attempt_number": attempt.number,
                "execution_id": attempt.id,
            }
        return reservation

    def touch_execution(self, execution_id: str) -> None:
        execution_id = _required_text(execution_id, "execution_id")
        with self._session(write=True) as session:
            attempt = session.get(PlanAttempt, execution_id)
            if attempt is None or attempt.status != AttemptStatus.running:
                raise PlanStateError("The execution is no longer running.")
            attempt.lease_until = time.time() + _LEASE_SECONDS

    def finish_execution(
        self,
        step_id: int,
        attempt_number: int,
        result: dict[str, Any],
        execution_id: str,
    ) -> dict[str, Any]:
        step_id = _positive_number(step_id, "step_id")
        attempt_number = _positive_number(attempt_number, "attempt_number")
        execution_id = _required_text(execution_id, "execution_id")
        if not isinstance(result, dict):
            raise PlanStateError("result must be an object.")
        result_json = _json(result)

        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number != step_id:
                raise PlanStateError(f"Step {step_id} is not the current step.")
            step = self._step(session, plan, step_id)
            attempt = self._latest_attempt(session, step)
            if (
                step.status != StepStatus.in_progress
                or attempt is None
                or attempt.status != AttemptStatus.running
            ):
                raise PlanStateError(f"Step {step_id} has no running execution.")
            if attempt.number != attempt_number:
                raise PlanStateError(
                    f"Attempt {attempt_number} is stale for step {step_id}."
                )
            if attempt.id != execution_id:
                raise PlanStateError("The execution ID does not own this attempt.")

            timestamp = utc_now()
            attempt.status = (
                AttemptStatus.succeeded
                if result.get("exit_code") == 0 and result.get("launch_error") is None
                else AttemptStatus.failed
            )
            attempt.result_json = result_json
            attempt.finished_at = timestamp
            attempt.lease_until = None
            step.status = StepStatus.awaiting_review
            step.latest_exit_code = result.get("exit_code")
            plan.updated_at = timestamp
        return self.compact_snapshot()

    def review_step(
        self,
        step_id: int,
        outcome: PlanReviewOutcome,
        summary: str,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        step_id = _positive_number(step_id, "step_id")
        summary = _required_text(summary, "summary")
        if outcome not in _REVIEW_OUTCOMES:
            raise PlanStateError(f"Invalid review outcome: {outcome!r}.")
        evidence = (
            evidence.strip() if isinstance(evidence, str) and evidence.strip() else None
        )
        if outcome == "completed" and evidence is None:
            raise PlanStateError("A completed step requires concrete evidence.")

        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number != step_id:
                raise PlanStateError(f"Step {step_id} is not the current step.")
            step = self._step(session, plan, step_id)
            if step.status != StepStatus.awaiting_review:
                raise PlanStateError(
                    f"Step {step_id} has no command result awaiting review."
                )
            step.status = StepStatus.in_progress if outcome == "retry" else outcome
            step.result_summary = summary
            step.evidence = evidence
            if outcome != "retry":
                step.completed_at = utc_now()
                plan.current_step_number = None
            plan.updated_at = utc_now()
        return self.compact_snapshot()

    def revise_plan(
        self,
        reason: str,
        steps: list[dict[str, str]],
        goal: str | None = None,
    ) -> dict[str, Any]:
        reason = _required_text(reason, "reason")
        definitions = _step_definitions(steps)
        goal = _required_text(goal, "goal") if goal is not None else None

        with self._session(write=True) as session:
            plan = self._active_plan(session)
            existing = self._steps(session, plan)
            if plan.current_step_number is not None:
                current = self._step(session, plan, plan.current_step_number)
                if current.status == StepStatus.awaiting_review:
                    raise PlanStateError(
                        "Review the latest command result before revising the plan."
                    )
                latest = self._latest_attempt(session, current)
                if latest is not None and latest.status == AttemptStatus.running:
                    raise PlanStateError(
                        "Finish the running command before revising the plan."
                    )

            timestamp = utc_now()
            for step in existing:
                if step.status in {
                    StepStatus.pending,
                    StepStatus.in_progress,
                    StepStatus.failed,
                }:
                    step.status = StepStatus.skipped
                    step.result_summary = f"Superseded by revision: {reason}"
                    step.completed_at = timestamp

            next_number = max((step.number for step in existing), default=0) + 1
            session.add_all(
                PlanStep(
                    plan_id=plan.id,
                    number=next_number + offset,
                    title=title,
                    expected_result=expected,
                )
                for offset, (title, expected) in enumerate(definitions)
            )
            plan.goal = goal or plan.goal
            plan.revision += 1
            plan.current_step_number = None
            plan.updated_at = timestamp
            session.add(
                PlanRevision(
                    plan_id=plan.id,
                    number=plan.revision,
                    reason=reason,
                    goal=plan.goal,
                )
            )
        return self.compact_snapshot()

    @staticmethod
    def _close(
        session: Session, plan: ExecutionPlan, status: PlanStatus, summary: str
    ) -> None:
        timestamp = utc_now()
        plan.status = status
        plan.final_summary = summary
        plan.current_step_number = None
        plan.completed_at = timestamp
        plan.updated_at = timestamp
        request = session.get(PlanRequest, plan.request_id)
        if request is None:
            raise PlanStateError("The plan's user request no longer exists.")
        request.status = status
        request.finished_at = timestamp

    def finish_plan(self, summary: str) -> dict[str, Any]:
        summary = _required_text(summary, "summary")
        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                raise PlanStateError(
                    "Resolve the current step before finishing the plan."
                )
            steps = self._steps(session, plan)
            unfinished = [
                step.number
                for step in steps
                if step.status not in {StepStatus.completed, StepStatus.skipped}
            ]
            if unfinished:
                raise PlanStateError(f"Unfinished plan steps: {unfinished}")
            if not any(
                step.status == StepStatus.completed and step.attempt_count
                for step in steps
            ):
                raise PlanStateError(
                    "At least one completed step with a command result is required."
                )
            self._close(session, plan, PlanStatus.completed, summary)
        return self.compact_snapshot()

    def block_plan(self, summary: str) -> dict[str, Any]:
        summary = _required_text(summary, "summary")
        with self._session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                current = self._step(session, plan, plan.current_step_number)
                if current.status == StepStatus.awaiting_review:
                    raise PlanStateError(
                        "Review the latest command result before blocking the plan."
                    )
                latest = self._latest_attempt(session, current)
                if latest is not None and latest.status == AttemptStatus.running:
                    raise PlanStateError(
                        "Finish the running command before blocking the plan."
                    )
            timestamp = utc_now()
            for step in self._steps(session, plan):
                if step.status == StepStatus.pending:
                    step.status = StepStatus.skipped
                    step.result_summary = f"Blocked: {summary}"
                    step.completed_at = timestamp
                elif step.status == StepStatus.in_progress:
                    step.status = StepStatus.failed
                    step.result_summary = summary
                    step.completed_at = timestamp
            self._close(session, plan, PlanStatus.blocked, summary)
        return self.compact_snapshot()

    @staticmethod
    def _attempt_data(attempt: PlanAttempt) -> dict[str, Any]:
        return {
            "number": attempt.number,
            "execution_id": attempt.id,
            "tool": attempt.tool,
            "action": attempt.action,
            "purpose": attempt.purpose,
            "expected_result": attempt.expected_result,
            "status": attempt.status,
            "started_at": attempt.started_at,
            "finished_at": attempt.finished_at,
            "request": json.loads(attempt.request_json),
            "result": json.loads(attempt.result_json) if attempt.result_json else None,
        }

    @classmethod
    def _step_data(
        cls, session: Session, step: PlanStep, *, full: bool
    ) -> dict[str, Any]:
        data = {
            "id": step.number,
            "plan_id": step.plan_id,
            "title": step.title,
            "expected_result": step.expected_result,
            "status": step.status,
            "attempt_count": step.attempt_count,
            "latest_exit_code": step.latest_exit_code,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "result_summary": step.result_summary,
            "evidence": step.evidence,
        }
        if full:
            attempts = session.exec(
                select(PlanAttempt)
                .where(PlanAttempt.step_id == step.id)
                .order_by(PlanAttempt.number)
            )
            data["attempts"] = [cls._attempt_data(attempt) for attempt in attempts]
        return data

    @classmethod
    def _plan_data(
        cls, session: Session, plan: ExecutionPlan, *, full: bool
    ) -> dict[str, Any]:
        data = {
            "id": plan.id,
            "request_id": plan.request_id,
            "goal": plan.goal,
            "status": plan.status,
            "revision": plan.revision,
            "current_step_id": plan.current_step_number,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "completed_at": plan.completed_at,
            "final_summary": plan.final_summary,
            "steps": [
                cls._step_data(session, step, full=full)
                for step in cls._steps(session, plan)
            ],
        }
        if full:
            revisions = session.exec(
                select(PlanRevision)
                .where(PlanRevision.plan_id == plan.id)
                .order_by(PlanRevision.number)
            )
            data["revisions"] = [
                {
                    "number": revision.number,
                    "reason": revision.reason,
                    "goal": revision.goal,
                    "created_at": revision.created_at,
                }
                for revision in revisions
            ]
        return data

    @staticmethod
    def _plan_summary(plan: ExecutionPlan) -> dict[str, Any]:
        return {
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status,
            "revision": plan.revision,
            "created_at": plan.created_at,
            "completed_at": plan.completed_at,
            "final_summary": plan.final_summary,
        }

    def _snapshot(self, session: Session, *, full: bool) -> dict[str, Any]:
        pointer = self._pointer(session)
        request = (
            session.get(PlanRequest, pointer.request_id) if pointer.request_id else None
        )
        plan = session.get(ExecutionPlan, pointer.plan_id) if pointer.plan_id else None
        current_request = None
        if request is not None:
            current_request = {
                "id": request.id,
                "input": request.input,
                "status": request.status,
                "started_at": request.started_at,
                "finished_at": request.finished_at,
                "plan_id": pointer.plan_id,
            }
            if full:
                inputs = session.exec(
                    select(RequestInput)
                    .where(RequestInput.request_id == request.id)
                    .order_by(RequestInput.received_at)
                )
                current_request["inputs"] = [
                    {"input": item.input, "received_at": item.received_at}
                    for item in inputs
                ]

        state = {
            "version": 3,
            "current_request": current_request,
            "active_plan": self._plan_data(session, plan, full=full) if plan else None,
        }
        if full:
            previous = session.exec(
                select(ExecutionPlan)
                .where(ExecutionPlan.id != pointer.plan_id)
                .order_by(ExecutionPlan.created_at)
            )
            state["history"] = [self._plan_summary(item) for item in previous]
        return state

    def snapshot(self) -> dict[str, Any]:
        with self._session() as session:
            return self._snapshot(session, full=True)

    def compact_snapshot(self) -> dict[str, Any]:
        with self._session() as session:
            return self._snapshot(session, full=False)

    def prompt_snapshot(self) -> str:
        return json.dumps(self.compact_snapshot(), ensure_ascii=False, indent=2)

    def list_plans(self) -> list[dict[str, Any]]:
        with self._session() as session:
            plans = session.exec(
                select(ExecutionPlan).order_by(ExecutionPlan.created_at.desc())
            )
            return [self._plan_summary(plan) for plan in plans]

    def plan_history(self, plan_id: str) -> dict[str, Any]:
        plan_id = _required_text(plan_id, "plan_id")
        with self._session() as session:
            plan = session.get(ExecutionPlan, plan_id)
            if plan is None:
                raise PlanStateError(f"Plan {plan_id} does not exist.")
            return self._plan_data(session, plan, full=True)

    def step_history(self, step_id: int, plan_id: str | None = None) -> dict[str, Any]:
        step_id = _positive_number(step_id, "step_id")
        with self._session() as session:
            selected_id = plan_id or self._pointer(session).plan_id
            if selected_id is None:
                raise PlanStateError("There is no current plan. Provide a plan_id.")
            plan = session.get(ExecutionPlan, selected_id)
            if plan is None:
                raise PlanStateError(f"Plan {selected_id} does not exist.")
            return self._step_data(
                session, self._step(session, plan, step_id), full=True
            )

    def current_request_status(self) -> str | None:
        with self._session() as session:
            request_id = self._pointer(session).request_id
            request = session.get(PlanRequest, request_id) if request_id else None
            return request.status if request else None

    def current_request_is_complete(self) -> bool:
        return self.current_request_status() == PlanStatus.completed


plan_store = PlanStore()
