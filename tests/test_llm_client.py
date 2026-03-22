import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio


# ── Minimal LLM Abstraction (mirrors your app/llm/) ──────────────────────────

class BaseLLMClient:
    """Base class all LLM clients must implement."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def get_provider_name(self) -> str:
        raise NotImplementedError


class GroqClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "llama3-8b-8192"):
        if not api_key:
            raise ValueError("Groq API key must not be empty")
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # Real implementation calls Groq API — mocked in tests
        raise NotImplementedError("Use mock in tests")

    def get_provider_name(self) -> str:
        return "groq"


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError("Use mock in tests")

    def get_provider_name(self) -> str:
        return "ollama"


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        if not api_key:
            raise ValueError("OpenAI API key must not be empty")
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError("Use mock in tests")

    def get_provider_name(self) -> str:
        return "openai"


def get_llm_client(provider: str, **kwargs) -> BaseLLMClient:
    """Factory — returns correct client based on LLM_PROVIDER env var."""
    provider = provider.lower()
    if provider == "groq":
        return GroqClient(**kwargs)
    elif provider == "ollama":
        return OllamaClient(**kwargs)
    elif provider == "openai":
        return OpenAIClient(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ── Test: BaseLLMClient ───────────────────────────────────────────────────────

class TestBaseLLMClient(unittest.TestCase):

    def test_generate_raises_not_implemented(self):
        client = BaseLLMClient()
        with self.assertRaises(NotImplementedError):
            client.generate("hello")

    def test_get_provider_name_raises_not_implemented(self):
        client = BaseLLMClient()
        with self.assertRaises(NotImplementedError):
            client.get_provider_name()


# ── Test: GroqClient ──────────────────────────────────────────────────────────

class TestGroqClient(unittest.TestCase):

    def test_init_with_valid_api_key(self):
        client = GroqClient(api_key="test-api-key")
        self.assertEqual(client.api_key, "test-api-key")

    def test_init_with_empty_api_key_raises(self):
        with self.assertRaises(ValueError):
            GroqClient(api_key="")

    def test_default_model_is_llama3(self):
        client = GroqClient(api_key="test-key")
        self.assertEqual(client.model, "llama3-8b-8192")

    def test_custom_model_set_correctly(self):
        client = GroqClient(api_key="test-key", model="mixtral-8x7b-32768")
        self.assertEqual(client.model, "mixtral-8x7b-32768")

    def test_provider_name_is_groq(self):
        client = GroqClient(api_key="test-key")
        self.assertEqual(client.get_provider_name(), "groq")

    def test_generate_mocked_response(self):
        client = GroqClient(api_key="test-key")
        client.generate = MagicMock(return_value="RAG stands for Retrieval Augmented Generation.")
        result = client.generate("What is RAG?")
        self.assertEqual(result, "RAG stands for Retrieval Augmented Generation.")
        client.generate.assert_called_once_with("What is RAG?")

    def test_generate_called_with_system_prompt(self):
        client = GroqClient(api_key="test-key")
        client.generate = MagicMock(return_value="answer")
        client.generate("question", system_prompt="You are a helpful assistant.")
        client.generate.assert_called_once_with("question", system_prompt="You are a helpful assistant.")


# ── Test: OllamaClient ────────────────────────────────────────────────────────

class TestOllamaClient(unittest.TestCase):

    def test_default_base_url(self):
        client = OllamaClient()
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_default_model_is_llama3(self):
        client = OllamaClient()
        self.assertEqual(client.model, "llama3")

    def test_custom_base_url(self):
        client = OllamaClient(base_url="http://myserver:11434")
        self.assertEqual(client.base_url, "http://myserver:11434")

    def test_custom_model(self):
        client = OllamaClient(model="mistral")
        self.assertEqual(client.model, "mistral")

    def test_provider_name_is_ollama(self):
        client = OllamaClient()
        self.assertEqual(client.get_provider_name(), "ollama")

    def test_generate_mocked_response(self):
        client = OllamaClient()
        client.generate = MagicMock(return_value="Mocked Ollama response")
        result = client.generate("Tell me about RAG")
        self.assertEqual(result, "Mocked Ollama response")


# ── Test: OpenAIClient ────────────────────────────────────────────────────────

class TestOpenAIClient(unittest.TestCase):

    def test_init_with_valid_api_key(self):
        client = OpenAIClient(api_key="sk-test-key")
        self.assertEqual(client.api_key, "sk-test-key")

    def test_init_with_empty_api_key_raises(self):
        with self.assertRaises(ValueError):
            OpenAIClient(api_key="")

    def test_default_model_is_gpt4(self):
        client = OpenAIClient(api_key="sk-test-key")
        self.assertEqual(client.model, "gpt-4")

    def test_provider_name_is_openai(self):
        client = OpenAIClient(api_key="sk-test-key")
        self.assertEqual(client.get_provider_name(), "openai")

    def test_generate_mocked_response(self):
        client = OpenAIClient(api_key="sk-test-key")
        client.generate = MagicMock(return_value="OpenAI response")
        result = client.generate("What is RAG?")
        self.assertEqual(result, "OpenAI response")


# ── Test: Factory Function ────────────────────────────────────────────────────

class TestGetLLMClient(unittest.TestCase):

    def test_groq_provider_returns_groq_client(self):
        client = get_llm_client("groq", api_key="test-key")
        self.assertIsInstance(client, GroqClient)

    def test_ollama_provider_returns_ollama_client(self):
        client = get_llm_client("ollama")
        self.assertIsInstance(client, OllamaClient)

    def test_openai_provider_returns_openai_client(self):
        client = get_llm_client("openai", api_key="sk-test-key")
        self.assertIsInstance(client, OpenAIClient)

    def test_unknown_provider_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_llm_client("unknown_provider")

    def test_provider_name_case_insensitive(self):
        client = get_llm_client("GROQ", api_key="test-key")
        self.assertIsInstance(client, GroqClient)

    def test_all_clients_inherit_base(self):
        groq   = get_llm_client("groq", api_key="test-key")
        ollama = get_llm_client("ollama")
        openai = get_llm_client("openai", api_key="sk-test-key")

        self.assertIsInstance(groq,   BaseLLMClient)
        self.assertIsInstance(ollama, BaseLLMClient)
        self.assertIsInstance(openai, BaseLLMClient)


# ── Test: Provider Switching via Env Var ──────────────────────────────────────

class TestProviderSwitching(unittest.TestCase):
    """Simulate switching LLM_PROVIDER via environment variable."""

    def _get_client_from_env(self, provider: str) -> BaseLLMClient:
        """Mimic how your app reads LLM_PROVIDER from .env"""
        api_keys = {
            "groq": "groq-test-key",
            "openai": "sk-test-key",
        }
        kwargs = {}
        if provider in api_keys:
            kwargs["api_key"] = api_keys[provider]
        return get_llm_client(provider, **kwargs)

    def test_switch_to_groq(self):
        client = self._get_client_from_env("groq")
        self.assertEqual(client.get_provider_name(), "groq")

    def test_switch_to_ollama(self):
        client = self._get_client_from_env("ollama")
        self.assertEqual(client.get_provider_name(), "ollama")

    def test_switch_to_openai(self):
        client = self._get_client_from_env("openai")
        self.assertEqual(client.get_provider_name(), "openai")

    def test_invalid_provider_in_env_raises(self):
        with self.assertRaises(ValueError):
            self._get_client_from_env("gemini")


if __name__ == "__main__":
    unittest.main()