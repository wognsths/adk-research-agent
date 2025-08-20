from google.adk.agents import LlmAgent
from pydantic import BaseModel
from .prompts import GENERATOR_PROMPT, TRIAGE_PROMPT

class ResponseSchema(BaseModel):
    valid: bool
    url: str
    request: str

triage_agent = LlmAgent(
    name="Triage_Agent",
    description="Outputs structured response, with whether the request is valid and url, request data",
    model="gemini-2.5-pro",
    instruction=TRIAGE_PROMPT,
    output_schema=ResponseSchema,
    output_key="triage_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

generator_agent = LlmAgent(
    name="Generator_Agent",
    description="Generates report using provided information",
    model="gemini-2.5-flash",
    instruction=GENERATOR_PROMPT
)