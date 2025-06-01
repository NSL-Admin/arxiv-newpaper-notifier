import re

import requests
from bs4 import BeautifulSoup, Comment
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.runnables.base import Runnable
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from const import REQUEST_HEADERS, PaperGist


class FetchContentAtURLInput(BaseModel):
    url: str = Field(description="The HTTP or HTTPS URL to fetch content from")


@tool(args_schema=FetchContentAtURLInput)
def fetch_content_at_url(
    url: str,
) -> str:
    """Retrieve raw content from a specific URL.
    Use this tool when you need to inspect exact content hosted at a URL

    Input requirements:
    - Must be full URL with scheme (http:// or https://)
    - No search queries or partial URLs

    Output format:
    Success:
      Raw text content (HTML/JS/Text) if decodable
    Failure:
      Structured error message with type and details:
      - "FAILED TO FETCH CONTENT: {error_type}: {details}"

    Examples:
      Good input: "https://medium.com/data-science-at-microsoft/using-differential-privacy-to-understand-usage-patterns-in-ai-applications-ad6538a81f30"
      Output (success): "text from website"

    Note: Only retrieves exact URL content - does not execute JS.
    """
    try:
        r = requests.get(
            url=url, allow_redirects=True, timeout=10, headers=REQUEST_HEADERS
        )
        r.raise_for_status()
    except Exception as e:
        return f"FAILED TO FETCH CONTENT: {type(e).__name__}: {e}"
    else:
        decoded_text = r.text
        content_type = r.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            try:
                soup = BeautifulSoup(decoded_text, "html.parser")

                # Remove script, style, and noscript tags
                for element_to_remove in soup.find_all(["script", "style", "noscript"]):
                    element_to_remove.decompose()

                # Remove HTML comments
                for comment in soup.find_all(
                    string=lambda text: isinstance(text, Comment)
                ):
                    comment.extract()

                # Get the remaining text content
                # separator=' ' adds a space between text from different tags, strip=True removes leading/trailing whitespace
                cleaned_text = soup.get_text(separator=" ", strip=True)

                # Further clean up multiple spaces/newlines if desired,
                # though get_text(strip=True) handles a lot of it.
                cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

                return cleaned_text
            except Exception:
                # Fallback to returning the original decoded_text if HTML processing fails
                return decoded_text
        else:
            # If not HTML, but successfully decoded (e.g., JS, CSS, plain text), return the raw decoded text
            return decoded_text


def prepare_llms(
    summarizer_llm_name: str,
    formatter_llm_name: str,
    summarizer_as_agent: bool,
    ollama_api_base_url: str,
    debug: bool,
) -> tuple[CompiledGraph | ChatOllama, Runnable[LanguageModelInput, PaperGist]]:
    summarizer = ChatOllama(
        model=summarizer_llm_name,
        num_ctx=10240,  # sufficiently large context to utilize both user's input and tool's output for reasoning
        num_predict=3072,
        base_url=ollama_api_base_url,
        verbose=debug,
    )
    if summarizer_as_agent:
        summarizer = create_react_agent(
            model=summarizer,
            tools=[DuckDuckGoSearchResults(output_format="json"), fetch_content_at_url],
            name=summarizer.model,
            debug=debug,
        )

    formatter = (
        ChatOllama(
            model=formatter_llm_name,
            num_predict=1024,
            temperature=0.1,
            base_url=ollama_api_base_url,
            verbose=debug,
        )
        .with_structured_output(PaperGist, method="json_schema")
        .with_retry(stop_after_attempt=5)
    )
    return summarizer, formatter  # type: ignore
