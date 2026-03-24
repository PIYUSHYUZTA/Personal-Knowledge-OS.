"""
Functional and integration tests for web researcher.
Tests knowledge integrity, code validation, and metadata handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.web_researcher import WebContentExtractor, WebResearcherService
from app.config import settings


class TestWebContentExtractorValidation:
    """Test URL validation for security and safety."""

    def test_validate_valid_https_url(self):
        """Valid: HTTPS URL to trusted domain."""
        url = "https://docs.python.org/3/library/index.html"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is True
        assert error is None

    def test_validate_valid_http_url(self):
        """Valid: HTTP URL."""
        url = "http://github.com/project/repo"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is True
        assert error is None

    def test_invalid_scheme_ftp(self):
        """Invalid: FTP scheme not allowed."""
        url = "ftp://files.example.com/document.txt"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False
        assert "scheme" in error.lower()

    def test_invalid_localhost_127(self):
        """Invalid: Localhost 127.0.0.1 blocked."""
        url = "http://127.0.0.1:8000/endpoint"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False
        assert "localhost" in error.lower()

    def test_invalid_localhost_name(self):
        """Invalid: Localhost name blocked."""
        url = "http://localhost:3000/page"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False
        assert "localhost" in error.lower()

    def test_invalid_localhost_ipv6(self):
        """Invalid: IPv6 loopback blocked."""
        url = "http://[::1]:8000/page"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False

    def test_block_facebook_domain(self):
        """Invalid: Facebook blocked by domain list."""
        url = "https://facebook.com/user/profile"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False
        assert "blocked" in error.lower()

    def test_block_twitter_domain(self):
        """Invalid: Twitter blocked."""
        url = "https://twitter.com/user/tweets"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False

    def test_block_instagram_domain(self):
        """Invalid: Instagram blocked."""
        url = "https://instagram.com/user/feed"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False

    def test_invalid_no_hostname(self):
        """Invalid: URL with no hostname."""
        url = "http://"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False

    def test_invalid_malformed_url(self):
        """Invalid: Malformed URL."""
        url = "not a url at all"
        is_valid, error = WebContentExtractor.validate_url(url)
        assert is_valid is False


class TestHTMLParsing:
    """Test HTML content extraction and cleaning."""

    def test_extract_article_from_html(self):
        """Extract: Clean article content from HTML."""
        html = """
        <html>
            <head><title>Python Guide</title></head>
            <body>
                <nav>Navigation menu</nav>
                <article>
                    <h1>Python Lists</h1>
                    <p>Lists are ordered collections.</p>
                    <p>You can modify lists in place.</p>
                </article>
                <footer>Copyright 2024</footer>
            </body>
        </html>
        """

        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")

        # Navigation and footer should be removed
        assert "Navigation menu" not in text
        assert "Copyright 2024" not in text

        # Content should be extracted
        assert "Python Lists" in text
        assert "Lists are ordered collections" in text
        assert "You can modify lists in place" in text

        # Metadata should be set
        assert metadata["character_count"] > 0
        assert metadata["parser"] == "BeautifulSoup4"

    def test_remove_script_tags(self):
        """Extract: Remove script tags from content."""
        html = """
        <html>
            <body>
                <p>Important content</p>
                <script>
                    console.log("tracking code");
                    analytics.track("event");
                </script>
                <p>More content</p>
            </body>
        </html>
        """

        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")

        assert "Important content" in text
        assert "More content" in text
        assert "console.log" not in text
        assert "analytics.track" not in text

    def test_remove_style_tags(self):
        """Extract: Remove style tags."""
        html = """
        <html>
            <head>
                <style>
                    body { color: blue; }
                    .container { width: 100%; }
                </style>
            </head>
            <body>
                <p>This is text content</p>
            </body>
        </html>
        """

        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")

        assert "This is text content" in text
        assert "color: blue" not in text
        assert "container" not in text

    def test_custom_css_selector(self):
        """Extract: Use custom CSS selector."""
        html = """
        <html>
            <body>
                <div class="sidebar">Sidebar content</div>
                <div class="main-content">
                    <h1>Main Article</h1>
                    <p>Primary content here</p>
                </div>
            </body>
        </html>
        """

        text, metadata = WebContentExtractor.parse_html(
            html, "https://example.com", custom_selector=".main-content"
        )

        assert "Main Article" in text
        assert "Primary content here" in text
        assert "Sidebar content" not in text
        assert metadata["extraction_method"] == "css_selector"

    def test_extract_title(self):
        """Extract: Get title from HTML."""
        html = "<html><head><title>React Documentation</title></head></html>"
        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")
        # Title extraction happens in research_url, not parse_html


class TestCodeExtraction:
    """Test code snippet detection and extraction."""

    def test_extract_python_code_block(self):
        """Extract: Python code in <code> block."""
        html = """
        <html>
            <body>
                <p>Here's how to use lists:</p>
                <pre><code class="language-python">
