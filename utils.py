import io
import os
import re
import shutil
import tempfile
import textwrap
import urllib
import urllib.request
from datetime import datetime, timedelta
from logging import Logger
from pprint import pformat
from typing import Any, Optional, cast

import fitz
from arxiv import Client, Result, Search, SortCriterion
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.runnables.base import Runnable
from langchain_ollama import ChatOllama
from langgraph.graph.graph import CompiledGraph
from PIL import Image

from const import Paper, PaperGist, PaperList


def fetch_papers(
    category: str, date: datetime, max_papers: int, logger: Logger
) -> list[Result]:
    client = Client(page_size=80)
    search = Search(
        query=f"cat:{category}",
        max_results=80,  # get a large number of papers first
        sort_by=SortCriterion.SubmittedDate,
    )
    all_results = list(client.results(search=search))
    selected = [
        r for r in all_results if date <= r.published < (date + timedelta(days=1))
    ]
    logger.info(
        f"found {len(selected)} papers published on {date.strftime('%Y-%m-%d')}"
    )
    selected_sorted = sorted(
        selected, key=lambda x: len(str(x.journal_ref)), reverse=True
    )  # prioritize papers already published in a journal
    return selected_sorted[:max_papers]


def generate_gist(
    summarizer: CompiledGraph | ChatOllama,
    formatter: Runnable[LanguageModelInput, PaperGist],
    title: str,
    abstract: str,
    logger: Logger,
) -> PaperGist:
    summarizer_input_text = textwrap.dedent(f"""
        You are a renowned professor in Computer Science. \
        Your lab student, who is well versed in various Computer Science fields, asked you to write a concise summary about the following academic paper utilizing your expertise.

        Your summary can be written in a free format, but should answer questions below:
        - [About] What did this research do?
        - [Objective] What did this research tried to achieve?
        - [Novelty] How is this research superior to existing ones?
        - [Key] What are the most important findings of this research?

        ```
        [Paper Information]
        title: {title}
        abstract: {abstract}
        ```
        """)

    # input type is different depending on whether the summarizer is an agent or not
    if isinstance(summarizer, CompiledGraph):
        summarizer_input_text = (
            # here, the LLM is equipped with web search tools. So adding a short instruction about them.
            summarizer_input_text  #               NOTE: is this specification in paren necessary? vvvvvvvvvvvvvvvvvvvvvvvvvvvv
            + "\nYou can use tools given to you to obtain additional information about unfamiliar (even to CS graduate students) notions and keywords that appear in the abstract. Whether to use tools is up to you, but if you decide to use them, they MUST be used BEFORE you start to write the summary. "
            + "Additionally, when you actually used tools to obtain information about a keyword from a Web article which turned out to be written in English and ACTUALLY INDISPENSIBLE to understand the research paper, "
            + "write its URL and title (that come as part of tools' responses) in the reference section at the bottom of the final summary. The reference section should ONLY exist when actual tool calls are made. The reference section should ONLY include urls that were really helpful, and shouldn't include random articles merely sharing similar concepts. "
            + "Moreover, please don't include any URLs of the paper itself, arxiv.org, www.mdpi.com, or placeholder URLs like example.com, which are not real URLs, in ANY of your outputs."
        )
        summarizer_input = {"messages": [HumanMessage(summarizer_input_text)]}
        summarizer_model_name = summarizer.get_name()
    else:
        summarizer_input = [HumanMessage(summarizer_input_text)]
        summarizer_model_name = summarizer.model

    logger.info(
        f'starting summary generation for "{title}" with {summarizer_model_name}'
    )
    summarizer_output = cast(
        # agent returns the state (dict[str, Any]), while simple LLM returns an AIMessage
        dict[str, Any] | AIMessage,
        summarizer.invoke(input=summarizer_input),  # type: ignore
    )
    logger.debug(
        pformat(
            object=summarizer_output.model_dump()
            if isinstance(summarizer_output, AIMessage)
            else {
                **summarizer_output,
                "messages": [m.model_dump() for m in summarizer_output["messages"]],
            },
            width=shutil.get_terminal_size().columns,
        )
    )
    logger.info(f'finished summary generation for "{title}"')

    logger.info("starting formatting into JSON")
    try:
        # strip reasoning tokens first
        summarizer_output_text = re.sub(
            pattern=r"<think>.+?<\/think>",
            repl="",
            string=summarizer_output.content
            if isinstance(summarizer_output, AIMessage)
            else summarizer_output["messages"][-1].content,  # type: ignore
            flags=re.DOTALL,
        ).strip()
        # then format the summary into a PaperGist instance
        paper_gist = formatter.invoke(
            input=[
                HumanMessage(
                    textwrap.dedent(f"""
                    Format the following summary of an academic paper in Computer Science into the specified format.

                    [Format Instructions]
                    - Each point should be around 50 words, and no newline character may be included.
                    - When you want to emphasize words, be sure to surround them with *single asterisk at each end*, not double asterisks.

                    [Paper Summary]
                    {summarizer_output_text}
                    """)
                )
            ]
        )
        logger.debug(
            pformat(
                object=paper_gist.model_dump(), width=shutil.get_terminal_size().columns
            )
        )
        logger.info("finished formatting")
        return paper_gist
    except Exception as e:
        logger.error("failed to format the summary")
        raise e


