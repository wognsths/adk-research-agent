# Page Info Extractor Agent

The Page Info Extractor Agent is a Google ADK-based agent that crawls web pages and extracts relevant information based on user queries.

## Architecture

The agent consists of three main components:

1. **Triage Agent**: Validates user requests and extracts URL and query information
2. **Crawler**: Crawls the website and saves HTML files locally
3. **Evaluator**: Analyzes HTML files using Gemini to extract relevant information
4. **Generator Agent**: Creates a structured report from the extracted information

## Workflow

1. User provides a request containing a URL and information they want to extract
2. Triage Agent validates the request and extracts structured data
3. Crawler visits the website and saves HTML files to local storage
4. Evaluator analyzes each HTML file against the user's query using Gemini
5. Generator Agent creates a comprehensive report from the extracted information

## Setup

1. Set your Google API key in the `.env` file:
   ```
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

2. Install required dependencies:
   ```bash
   pip install google-adk httpx selectolax tldextract pydantic pydantic-settings
   ```

## Usage

```python
from page_info_extractor import InfoExtractorAgent
from page_info_extractor.utils.agents import triage_agent, generator_agent

# Create the agent
agent = InfoExtractorAgent(
    name="PageInfoExtractor",
    triage_agent=triage_agent,
    generator_agent=generator_agent
)

# Use with ADK runner
```

## Configuration

The agent can be configured through environment variables in `.env`:

- `GOOGLE_API_KEY`: Your Google API key for Gemini models
- `GENAI_MODEL`: The Gemini model to use (default: gemini-2.5-flash-lite)
- `MAX_CONCURRENCY`: Number of concurrent requests (default: 10)
- `MAX_PAGES`: Maximum pages to crawl (default: 50)
- `TIMEOUT`: Request timeout in seconds (default: 15)

## Components

### Crawler (`crawler/`)
- `crawler.py`: Main crawler implementation
- `config.py`: Crawler configuration settings
- Saves HTML files to `./pages` directory
- Creates `index.csv` with crawled page metadata

### Evaluator (`eval/`)
- `eval.py`: Information extraction using Gemini
- `main.py`: CLI interface and batch processing
- `config.py`: Evaluator configuration
- Reads HTML files from local storage
- Extracts relevant information based on user queries

### Utils (`utils/`)
- `agents.py`: Triage and Generator agent definitions
- `prompts.py`: System prompts for agents
- `util.py`: Utility functions for URL handling and data coercion

## Example

```
User: "https://example.com에서 이 회사가 어떤 사업을 하는지 알아보고 싶어"

Agent Response:
Starting to crawl https://example.com to gather information...
Successfully crawled 25 pages from https://example.com
Analyzing crawled pages to extract relevant information...

--------------------
[요약]
- Example Company는 주로 소프트웨어 개발 및 IT 컨설팅 사업을 운영
- 클라우드 솔루션과 웹 애플리케이션 개발에 특화
- 2010년 설립되어 현재 50명의 직원을 보유

[세부 내용]
- 주요 서비스: 웹 애플리케이션 개발, 모바일 앱 개발, 클라우드 마이그레이션
- 주요 고객: 중소기업 및 스타트업 대상
- 기술 스택: React, Node.js, AWS, Docker

[출처]
- https://example.com
--------------------
```