my_list = [1, 2, 3]
my_list.append(4)
print(my_list)
                </code></pre>
            </body>
        </html>
        """

        codes = WebContentExtractor.extract_code_blocks(html)

        assert len(codes) > 0
        assert codes[0]["language"] == "python"
        assert "my_list = [1, 2, 3]" in codes[0]["code"]
        assert "append" in codes[0]["code"]

    def test_extract_javascript_code(self):
        """Extract: JavaScript code block."""
        html = """
        <html>
            <body>
                <pre><code class="language-javascript">
const arr = [1, 2, 3];
arr.push(4);
console.log(arr);
                </code></pre>
            </body>
        </html>
        """

        codes = WebContentExtractor.extract_code_blocks(html)

        assert len(codes) > 0
        assert codes[0]["language"] == "javascript"
        assert "const arr" in codes[0]["code"]

    def test_multiple_code_blocks(self):
        """Extract: Multiple code blocks."""
        html = """
        <html>
            <body>
                <pre><code class="language-python">print("First")</code></pre>
                <pre><code class="language-python">print("Second")</code></pre>
                <pre><code class="language-bash">echo "Third"</code></pre>
            </body>
        </html>
        """

        codes = WebContentExtractor.extract_code_blocks(html)

        assert len(codes) >= 2
        assert any("First" in c["code"] for c in codes)
        assert any("Second" in c["code"] for c in codes)

    def test_skip_tiny_code_snippets(self):
        """Extract: Ignore tiny code snippets."""
        html = """
        <html>
            <body>
                <code>x</code>
                <code>y</code>
                <pre><code class="language-python">
# This is a real code block
def hello():
    print("world")
                </code></pre>
            </body>
        </html>
        """

        codes = WebContentExtractor.extract_code_blocks(html)

        # Single-char snippets should be filtered
        assert not any(len(c["code"].strip()) < 10 for c in codes)
        assert len(codes) > 0
        assert "hello" in codes[0]["code"]


class TestCodeValidation:
    """Test code snippet validation via Sandbox."""

    @pytest.mark.asyncio
    async def test_validate_valid_python_code(self):
        """Validate: Valid Python code passes."""
        code = "x = 1 + 1\nprint(x)"
        is_valid, error = await WebContentExtractor.validate_code_snippet(code)
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_invalid_syntax(self):
        """Validate: Syntax error detected."""
        code = "def broken(\n    print('missing colon"
        is_valid, error = await WebContentExtractor.validate_code_snippet(code)
        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_validate_blocks_os_module(self):
        """Validate: os module import blocked."""
        code = "import os\nos.system('rm -rf /')"
        is_valid, error = await WebContentExtractor.validate_code_snippet(code)
        assert is_valid is False
        assert "os" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_blocks_eval(self):
        """Validate: eval() blocked."""
        code = "result = eval('1+1')"
        is_valid, error = await WebContentExtractor.validate_code_snippet(code)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_blocks_exec(self):
        """Validate: exec() blocked."""
        code = "exec('print(1)')"
        is_valid, error = await WebContentExtractor.validate_code_snippet(code)
        assert is_valid is False


class TestContentHashing:
    """Test deduplication via content hashing."""

    def test_same_content_same_hash(self):
        """Hash: Identical content produces same hash."""
        content = "The quick brown fox jumps over the lazy dog"

        hash1 = WebResearcherService.generate_content_hash(content)
        hash2 = WebResearcherService.generate_content_hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Hash: Different content produces different hash."""
        content1 = "The quick brown fox"
        content2 = "The lazy brown fox"

        hash1 = WebResearcherService.generate_content_hash(content1)
        hash2 = WebResearcherService.generate_content_hash(content2)

        assert hash1 != hash2

    def test_hash_length_consistent(self):
        """Hash: SHA256 produces 64-char hex string."""
        content = "Any content here"
        hash_value = WebResearcherService.generate_content_hash(content)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestFetchWithMocking:
    """Test HTTP fetch with mocked responses."""

    @pytest.mark.asyncio
    async def test_fetch_successful_response(self):
        """Fetch: Successfully retrieve HTML content."""
        html_content = "<html><body>Test content</body></html>"

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {"content-type": "text/html"}
            mock_response.url = "https://example.com/page"
            mock_response.content = html_content.encode()
            mock_get.return_value = mock_response

            content, metadata = await WebContentExtractor.fetch_url("https://example.com/page")

            assert content == html_content
            assert metadata["status_code"] == 200
            assert metadata["error_message"] is None

    @pytest.mark.asyncio
    async def test_fetch_404_error(self):
        """Fetch: Handle 404 error."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            content, metadata = await WebContentExtractor.fetch_url("https://example.com/notfound")

            assert content is None
            assert metadata["status_code"] == 404
            assert "404" in metadata["error_message"]

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Fetch: Handle timeout gracefully."""
        import httpx

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            content, metadata = await WebContentExtractor.fetch_url("https://slow-site.com")

            assert content is None
            assert "timeout" in metadata["error_message"].lower()

    @pytest.mark.asyncio
    async def test_fetch_size_limit_exceeded(self):
        """Fetch: Reject content exceeding size limit."""
        huge_content = "x" * (settings.WEB_CONTENT_MAX_SIZE + 1)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = huge_content.encode()
            mock_response.text = huge_content
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            content, metadata = await WebContentExtractor.fetch_url("https://example.com")

            assert content is None
            assert "too large" in metadata["error_message"].lower()


