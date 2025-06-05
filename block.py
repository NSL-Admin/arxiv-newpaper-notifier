import textwrap
from typing import Optional

from slack_sdk.models.blocks import (
    ActionsBlock,
    Block,
    ButtonElement,
    DividerBlock,
    ImageBlock,
    MarkdownTextObject,
    PlainTextObject,
    SectionBlock,
    basic_components,
)

from const import Paper


def get_paper_block(paper: Paper, image_fileid: Optional[str]) -> list[Block]:
    blocks = [
        SectionBlock(text=MarkdownTextObject(text=f"*{paper.title}*")),
        DividerBlock(),
        SectionBlock(
            text=MarkdownTextObject(
                text=textwrap.dedent(
                    f"""\
                - *about:* {paper.gist.about}
                - *objective:* {paper.gist.objective}
                - *novelty:* {paper.gist.novelty}
                - *key:* {paper.gist.key}"""
                )
                + (
                    f"\n- *references:* {', '.join([f'<{u.url}|{u.text}>' for u in paper.gist.reference_urls])}"
                    if paper.gist.reference_urls
                    else ""
                )
            )
        ),
    ]
    if image_fileid:
        blocks += [
            ImageBlock(
                slack_file=basic_components.SlackFile(id=image_fileid),
                alt_text="the first figure of this paper",
            )
        ]
    blocks += [
        ActionsBlock(
            elements=[
                ButtonElement(
                    text=PlainTextObject(
                        text="View on arXiv :globe_with_meridians:",
                    ),
                    url=paper.url,
                )
            ]
        ),
    ]
    return blocks
