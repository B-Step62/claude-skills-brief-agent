"""Contract tests for the participant agent's Terra model boundary."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PLAIN_DIR = Path(__file__).resolve().parents[1] / "plain"
sys.path.insert(0, str(PLAIN_DIR))

from brief_agent import llm  # noqa: E402


class TerraCompatibleModel:
    """Small local substitute that enforces Terra's request constraints."""

    def invoke(self, messages, **kwargs):
        temperature = kwargs.get("temperature", 1)
        if temperature != 1:
            return SimpleNamespace(content="INVALID_TEMPERATURE")
        if kwargs.get("reasoning_effort") != "low":
            return SimpleNamespace(content="INVALID_REASONING_EFFORT")
        if not messages:
            return SimpleNamespace(content="MISSING_MESSAGES")
        return SimpleNamespace(content="TERRA_OK")


class LlmContractTest(unittest.TestCase):
    def tearDown(self):
        llm._model = None

    def test_model_factory_targets_terra_serving_endpoint(self):
        class TerraEndpoint:
            def __init__(self, *, endpoint, workspace_client):
                self.endpoint = endpoint
                self.workspace_client = workspace_client

            def invoke(self, messages):
                if self.endpoint != "databricks-gpt-5-6-terra":
                    return SimpleNamespace(content="WRONG_ENDPOINT")
                if self.workspace_client != "workspace-client":
                    return SimpleNamespace(content="WRONG_WORKSPACE_CLIENT")
                return SimpleNamespace(content="TERRA_OK")

        with (
            patch.object(llm, "WorkspaceClient", return_value="workspace-client"),
            patch.object(llm, "ChatDatabricks", TerraEndpoint),
        ):
            response = llm._get_model().invoke([])

        self.assertEqual(response.content, "TERRA_OK")

    def test_complete_uses_terra_compatible_chat_parameters(self):
        with patch.object(llm, "_get_model", return_value=TerraCompatibleModel()):
            answer = llm.complete("Follow the instruction.", "Reply with TERRA_OK")

        self.assertEqual(answer, "TERRA_OK")


if __name__ == "__main__":
    unittest.main()
