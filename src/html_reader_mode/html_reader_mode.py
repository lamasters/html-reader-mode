import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag, PageElement, Comment


class TextBlock:
    def __init__(
        self,
        text_builder: list[str],
        num_words: int,
        num_linked_words: int,
        tag_level: int,
        tag_name: str = "p",
    ):
        self.text: str = "".join(text_builder).strip()
        self.num_words: int = num_words
        self.num_linked_words: int = num_linked_words
        self.link_density: float = (
            num_linked_words / num_words if num_words > 0 else 0.0
        )
        self.tag_level: int = tag_level
        self.tag_name: str = tag_name
        self.is_content: bool = False
        self.to_be_excluded: bool = False


class HTMLReaderMode:
    DEFAULT_BLOCK_TAGS: set[str] = {
        "div",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "header",
        "footer",
        "section",
        "article",
        "aside",
    }
    DEFAULT_SCRIPT_TAGS: set[str] = {"script", "style", "noscript", "iframe", "svg"}
    DEFAULT_TERMINATING_KEYWORDS: list[str] = [
        "comments",
        "share this",
        "related articles",
        "subscribe",
        "topics",
        "newsletter",
        "related",
        "read more",
        "about the author",
        "no newsletters selected",
    ]
    DEFAULT_CUTOFF_KEYWORDS: list[str] = [
        "comments",
        "related articles",
        "topics",
        "newsletter",
        "related",
        "about the author",
    ]

    def __init__(
        self,
        minimum_cutoff_threshold: int = 100,
        minimum_block_words: int = 16,
        maximum_preceding_block_link_density: float = 0.5,
        maximum_block_link_density: float = 0.33,
        block_tags: Optional[set[str]] = None,
        script_tags: Optional[set[str]] = None,
        terminating_keywords: Optional[list[str]] = None,
        cutoff_keywords: Optional[list[str]] = None,
    ):
        """Initialize the HTMLReaderMode with the given parameters

        Args:
            minimum_cutoff_threshold (int): Minimum number of words to trigger cutoff regex matching
            minimum_block_words (int): Minimum number of words in a content block
            maximum_preceding_block_link_density (float): Maximum link density of the preceding block
            maximum_block_link_density (float): Maximum link density of the block
            block_tags (Optional[set[str]]): set of block HTML tags
            script_tags (Optional[set[str]]): set of script HTML tags
            terminating_keywords (Optional[list[str]]): list of terminating keywords
            cutoff_keywords (Optional[list[str]]): list of cutoff keywords
        """
        self.minimum_cutoff_threshold = minimum_cutoff_threshold
        self.minimum_block_words = minimum_block_words
        self.maximum_preceding_block_link_density = maximum_preceding_block_link_density
        self.maximum_block_link_density = maximum_block_link_density
        self.block_tags = (
            block_tags if block_tags is not None else self.DEFAULT_BLOCK_TAGS
        )
        self.script_tags = (
            script_tags if script_tags is not None else self.DEFAULT_SCRIPT_TAGS
        )
        self.terminating_keywords = (
            terminating_keywords
            if terminating_keywords is not None
            else self.DEFAULT_TERMINATING_KEYWORDS
        )
        self.cutoff_keywords = (
            cutoff_keywords
            if cutoff_keywords is not None
            else self.DEFAULT_CUTOFF_KEYWORDS
        )

    def sanitize(self, html: str) -> list[dict[str, str]]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        for script in soup(self.script_tags):
            script.decompose()

        root = soup.body if soup.body else soup
        blocks: list[TextBlock] = self._linearize_dom(root)
        self._classify_blocks(blocks)

        return [{"tag": b.tag_name, "content": b.text} for b in blocks if b.is_content]

    def _linearize_dom(self, root: PageElement) -> list[TextBlock]:
        blocks: list[TextBlock] = []

        current_text: list[str] = []
        current_num_words: int = 0
        current_num_linked_words: int = 0

        def flush_block(tag_level: int, tag_name: str) -> None:
            nonlocal current_text, current_num_words, current_num_linked_words
            if current_text:
                text_content = "".join(current_text).strip()
                if text_content:
                    blocks.append(
                        TextBlock(
                            current_text,
                            current_num_words,
                            current_num_linked_words,
                            tag_level,
                            tag_name,
                        )
                    )
            current_text = []
            current_num_words = 0
            current_num_linked_words = 0

        def count_words(text: str) -> int:
            return len(text.split())

        def traverse(
            node: PageElement, depth: int, in_link: bool, container_tag: str
        ) -> None:
            nonlocal current_num_words, current_num_linked_words

            if isinstance(node, Comment):
                return

            if isinstance(node, NavigableString):
                text = str(node)
                if not text.strip():
                    return
                current_text.append(text)
                words = count_words(text)
                current_num_words += words
                if in_link:
                    current_num_linked_words += words
            elif isinstance(node, Tag):
                is_block = node.name in self.block_tags
                is_link = node.name == "a"

                next_container_tag = node.name if is_block else container_tag

                if is_block:
                    flush_block(depth, container_tag)

                for child in node.children:
                    traverse(child, depth + 1, in_link or is_link, next_container_tag)

                if is_block:
                    flush_block(depth, next_container_tag)

        traverse(root, 0, False, "p")
        flush_block(0, "p")
        return blocks

    def _classify_blocks(self, blocks: list[TextBlock]) -> None:
        if not blocks:
            return
        terminating_pattern = f"^({'|'.join(self.terminating_keywords)})$"
        cutoff_pattern = f"^({'|'.join(self.cutoff_keywords)})$"
        terminating_regex = re.compile(terminating_pattern, re.IGNORECASE)
        cutoff_regex = re.compile(cutoff_pattern, re.IGNORECASE)

        cutoff = False
        content_words_so_far = 0

        for i in range(len(blocks)):
            prev_block: Optional[TextBlock] = blocks[i - 1] if i > 0 else None
            current_block: TextBlock = blocks[i]
            next_block: Optional[TextBlock] = (
                blocks[i + 1] if i < len(blocks) - 1 else None
            )

            if cutoff:
                current_block.to_be_excluded = True
                continue

            if (
                terminating_regex.search(current_block.text)
                and current_block.num_words < self.minimum_block_words
            ):
                current_block.to_be_excluded = True
                if (
                    cutoff_regex.search(current_block.text)
                    and content_words_so_far > self.minimum_cutoff_threshold
                ):
                    cutoff = True
                    current_block.is_content = False
                    continue

            if current_block.to_be_excluded:
                current_block.is_content = False
                continue

            is_content = False
            if current_block.link_density <= self.maximum_block_link_density:
                if (
                    prev_block is None
                    or prev_block.link_density
                    <= self.maximum_preceding_block_link_density
                ):
                    if current_block.num_words <= self.minimum_block_words:
                        if (
                            next_block is None
                            or next_block.num_words <= self.minimum_block_words
                        ):
                            if (
                                prev_block is None
                                or prev_block.num_words <= self.minimum_block_words
                            ):
                                is_content = False
                            else:
                                is_content = True
                        else:
                            is_content = True
                    else:
                        is_content = True
                else:
                    if current_block.num_words <= self.minimum_block_words:
                        if (
                            next_block is None
                            or next_block.num_words <= self.minimum_block_words
                        ):
                            is_content = False
                        else:
                            is_content = True
                    else:
                        is_content = True
            else:
                is_content = False

            current_block.is_content = is_content
            if is_content:
                content_words_so_far += current_block.num_words
