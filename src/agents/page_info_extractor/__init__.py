from .agent import InfoExtractorAgent
from .utils.subagents import triage_agent, generator_agent

__all__ = ["InfoExtractorAgent", "triage_agent", "generator_agent"]

root_agent = InfoExtractorAgent(
    name="SiteInfoExtractor",
    triage_agent=triage_agent,
    generator_agent=generator_agent
)