def get_first_figure(pdf_url: str, data_dir: str, logger: Logger) -> Optional[str]:
    # TODO: filter picture with aspect ratio
    pdf_name = os.path.basename(pdf_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        # download pdf to temporary directory
        with urllib.request.urlopen(pdf_url) as web_stream:
            pdf_path = os.path.join(tmpdir, pdf_name)
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(web_stream.read())
        # open pdf and search for images
        pdf = fitz.open(pdf_path)
        for page in pdf:
            images = page.get_images()  # type:ignore
            if not images:
                continue
            # extract reference number to the first image in this PDF
            first_image = images[0]
            image_xref: int = first_image[0]
            # extract image itself and save it
            base_image = pdf.extract_image(xref=image_xref)
            try:
                image = Image.open(io.BytesIO(base_image["image"]))
            except Exception as e:
                logger.error(f"failed to extract an image: {e}")
            else:
                # check the aspect ratio of this image.
                # since the figure describing the overall workflow tends to
                # be long in horizontal direction, we only accept image whose
                # ratio is more than 4 : 3
                MIN_RATIO = 4 / 3
                w, h = image.size
                if (w / h) < MIN_RATIO:
                    continue
                image_path = os.path.join(
                    data_dir,
                    "images",
                    f"{pdf_name}.{base_image['ext']}",
                )
                image.save(image_path)
                logger.info(
                    f"extracted image from {pdf_name} and saved it at {image_path}"
                )
                return image_path
        logger.info(f"found no image in {pdf_name}")
        return None  # no image was found in the pdf


def process_results(
    search_results: list[Result],
    date: datetime,
    summarizer: CompiledGraph | ChatOllama,
    formatter: Runnable[LanguageModelInput, PaperGist],
    data_dir: str,
    logger: Logger,
) -> PaperList:
    papers = []
    for result in search_results:
        try:
            gist = generate_gist(
                summarizer=summarizer,
                formatter=formatter,
                title=result.title,
                abstract=result.summary,
                logger=logger,
            )
        except Exception as e:
            # failed to generate gist for this paper
            logger.info(
                f"failed to generate gist for this paper due to the following error: {e}, continuing"
            )
            continue
        first_figure_path = (
            get_first_figure(pdf_url=result.pdf_url, data_dir=data_dir, logger=logger)
            if result.pdf_url
            else None
        )
        paper = Paper(
            title=result.title,
            author=", ".join(
                map(lambda author: author.name, result.authors)
            ),  # generate comma-separated list of authors
            gist=gist,
            url=result.entry_id,
            first_figure_path=first_figure_path,
        )
        papers.append(paper)
    return PaperList(papers=papers, date=date)
