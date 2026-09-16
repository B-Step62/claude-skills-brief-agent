from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def load_llm(monkeypatch):
    monkeypatch.delenv("BRIEF_AGENT_MODEL_ENDPOINT", raising=False)
    monkeypatch.setenv("BRIEF_AGENT_PROFILE", "test-profile")

    def load(endpoint=None):
        if endpoint is not None:
            monkeypatch.setenv("BRIEF_AGENT_MODEL_ENDPOINT", endpoint)

        class WorkspaceClient:
            def __init__(self, *, profile):
                self.profile = profile

        class ChatDatabricks:
            instances: ClassVar[list] = []

            def __init__(self, *, endpoint, workspace_client):
                self.endpoint = endpoint
                self.workspace_client = workspace_client
                self.calls = []
                self.responses = []
                self.instances.append(self)

            def invoke(self, messages, **kwargs):
                self.calls.append((messages, kwargs))
                return SimpleNamespace(content=self.responses.pop(0))

        class HumanMessage:
            def __init__(self, content):
                self.content = content

        class SystemMessage:
            def __init__(self, content):
                self.content = content

        databricks = ModuleType("databricks")
        databricks.__path__ = []
        sdk = ModuleType("databricks.sdk")
        sdk.WorkspaceClient = WorkspaceClient
        databricks.sdk = sdk
        databricks_langchain = ModuleType("databricks_langchain")
        databricks_langchain.ChatDatabricks = ChatDatabricks
        langchain_core = ModuleType("langchain_core")
        langchain_core.__path__ = []
        messages = ModuleType("langchain_core.messages")
        messages.HumanMessage = HumanMessage
        messages.SystemMessage = SystemMessage
        langchain_core.messages = messages

        spec = importlib.util.spec_from_file_location(
            "brief_agent_llm_under_test", ROOT / "plain/brief_agent/llm.py"
        )
        module = importlib.util.module_from_spec(spec)
        with monkeypatch.context() as imports:
            for dependency in (databricks, sdk, databricks_langchain, langchain_core, messages):
                imports.setitem(sys.modules, dependency.__name__, dependency)
            spec.loader.exec_module(module)

        return module

    return load


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (None, "databricks-qwen3-next-80b-a3b-instruct"),
        ("custom-model", "custom-model"),
    ],
)
def test_endpoint_is_selected_at_import_and_forwarded_to_model(
    load_llm, monkeypatch, endpoint, expected
):
    llm = load_llm(endpoint)
    monkeypatch.setenv("BRIEF_AGENT_MODEL_ENDPOINT", "changed-after-import")

    model = llm._get_model()

    assert llm.MODEL_ENDPOINT == expected
    assert model.endpoint == expected
    assert model.workspace_client.profile == "test-profile"
    assert llm._get_model() is model
    assert len(llm.ChatDatabricks.instances) == 1


def test_complete_returns_visible_answer_with_default_token_limit_without_retry(load_llm):
    llm = load_llm()
    model = llm._get_model()
    model.responses = ["  Visible answer.  "]

    answer = llm.complete("System instructions", "User request")

    assert answer == "Visible answer."
    assert llm.MAX_OUTPUT_TOKENS == 8_000
    assert llm.MIN_RETRY_OUTPUT_TOKENS == 8_000
    assert len(model.calls) == 1
    messages, kwargs = model.calls[0]
    assert [type(message) for message in messages] == [llm.SystemMessage, llm.HumanMessage]
    assert [message.content for message in messages] == ["System instructions", "User request"]
    assert kwargs == {"max_tokens": 8_000, "temperature": 0.3, "reasoning_effort": "low"}


@pytest.mark.parametrize(
    "first_response",
    [
        "",
        [{"type": "reasoning", "reasoning": "Hidden reasoning."}],
        '[{"type": "reasoning", "reasoning": "Hidden reasoning."}]',
    ],
)
@pytest.mark.parametrize(
    ("max_tokens", "retry_tokens"),
    [(1_000, 8_000), (4_500, 9_000), (8_000, 10_000), (12_000, 10_000)],
)
def test_empty_visible_answer_retries_with_bounded_token_budget(
    load_llm, first_response, max_tokens, retry_tokens
):
    llm = load_llm()
    model = llm._get_model()
    model.responses = [first_response, [{"type": "text", "text": "Retry answer."}]]

    answer = llm.complete(
        "System instructions",
        "User request",
        max_tokens=max_tokens,
        temperature=0.1,
        reasoning_effort="medium",
    )

    assert answer == "Retry answer."
    assert len(model.calls) == 2
    assert model.calls[0][1] == {
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "reasoning_effort": "medium",
    }
    assert model.calls[1][1] == {
        "max_tokens": retry_tokens,
        "temperature": 0.1,
        "reasoning_effort": "medium",
    }
    assert model.calls[1][0] is model.calls[0][0]


def test_complete_retries_only_once_when_both_responses_are_empty(load_llm):
    llm = load_llm()
    model = llm._get_model()
    model.responses = ["", [{"type": "reasoning", "reasoning": "Still hidden."}]]

    assert llm.complete("", "User request") == ""
    assert [kwargs["max_tokens"] for _, kwargs in model.calls] == [8_000, 10_000]
    assert len(model.calls[0][0]) == 1
    assert isinstance(model.calls[0][0][0], llm.HumanMessage)
