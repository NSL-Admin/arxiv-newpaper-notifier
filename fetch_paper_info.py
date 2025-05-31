import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

from const import ARXIV_CATEGORIES
from llms import prepare_llms
from utils import fetch_papers, process_results

parser = argparse.ArgumentParser(
    description="Fetch information of the latest papers from arXiv, then update json"
)
parser.add_argument(
    "--category",
    help="Category ID to search for papers of",
    choices=ARXIV_CATEGORIES,
    required=True,
)
parser.add_argument(
    "--date",
    help="Date to search for papers within (in the format like 2024-01-01). Defaults to yesterday",
    type=lambda datestr: datetime.strptime(datestr, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ),
    default=(
        datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(days=2)
    ).replace(tzinfo=timezone.utc),  # defaults to 00:00 AM of the day before yesterday
    required=False,
)
parser.add_argument(
    "--data-dir",
    help="Path to a directory to store data in. Defaults to ./data",
    default=os.path.join(os.path.dirname(__file__), "data"),
    required=False,
)
parser.add_argument(
    "--max-papers",
    help="Max number of papers to search for. Defaults to 20",
    type=int,
    default=20,
    required=False,
)
parser.add_argument(
    "--summarizer-llm-name",
    help="Name of Ollama model who digests the paper into a summary.  Defaults to qwen3:8b",
    type=str,
    default="qwen3:8b",
    required=False,
)
parser.add_argument(
    "--summarizer-as-agent",
    help="Instantiate summarizer as a LLM agent equipped with tools.",
    action="store_true",
    required=False,
)
parser.add_argument(
    "--formatter-llm-name",
    help="Name of Ollama model who converts a sumamry into the predefined JSON format. Defaults to gemma3:4b",
    type=str,
    default="gemma3:4b",
    required=False,
)
parser.add_argument(
    "--ollama-api-base-url",
    help="URL to Ollama API. Defaults to http://127.0.0.1:11434",
    type=str,
    default="http://127.0.0.1:11434",
    required=False,
)
parser.add_argument(
    "--verbose",
    help="Enable verbose logging from this script.",
    action="store_true",
    required=False,
)

if __name__ == "__main__":
    args = parser.parse_args()

    # globally enable logging (to stdout)
    logging.basicConfig()

    # create logger for logs from this app
    logger = logging.getLogger("fetch_paper_info")
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    # instantiate LLMs
    summarizer, formatter = prepare_llms(
        summarizer_llm_name=args.summarizer_llm_name,
        formatter_llm_name=args.formatter_llm_name,
        ollama_api_base_url=args.ollama_api_base_url,
        summarizer_as_agent=args.summarizer_as_agent,
        debug=False,
    )

    # fetch papers from arXiv
    search_results = fetch_papers(
        category=args.category,
        date=args.date,
        max_papers=args.max_papers,
        logger=logger,
    )

    # extract necessary information from papers
    paperlist = process_results(
        search_results=search_results,
        date=args.date,
        summarizer=summarizer,
        formatter=formatter,
        data_dir=args.data_dir,
        logger=logger,
    )

    # write to json
    with open(
        os.path.join(args.data_dir, f"papers-{args.category}.json"), "w"
    ) as jsonfile:
        jsonfile.write(paperlist.model_dump_json())
