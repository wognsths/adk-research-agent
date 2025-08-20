#!/usr/bin/env python3
"""
Example usage of the InfoExtractorAgent
"""
import asyncio
from google.adk.runners import InMemoryRunner
from google.adk.types import Content, Part

from agent import InfoExtractorAgent
from utils.agents import triage_agent, generator_agent


async def main():
    # Create the InfoExtractorAgent
    info_extractor = InfoExtractorAgent(
        name="PageInfoExtractor",
        triage_agent=triage_agent,
        generator_agent=generator_agent
    )
    
    # Create a runner
    runner = InMemoryRunner(info_extractor)
    
    # Create a session
    session = await runner.session_service().create_session(
        app_name=runner.app_name(),
        user_id="test_user",
        initial_state={},
        session_id="test_session"
    ).to_aio()
    
    # Example user request
    user_request = "https://www.zarathu.com/ 에서 이 회사가 어떤 사업을 하는지 알아보고 싶어"
    user_content = Content(parts=[Part(text=user_request)])
    
    print(f"User: {user_request}")
    print("\nAgent Response:")
    
    # Run the agent
    events = runner.run_async(session.user_id, session.id, user_content)
    
    async for event in events.to_aio():
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(main())