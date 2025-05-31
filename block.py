from typing import Optional

from slack_sdk.models.blocks import (
    ActionsBlock,
    Block,
    ButtonElement,
    DividerBlock,
    ImageBlock,
    MarkdownTextObject,
    PlainTextObject,
    RichTextBlock,
    RichTextElementParts,
    RichTextListElement,
    RichTextSectionElement,
    SectionBlock,
    basic_components,
)

from const import Paper


def get_paper_block(paper: Paper, image_fileid: Optional[str]) -> list[Block]:
    blocks = [
        SectionBlock(text=MarkdownTextObject(text=f"*{paper.title}*")),
        DividerBlock(),
        RichTextBlock(
            elements=[
                RichTextListElement(
                    style="bullet",
                    elements=[
                        RichTextSectionElement(
                            elements=[
                                RichTextElementParts.Text(
                                    text="about: ",
                                    style=RichTextElementParts.TextStyle(bold=True),
                                ),
                                RichTextElementParts.Text(
                                    text=paper.gist.about,
                                ),
                            ]
                        ),
                        RichTextSectionElement(
                            elements=[
                                RichTextElementParts.Text(
                                    text="objective: ",
                                    style=RichTextElementParts.TextStyle(bold=True),
                                ),
                                RichTextElementParts.Text(
                                    text=paper.gist.objective,
                                ),
                            ]
                        ),
                        RichTextSectionElement(
                            elements=[
                                RichTextElementParts.Text(
                                    text="novelty: ",
                                    style=RichTextElementParts.TextStyle(bold=True),
                                ),
                                RichTextElementParts.Text(
                                    text=paper.gist.novelty,
                                ),
                            ]
                        ),
                        RichTextSectionElement(
                            elements=[
                                RichTextElementParts.Text(
                                    text="key: ",
                                    style=RichTextElementParts.TextStyle(bold=True),
                                ),
                                RichTextElementParts.Text(
                                    text=paper.gist.key,
                                ),
                            ]
                        ),
                    ]
                    + (
                        [
                            RichTextSectionElement(
                                elements=[
                                    RichTextElementParts.Text(
                                        text="references: ",
                                        style=RichTextElementParts.TextStyle(bold=True),
                                    ),
                                    RichTextElementParts.Text(
                                        text=", ".join(
                                            [
                                                f"<{u.url}|{u.text}>"
                                                for u in paper.gist.reference_urls
                                            ]
                                        ),
                                    ),
                                ]
                            ),
                        ]
                        if paper.gist.reference_urls
                        else []  # omit references section if no reference url is provided
                    ),
                ),
            ]
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
                        text="view on arXiv :globe_with_meridians:",
                    ),
                    url=paper.url,
                )
            ]
        ),
    ]
    return blocks
