import json
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Literal

from sqlalchemy import event, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
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
_EXECUTION_LEASE_SECONDS = 20


class PlanStateError(RuntimeError):
    """Raised when a requested plan transition is not currently valid."""


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanStateError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PlanStateError(f"{field_name} must be a positive integer.")
    return value


def _validated_steps(steps: object) -> list[tuple[str, str]]:
    if not isinstance(steps, list) or not steps:
        raise PlanStateError("A plan must contain at least one step.")

    result: list[tuple[str, str]] = []
    for number, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise PlanStateError(f"Step {number} must be an object.")
        result.append(
            (
                _required_text(step.get("title"), f"step {number}.title"),
                _required_text(
                    step.get("expected_result"), f"step {number}.expected_result"
                ),
            )
        )
    return result


def _json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PlanStateError(f"Plan execution data is not JSON serializable: {exc}") from exc


@lru_cache(maxsize=64)
def _create_plan_engine(database_path: Path) -> Engine:
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: Any, _record: Any) -> None:
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
    return engine


class PlanStore:
    """Persist and enforce one ordered plan for each configured session."""

    def __init__(self, *, session_id: str | None = None) -> None:
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        return _required_text(self._session_id or settings.session_id, "session_id")

    @property
    def database_path(self) -> Path:
        return get_project_state_directory() / "plan.db"

    @contextmanager
    def _database_session(self, *, write: bool = False) -> Iterator[Session]:
        try:
            with Session(
                _create_plan_engine(self.database_path), expire_on_commit=False
            ) as session:
                with session.begin():
                    if write:
                        session.exec(
                            sqlite_insert(PlanPointer)
                            .values(session_id=self.session_id, version=0)
                            .on_conflict_do_nothing(index_elements=["session_id"])
                        )
                        session.exec(
                            update(PlanPointer)
                            .where(PlanPointer.session_id == self.session_id)
                            .values(version=PlanPointer.version + 1)
                        )
                    yield session
        except SQLAlchemyError as exc:
            raise PlanStateError(
                f"Cannot access plan database {self.database_path}: {exc}"
            ) from exc

    def _pointer(self, session: Session) -> PlanPointer:
        pointer = session.get(PlanPointer, self.session_id)
        return pointer or PlanPointer(session_id=self.session_id)

    def _request(
        self, session: Session, request_id: str | None
    ) -> PlanRequest | None:
        if request_id is None:
            return None
        return session.exec(
            select(PlanRequest).where(
                PlanRequest.id == request_id,
                PlanRequest.session_id == self.session_id,
            )
        ).one_or_none()

    def _plan(
        self, session: Session, plan_id: str | None
    ) -> ExecutionPlan | None:
        if plan_id is None:
            return None
        return session.exec(
            select(ExecutionPlan).where(
                ExecutionPlan.id == plan_id,
                ExecutionPlan.session_id == self.session_id,
            )
        ).one_or_none()

    def _active_plan(self, session: Session) -> ExecutionPlan:
        plan = self._plan(session, self._pointer(session).plan_id)
        if plan is None or plan.status != PlanStatus.active:
            raise PlanStateError("There is no active plan. Create a plan first.")
        return plan

    @staticmethod
    def _step(session: Session, plan: ExecutionPlan, number: int) -> PlanStep:
        step = session.exec(
            select(PlanStep).where(
                PlanStep.plan_id == plan.id,
                PlanStep.number == number,
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
        """Open a new request or attach new input to unfinished work."""
        user_input = _required_text(user_input, "user_input")

        with self._database_session(write=True) as session:
            pointer = self._pointer(session)
            request = self._request(session, pointer.request_id)
            plan = self._plan(session, pointer.plan_id)
            is_continuation = (
                request is not None and request.status == PlanStatus.active
            )

            if is_continuation and plan is not None:
                self._recover_interrupted_execution(session, plan)

            if not is_continuation:
                request = PlanRequest(session_id=self.session_id, input=user_input)
                session.add(request)
                pointer.request_id = request.id
                pointer.plan_id = None

            session.add(RequestInput(request_id=request.id, input=user_input))

        return self.compact_snapshot()

    def _recover_interrupted_execution(
        self, session: Session, plan: ExecutionPlan
    ) -> None:
        if plan.current_step_number is None:
            return
        step = self._step(session, plan, plan.current_step_number)
        attempt = self._latest_attempt(session, step)
        if attempt is None or attempt.status != AttemptStatus.running:
            return
        if (attempt.lease_until or 0) > time.time():
            raise PlanStateError("This session has a live tool execution.")

        timestamp = utc_now()
        attempt.status = AttemptStatus.interrupted
        attempt.finished_at = timestamp
        attempt.lease_until = None
        attempt.result_json = _json(
            {
                "ok": False,
                "exit_code": None,
                "error": "The previous tool execution ended without recording a result.",
                "finished_at": timestamp,
            }
        )
        step.status = StepStatus.awaiting_review
        plan.updated_at = timestamp

    def create_plan(self, goal: str, steps: list[dict[str, str]]) -> dict[str, Any]:
        goal = _required_text(goal, "goal")
        definitions = _validated_steps(steps)

        with self._database_session(write=True) as session:
            pointer = self._pointer(session)
            request = self._request(session, pointer.request_id)
            if request is None or request.status != PlanStatus.active:
                raise PlanStateError("No active user request exists.")
            if pointer.plan_id is not None:
                raise PlanStateError("A plan already exists. Revise it instead.")

            plan = ExecutionPlan(
                session_id=self.session_id,
                request_id=request.id,
                goal=goal,
            )
            session.add(plan)
            session.add_all(
                PlanStep(
                    plan_id=plan.id,
                    number=number,
                    title=title,
                    expected_result=expected_result,
                )
                for number, (title, expected_result) in enumerate(
                    definitions, start=1
                )
            )
            session.add(
                PlanRevision(
                    plan_id=plan.id,
                    number=1,
                    reason="Initial plan",
                    goal=goal,
                )
            )
            pointer.plan_id = plan.id

        return self.compact_snapshot()

    def start_step(self, step_id: int) -> dict[str, Any]:
        step_id = _positive_integer(step_id, "step_id")

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                raise PlanStateError(
                    f"Step {plan.current_step_number} must be resolved first."
                )

            steps = self._steps(session, plan)
            if any(step.status == StepStatus.failed for step in steps):
                raise PlanStateError("Revise the plan before continuing a failed step.")

            next_pending = next(
                (step for step in steps if step.status == StepStatus.pending), None
            )
            if next_pending is None or next_pending.number != step_id:
                expected = next_pending.number if next_pending is not None else "none"
                raise PlanStateError(
                    f"Step {step_id} is out of order. The next step is {expected}."
                )

            step = self._step(session, plan, step_id)
            if step.status != StepStatus.pending:
                raise PlanStateError(
                    f"Step {step_id} cannot start from status {step.status}."
                )

            timestamp = utc_now()
            step.status = StepStatus.in_progress
            step.started_at = timestamp
            plan.current_step_number = step_id
            plan.updated_at = timestamp

        return self.compact_snapshot()

    def begin_execution(
        self,
        *,
        step_id: int,
        tool_name: str,
        action: str,
        purpose: str,
        expected_result: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        step_id = _positive_integer(step_id, "step_id")
        tool_name = _required_text(tool_name, "tool_name")
        action = _required_text(action, "action")
        purpose = _required_text(purpose, "purpose")
        expected_result = _required_text(expected_result, "expected_result")
        if not isinstance(details, dict):
            raise PlanStateError("details must be an object.")
        request_json = _json(details)

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number != step_id:
                raise PlanStateError(
                    f"Step {step_id} is not current. Current step: {plan.current_step_number}."
                )

            step = self._step(session, plan, step_id)
            if step.status != StepStatus.in_progress:
                raise PlanStateError(
                    f"Step {step_id} must be in_progress, not {step.status}."
                )
            latest = self._latest_attempt(session, step)
            if latest is not None and latest.status == AttemptStatus.running:
                raise PlanStateError(f"Step {step_id} already has a running attempt.")

            step.attempt_count += 1
            attempt = PlanAttempt(
                step_id=step.id,
                number=step.attempt_count,
                tool=tool_name,
                action=action,
                purpose=purpose,
                expected_result=expected_result,
                request_json=request_json,
                lease_until=time.time() + _EXECUTION_LEASE_SECONDS,
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

    def finish_execution(
        self,
        *,
        step_id: int,
        attempt_number: int,
        execution_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        step_id = _positive_integer(step_id, "step_id")
        attempt_number = _positive_integer(attempt_number, "attempt_number")
        execution_id = _required_text(execution_id, "execution_id")
        if not isinstance(result, dict):
            raise PlanStateError("result must be an object.")
        result_json = _json(result)

        with self._database_session(write=True) as session:
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
                raise PlanStateError(f"Step {step_id} has no running attempt.")
            if attempt.number != attempt_number or attempt.id != execution_id:
                raise PlanStateError("The execution reservation is stale or invalid.")

            timestamp = utc_now()
            attempt.status = (
                AttemptStatus.succeeded
                if result.get("ok") is True
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
        *,
        step_id: int,
        outcome: PlanReviewOutcome,
        summary: str,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        step_id = _positive_integer(step_id, "step_id")
        summary = _required_text(summary, "summary")
        if outcome not in _REVIEW_OUTCOMES:
            raise PlanStateError(f"Invalid review outcome: {outcome!r}.")

        evidence = (
            evidence.strip()
            if isinstance(evidence, str) and evidence.strip()
            else None
        )
        if outcome == "completed" and evidence is None:
            raise PlanStateError("A completed step requires concrete evidence.")

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number != step_id:
                raise PlanStateError(f"Step {step_id} is not the current step.")
            step = self._step(session, plan, step_id)
            if step.status != StepStatus.awaiting_review:
                raise PlanStateError(
                    f"Step {step_id} has no tool result awaiting review."
                )

            timestamp = utc_now()
            step.status = StepStatus.in_progress if outcome == "retry" else outcome
            step.result_summary = summary
            step.evidence = evidence
            if outcome != "retry":
                step.completed_at = timestamp
                plan.current_step_number = None
            plan.updated_at = timestamp

        return self.compact_snapshot()

    def revise_plan(
        self,
        *,
        reason: str,
        steps: list[dict[str, str]],
        goal: str | None = None,
    ) -> dict[str, Any]:
        reason = _required_text(reason, "reason")
        definitions = _validated_steps(steps)
        revised_goal = _required_text(goal, "goal") if goal is not None else None

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            existing_steps = self._steps(session, plan)

            if plan.current_step_number is not None:
                current = self._step(session, plan, plan.current_step_number)
                if current.status == StepStatus.awaiting_review:
                    raise PlanStateError(
                        "Review the latest tool result before revising the plan."
                    )
                latest = self._latest_attempt(session, current)
                if latest is not None and latest.status == AttemptStatus.running:
                    raise PlanStateError(
                        "Finish the running tool execution before revising the plan."
                    )

            timestamp = utc_now()
            for step in existing_steps:
                if step.status in {
                    StepStatus.pending,
                    StepStatus.in_progress,
                    StepStatus.failed,
                }:
                    step.status = StepStatus.skipped
                    step.result_summary = f"Superseded by revision: {reason}"
                    step.completed_at = timestamp

            first_number = max(
                (step.number for step in existing_steps), default=0
            ) + 1
            session.add_all(
                PlanStep(
                    plan_id=plan.id,
                    number=first_number + offset,
                    title=title,
                    expected_result=expected_result,
                )
                for offset, (title, expected_result) in enumerate(definitions)
            )

            plan.goal = revised_goal or plan.goal
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
    def _close_plan(
        session: Session,
        plan: ExecutionPlan,
        status: PlanStatus,
        summary: str,
    ) -> None:
        timestamp = utc_now()
        plan.status = status
        plan.final_summary = summary
        plan.current_step_number = None
        plan.completed_at = timestamp
        plan.updated_at = timestamp

        request = session.get(PlanRequest, plan.request_id)
        if request is None or request.session_id != plan.session_id:
            raise PlanStateError("The plan's user request does not exist.")
        request.status = status
        request.finished_at = timestamp

    def finish_plan(self, summary: str) -> dict[str, Any]:
        summary = _required_text(summary, "summary")

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                raise PlanStateError("Resolve the current step before finishing.")

            steps = self._steps(session, plan)
            unfinished = [
                step.number
                for step in steps
                if step.status not in {StepStatus.completed, StepStatus.skipped}
            ]
            if unfinished:
                raise PlanStateError(f"Unfinished plan steps: {unfinished}")
            if not any(
                step.status == StepStatus.completed and step.attempt_count > 0
                for step in steps
            ):
                raise PlanStateError(
                    "At least one completed step with a tool result is required."
                )

            self._close_plan(session, plan, PlanStatus.completed, summary)

        return self.compact_snapshot()

    def block_plan(self, summary: str) -> dict[str, Any]:
        summary = _required_text(summary, "summary")

        with self._database_session(write=True) as session:
            plan = self._active_plan(session)
            if plan.current_step_number is not None:
                current = self._step(session, plan, plan.current_step_number)
                if current.status == StepStatus.awaiting_review:
                    raise PlanStateError(
                        "Review the latest tool result before blocking the plan."
                    )
                latest = self._latest_attempt(session, current)
                if latest is not None and latest.status == AttemptStatus.running:
                    raise PlanStateError(
                        "Finish the running tool execution before blocking the plan."
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

            self._close_plan(session, plan, PlanStatus.blocked, summary)

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
        data: dict[str, Any] = {
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
            data["attempts"] = [
                cls._attempt_data(attempt) for attempt in attempts
            ]
        return data

    @classmethod
    def _plan_data(
        cls, session: Session, plan: ExecutionPlan, *, full: bool
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
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
        request = self._request(session, pointer.request_id)
        plan = self._plan(session, pointer.plan_id)

        current_request: dict[str, Any] | None = None
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

        state: dict[str, Any] = {
            "version": 3,
            "current_request": current_request,
            "active_plan": (
                self._plan_data(session, plan, full=full) if plan is not None else None
            ),
        }
        if full:
            history = session.exec(
                select(ExecutionPlan)
                .where(
                    ExecutionPlan.session_id == self.session_id,
                    ExecutionPlan.id != pointer.plan_id,
                )
                .order_by(ExecutionPlan.created_at)
            )
            state["history"] = [self._plan_summary(item) for item in history]

        return state

    def snapshot(self) -> dict[str, Any]:
        with self._database_session() as session:
            return self._snapshot(session, full=True)

    def compact_snapshot(self) -> dict[str, Any]:
        with self._database_session() as session:
            return self._snapshot(session, full=False)

    def prompt_snapshot(self) -> str:
        return json.dumps(self.compact_snapshot(), ensure_ascii=False, indent=2)

    def list_plans(self) -> list[dict[str, Any]]:
        with self._database_session() as session:
            plans = session.exec(
                select(ExecutionPlan)
                .where(ExecutionPlan.session_id == self.session_id)
                .order_by(ExecutionPlan.created_at.desc())
            )
            return [self._plan_summary(plan) for plan in plans]

    def plan_history(self, plan_id: str) -> dict[str, Any]:
        plan_id = _required_text(plan_id, "plan_id")
        with self._database_session() as session:
            plan = self._plan(session, plan_id)
            if plan is None:
                raise PlanStateError(f"Plan {plan_id} does not exist.")
            return self._plan_data(session, plan, full=True)

    def step_history(
        self, step_id: int, plan_id: str | None = None
    ) -> dict[str, Any]:
        step_id = _positive_integer(step_id, "step_id")
        with self._database_session() as session:
            selected_plan_id = plan_id or self._pointer(session).plan_id
            if selected_plan_id is None:
                raise PlanStateError("There is no current plan. Provide a plan_id.")
            plan = self._plan(session, selected_plan_id)
            if plan is None:
                raise PlanStateError(f"Plan {selected_plan_id} does not exist.")
            return self._step_data(
                session,
                self._step(session, plan, step_id),
                full=True,
            )

    def current_request_status(self) -> str | None:
        with self._database_session() as session:
            pointer = self._pointer(session)
            request = self._request(session, pointer.request_id)
            return request.status if request is not None else None


plan_store = PlanStore()
