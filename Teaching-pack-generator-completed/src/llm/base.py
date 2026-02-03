from pydantic_ai import Agent
from typing import List, Callable, Optional, Type, TypeVar, cast
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
import os
from data.cache.redis_cache import ShortTermMemory

provider = GoogleProvider(api_key=os.getenv("GEMINI_API_KEY"))
model = GoogleModel("gemini-2.0-flash", provider=provider)
session_manager = ShortTermMemory(max_messages=15)

T = TypeVar('T')


class AgentClient:
    def __init__(
        self, system_prompt: str, tools: List[Callable], model: GoogleModel = model
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools

    def create_agent(self, result_type: Optional[Type[T]] = None):
        """Creates and returns a PydanticAI Agent instance."""
        if result_type:
            # In pydantic-ai 1.39.0+, use output_type instead of result_type
            agent: Agent[None, T] = Agent(
                model=self.model, 
                system_prompt=self.system_prompt, 
                tools=self.tools,
                output_type=result_type  # type: ignore
            )
            return agent
        return Agent(model=self.model, system_prompt=self.system_prompt, tools=self.tools)