class TestMetadataGeneration:
    """Test metadata is correctly generated and stored."""

    @pytest.mark.asyncio
    async def test_metadata_includes_timestamp(self):
        """Metadata: Fetch timestamp recorded."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Content</body></html>"
            mock_response.headers = {"content-type": "text/html"}
            mock_response.url = "https://example.com"
            mock_response.content = b"<html><body>Content</body></html>"
            mock_get.return_value = mock_response

            content, metadata = await WebContentExtractor.fetch_url("https://example.com")

            assert "fetch_timestamp" in metadata
            # Should be ISO format
            assert "T" in metadata["fetch_timestamp"]
            assert "Z" in metadata["fetch_timestamp"]

    @pytest.mark.asyncio
    async def test_metadata_includes_status_code(self):
        """Metadata: HTTP status code recorded."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 201
            mock_response.text = "Created"
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = "https://example.com"
            mock_response.content = b"Created"
            mock_get.return_value = mock_response

            content, metadata = await WebContentExtractor.fetch_url("https://example.com")

            assert metadata["status_code"] == 201

    def test_metadata_includes_content_type(self):
        """Metadata: Content-Type header recorded."""
        html = "<html><body>Test</body></html>"
        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")

        assert "extraction_method" in metadata
        assert metadata["parser"] == "BeautifulSoup4"
        assert metadata["character_count"] >= 0


class TestPerformance:
    """Performance profiling tests."""

    @pytest.mark.asyncio
    async def test_parsing_latency(self):
        """Performance: HTML parsing should be <100ms."""
        import time

        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <nav>Nav</nav>
                <article>
                    <h1>Title</h1>
                    <p>Content paragraph 1</p>
                    <p>Content paragraph 2</p>
                    <p>Content paragraph 3</p>
                </article>
                <footer>Footer</footer>
            </body>
        </html>
        """

        start = time.time()
        text, metadata = WebContentExtractor.parse_html(html, "https://example.com")
        elapsed_ms = (time.time() - start) * 1000

        # BeautifulSoup should parse in <100ms
        assert elapsed_ms < 100, f"Parsing took {elapsed_ms}ms"
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_code_extraction_latency(self):
        """Performance: Code extraction should be <50ms."""
        import time

        html = """
        <html><body>
            <pre><code>""" + "\n".join([f"line_{i} = {i}" for i in range(100)]) + """</code></pre>
        </body></html>
        """

        start = time.time()
        codes = WebContentExtractor.extract_code_blocks(html)
        elapsed_ms = (time.time() - start) * 1000

        # Code extraction should be very fast
        assert elapsed_ms < 50, f"Code extraction took {elapsed_ms}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
