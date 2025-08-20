from google.adk.agents import LlmAgent
from pydantic import BaseModel
from prompts import GENERATOR_PROMPT, TRIAGE_PROMPT

class ReponseSchema(BaseModel):
    valid: bool
    url: str
    request: str

triage_agent = LlmAgent(
    name="Triage Agent",
    description="Outputs structured response, with whether the request is valid and url, request data",
    model="gemini-2.5-flash-lite",
    instruction=TRIAGE_PROMPT,
    output_schema=ReponseSchema,
    output_key="triage_result"
)

generator_agent = LlmAgent(
    name="Generator Agent",
    description="Generates report using provided information",
    model="gemini-2.5-flash",
    instruction=GENERATOR_PROMPT
)