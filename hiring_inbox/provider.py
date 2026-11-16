"""Provider contract and its Groq Cloud implementation."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dotenv import dotenv_values
from groq import APIConnectionError, APIError, APIResponseValidationError, APIStatusError
from groq import APITimeoutError, Groq
from groq.types.chat import ChatCompletion
from pydantic import BaseModel


DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_REASONING_EFFORT = "medium"


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class Completion:
    content: str | None = None
    usage: TokenUsage | None = None
    failure: str | None = None


class StructuredProvider(Protocol):
    def complete(
        self, schema: type[BaseModel], instructions: str, payload: dict[str, str]
    ) -> Completion: ...


class GroqProvider:
    def __init__(self, client: Groq, model: str, reasoning_effort: str) -> None:
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort

    @classmethod
    def from_environment(cls, env_file: Path) -> "GroqProvider | None":
        # Read dotenv settings for this client only. The SDK receives the key directly.
        file_settings = dotenv_values(env_file, interpolate=False)
        api_key = (os.environ.get("GROQ_API_KEY", file_settings.get("GROQ_API_KEY")) or "").strip()
        if not api_key:
            return None
        model = os.environ.get("GROQ_MODEL", file_settings.get("GROQ_MODEL")) or DEFAULT_MODEL
        effort = (
            os.environ.get("GROQ_REASONING_EFFORT", file_settings.get("GROQ_REASONING_EFFORT"))
            or DEFAULT_REASONING_EFFORT
        )
        if model not in {DEFAULT_MODEL, "openai/gpt-oss-20b"}:
            raise ValueError("GROQ_MODEL must be a GPT-OSS model supported by this adapter")
        if effort not in {"low", "medium", "high"}:
            raise ValueError("GROQ_REASONING_EFFORT must be low, medium, or high")
        client = Groq(
            api_key=api_key,
            base_url="https://api.groq.com",
            timeout=15.0,
            max_retries=2,
            _strict_response_validation=True,
        )
        return cls(client, model, effort)

    def complete(
        self, schema: type[BaseModel], instructions: str, payload: dict[str, str]
    ) -> Completion:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                reasoning_effort=self.reasoning_effort,
                reasoning_format="hidden",
                max_completion_tokens=2048,
                temperature=0,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "strict": True,
                        "schema": schema.model_json_schema(),
                    },
                },
            )
        except APITimeoutError:
            return Completion(failure="timeout")
        except APIConnectionError:
            return Completion(failure="connection_error")
        except APIResponseValidationError as error:
            # The SDK's finish-reason enum omits content_filter.
            choices = error.body.get("choices") if isinstance(error.body, dict) else None
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                if choices[0].get("finish_reason") == "content_filter":
                    return Completion(failure="refusal")
            return Completion(failure="invalid_response")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Completion(failure="invalid_response")
        except APIStatusError as error:
            return Completion(failure=f"api_http_{error.status_code}")
        except APIError:
            return Completion(failure="api_error")

        if not isinstance(response, ChatCompletion):
            return Completion(failure="invalid_response")
        usage = None
        if response.usage is not None:
            tokens = response.usage
            usage = TokenUsage(
                prompt_tokens=tokens.prompt_tokens,
                completion_tokens=tokens.completion_tokens,
                cached_prompt_tokens=getattr(tokens.prompt_tokens_details, "cached_tokens", None),
                reasoning_tokens=getattr(tokens.completion_tokens_details, "reasoning_tokens", None),
            )
        if not response.choices:
            return Completion(usage=usage, failure="invalid_response")
        choice = response.choices[0]
        if getattr(choice.message, "refusal", None) or choice.finish_reason == "content_filter":
            return Completion(usage=usage, failure="refusal")
        if choice.finish_reason == "length":
            return Completion(usage=usage, failure="truncated_response")
        if choice.finish_reason != "stop" or not choice.message.content:
            return Completion(usage=usage, failure="invalid_response")
        return Completion(content=choice.message.content, usage=usage)
