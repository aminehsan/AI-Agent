import uuid
import tempfile
import unittest
from asyncio import run
from inspect import signature
from pathlib import Path
from agents import RunContextWrapper
from app.settings import settings
from app.agent import create_agent


class ToolRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.original_root = settings.project_root
        self.original_session = settings.session_id
        settings.project_root = Path(self.temporary.name)
        settings.session_id = f"tools-{uuid.uuid4().hex}"

    def tearDown(self) -> None:
        settings.project_root = self.original_root
        settings.session_id = self.original_session
        self.temporary.cleanup()

    def test_only_three_model_facing_tools_are_registered(self) -> None:
        agent = create_agent()
        self.assertEqual(
            [tool.name for tool in agent.tools], ["plan", "filesystem", "run_command"]
        )
        self.assertFalse(agent.model_settings.parallel_tool_calls)

    def test_dynamic_instructions_accept_context_and_agent(self) -> None:
        agent = create_agent()
        self.assertEqual(len(signature(agent.instructions).parameters), 2)
        prompt = run(agent.get_system_prompt(RunContextWrapper(context=None)))
        self.assertIn("Mandatory workflow", prompt)

    def test_action_tools_use_discriminated_strict_schemas(self) -> None:
        agent = create_agent()
        schemas = {tool.name: tool.params_json_schema for tool in agent.tools}
        self.assertEqual(schemas["plan"]["required"], ["request"])
        self.assertEqual(schemas["filesystem"]["required"], ["request"])
        self.assertEqual(schemas["run_command"]["required"], ["request"])
