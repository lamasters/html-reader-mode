# HTML Reader Mode

A Python library to extract the main content from an HTML document, similar to the "Reader Mode" feature found in web browsers. It filters out navigation, ads, sidebars, and other non-content elements.

## Installation

```bash
pip install html-reader-mode
```

## Usage

```python
from html_reader_mode import HTMLReaderMode

html_content = """
<html>
    <body>
        <div id="header">Header content</div>
        <div id="content">
            <h1>Article Title</h1>
            <p>This is the main content of the article.</p>
        </div>
        <div id="footer">Footer content</div>
    </body>
</html>
"""

reader = HTMLReaderMode()
content = reader.sanitize(html_content)

print(content)
# Output:
# [{'tag': 'h1', 'content': 'Article Title'}, {'tag': 'p', 'content': 'This is the main content of the article.'}]
```

## Features

-   **Content Extraction**: Identifies and extracts the main text blocks.
-   **Noise Reduction**: Removes scripts, styles, and high-link-density blocks (like navigation menus).
-   **Customizable**: Configure block tags, script tags, and filtering thresholds.

## License

MIT
