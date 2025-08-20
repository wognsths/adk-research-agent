from google.adk.agents import BaseAgent, LlmAgent
from typing import override, AsyncGenerator
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from .utils.util import ensure_https, coerce_to_dict
from .crawler.crawler import Crawler
from .eval.main import _amain

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
        # Debug: Print the user's message
        if ctx.user_content and ctx.user_content.parts:
            user_message = ""
            for part in ctx.user_content.parts:
                if part.text:
                    user_message += part.text
            print(f"[{self.name}] User message: {user_message}")
        
        async for event in self.triage_agent.run_async(ctx):
            print(f"[{self.name}] Running Triage...")
            yield event

        raw = ctx.session.state.get("triage_result")
        if not raw:
            print(f"[{self.name}] Failed to generate response in **triage agent** (missing triage_result)")
            yield Event(author=self.name, content=Content(parts=[Part(text="Triage failed: no triage_result in state.")]))
            return
        
        # Debug: Print triage result
        print(f"[{self.name}] Raw triage result: {raw}")
        print(f"[{self.name}] Triage result type: {type(raw)}")

        data = coerce_to_dict(raw)

        data["url"] = ensure_https(str(data.get("url", "")))
        data["request"] = str(data.get("request", "")).strip()
        if "valid" not in data:
            data["valid"] = bool(data["url"] and data["request"])

        if not data["valid"] or (data["valid"] == "false"):
            yield Event(author=self.name, content=Content(parts=[Part(text="The request is not valid. Please try again with valid request")]))
            return
        
        url = data["url"]
        request_query = data["request"]
        
        print(f"[{self.name}] Starting crawling for URL: {url}")
        yield Event(author=self.name, content=Content(parts=[Part(text=f"Starting to crawl {url} to gather information...")]))
        
        # Step 1: Run crawler to save HTML files locally
        crawler = Crawler(start_url=url, out_dir="./pages")
        try:
            total_pages = await crawler.run()
            print(f"[{self.name}] Crawled {total_pages} pages successfully")
            yield Event(author=self.name, content=Content(parts=[Part(text=f"Successfully crawled {total_pages} pages from {url}")]))
        except Exception as e:
            print(f"[{self.name}] Crawler failed: {e}")
            yield Event(author=self.name, content=Content(parts=[Part(text=f"Failed to crawl {url}: {str(e)}")]))
            return
        
        # Step 2: Run evaluator to extract information from local HTML files
        print(f"[{self.name}] Starting evaluation of crawled pages...")
        yield Event(author=self.name, content=Content(parts=[Part(text="Analyzing crawled pages to extract relevant information...")]))
        
        try:
            results = await _amain(request_query, "./pages")
            print(f"[{self.name}] Evaluation completed, found {len(results)} relevant results")
            
            # Extract core information from results
            extracted_info = []
            for result in results:
                if result.get('result') and isinstance(result['result'], list):
                    for item in result['result']:
                        if item.get('is_valid', False) and item.get('core_informations'):
                            extracted_info.extend(item['core_informations'])
            
            if not extracted_info:
                yield Event(author=self.name, content=Content(parts=[Part(text="No relevant information found in the crawled pages.")]))
                return
            
            # Step 3: Pass extracted information to generator agent
            print(f"[{self.name}] Passing extracted information to generator agent...")
            
            # Format extracted information for the generator prompt
            extracted_info_text = "\n".join([f"- {info}" for info in extracted_info])
            
            # Create the context message for generator
            from .utils.prompts import GENERATOR_PROMPT
            generator_prompt = GENERATOR_PROMPT.format(
                original_query=request_query,
                source_url=url,
                extracted_info=extracted_info_text
            )
            
            # Update the generator agent's instruction with the formatted prompt
            original_instruction = self.generator_agent.instruction
            self.generator_agent.instruction = generator_prompt
            
            try:
                async for event in self.generator_agent.run_async(ctx):
                    print(f"[{self.name}] Running Generator...")
                    yield event
            finally:
                # Restore original instruction
                self.generator_agent.instruction = original_instruction
                
        except Exception as e:
            print(f"[{self.name}] Evaluation failed: {e}")
            yield Event(author=self.name, content=Content(parts=[Part(text=f"Failed to analyze crawled pages: {str(e)}")]))
            return

            