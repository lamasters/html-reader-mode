import unittest
from html_reader_mode import HTMLReaderMode


class TestHTMLReaderMode(unittest.TestCase):
    def setUp(self):
        self.reader_mode = HTMLReaderMode()

    def test_basic_extraction(self):
        html = """
        <html>
            <body>
                <div id="header">
                    <a href="/">Home</a> <a href="/about">About</a>
                </div>
                <div id="content">
                    <h1>Main Article Title</h1>
                    <p>This is the main content of the article. It has many words to ensure it is classified as content.
                    The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog.
                    The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog.</p>
                    <p>More content here. Very important information that we want to extract.</p>
                </div>
                <div id="sidebar">
                    <a href="/link1">Link 1</a>
                    <a href="/link2">Link 2</a>
                    <a href="/link3">Link 3</a>
                </div>
                <div id="footer">
                    <p>Copyright 2023. All rights reserved.</p>
                </div>
            </body>
        </html>
        """
        content = self.reader_mode.sanitize(html)

        self.assertTrue(
            any(
                "Main Article Title" in c["content"] and c["tag"] == "h1"
                for c in content
            )
        )
        self.assertTrue(
            any(
                "This is the main content" in c["content"] and c["tag"] == "p"
                for c in content
            )
        )

        self.assertFalse(any("Link 1" in c["content"] for c in content))

    def test_terminating_blocks(self):
        html = """
        <div>
            <p>This is content. It is long enough to be content. One two three four five six seven eight nine ten.</p>
            <p>Comments</p>
            <p>User 1: Great post!</p>
        </div>
        """
        content = self.reader_mode.sanitize(html)
        self.assertTrue(any("This is content" in c["content"] for c in content))
        self.assertFalse(any("Comments" in c["content"] for c in content))

    def test_empty_html(self):
        self.assertEqual(self.reader_mode.sanitize(""), [])
        self.assertEqual(self.reader_mode.sanitize(None), [])

    def test_no_body(self):
        reader = HTMLReaderMode(minimum_block_words=1)
        html = "<div><p>Content without body tag.</p></div>"
        content = reader.sanitize(html)
        self.assertTrue(
            any("Content without body tag" in c["content"] for c in content)
        )

    def test_custom_parameters_min_words(self):
        reader = HTMLReaderMode(minimum_block_words=20)
        html = """
        <body>
            <p>Short content 1. Not enough words.</p>
            <p>Short content 2. Also not enough.</p>
            <p>This paragraph has enough words to be considered content because we are going to make it very long indeed. One two three four five six seven eight nine ten.</p>
        </body>
        """
        content = reader.sanitize(html)
        self.assertFalse(any("Short content 1" in c["content"] for c in content))
        self.assertTrue(
            any("This paragraph has enough words" in c["content"] for c in content)
        )

    def test_custom_parameters_link_density(self):
        reader = HTMLReaderMode(maximum_block_link_density=0.8, minimum_block_words=1)
        html = """
        <body>
            <p><a href="l1">Link1</a> <a href="l2">Link2</a> <a href="l3">Link3</a> Text content here.</p>
        </body>
        """
        content = reader.sanitize(html)
        self.assertTrue(any("Text content here" in c["content"] for c in content))

    def test_custom_block_tags(self):
        reader = HTMLReaderMode(block_tags={"custom"}, minimum_block_words=1)
        html = """
        <body>
            <custom>This is a custom block tag content.</custom>
            <p>This is a p tag, which is no longer a block tag.</p>
        </body>
        """
        content = reader.sanitize(html)
        self.assertTrue(
            any("custom block tag content" in c["content"] for c in content)
        )

    def test_cutoff_logic(self):
        reader = HTMLReaderMode(
            minimum_cutoff_threshold=5,
            cutoff_keywords=["cutoff_here"],
            terminating_keywords=["cutoff_here"],
            minimum_block_words=2,
        )
        html = """
        <body>
            <p>Start of the article. Valid content. One two three four five six.</p>
            <p>cutoff_here</p>
            <p>This content should be cut off.</p>
        </body>
        """
        content = reader.sanitize(html)
        self.assertTrue(any("Start of the article" in c["content"] for c in content))
        self.assertFalse(
            any("This content should be cut off" in c["content"] for c in content)
        )

    def test_preceding_link_density(self):
        reader = HTMLReaderMode(
            maximum_preceding_block_link_density=0.1, minimum_block_words=16
        )
        html = """
        <body>
            <p><a href="l1">Link</a> <a href="l2">Link</a> <a href="l3">Link</a></p>
            <p>Short follow up.</p>
        </body>
        """
        content = reader.sanitize(html)
        self.assertFalse(any("Short follow up" in c["content"] for c in content))

    def test_nested_structure(self):
        reader = HTMLReaderMode(minimum_block_words=1)
        html = """
        <body>
            <div>
                <p>Nested content inside div.</p>
                <div>
                    <p>Deeply nested content.</p>
                </div>
            </div>
        </body>
        """
        content = reader.sanitize(html)
        self.assertTrue(
            any("Nested content inside div" in c["content"] for c in content)
        )
        self.assertTrue(any("Deeply nested content" in c["content"] for c in content))


if __name__ == "__main__":
    unittest.main()
