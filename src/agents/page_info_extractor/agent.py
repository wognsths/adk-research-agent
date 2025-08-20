from google.adk.agents import BaseAgent, LlmAgent
from typing import override, AsyncGenerator
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from utils.util import ensure_https, coerce_to_dict
from crawler.crawler import Crawler
from eval.main import _amain

class InfoExtractorAgent(BaseAgent):
    triage_agent: LlmAgent
    generator_agent: LlmAgent

    def __init__(
            self,
            name: str,
            triage_agent: LlmAgent,
            generator_agent: LlmAgent,
    ):
        sub_agents_list = [
            triage_agent,
            generator_agent
        ]

        super().__init__(
            name=name,
            triage_agent=triage_agent,
            generator_agent=generator_agent,
            sub_agents=sub_agents_list
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self.triage_agent.run_async(ctx):
            print(f"[{self.name}] Running Triage...")
            yield event

        raw = ctx.session.state.get("triage_result")
        if not raw:
            print(f"[{self.name}] Failed to generate response in **triage agent** (missing triage_result)")
            return Event(text="Triage failed: no triage_result in state.")

        data = coerce_to_dict(raw)

        data["url"] = ensure_https(str(data.get("url", "")))
        data["request"] = str(data.get("request", "")).strip()
        if "valid" not in data:
            data["valid"] = bool(data["url"] and data["request"])

        if not data["valid"] or (data["valid"] == "false"):
            return Event(text="The request is not valid. Please try again with valid request")
        

        
        


            