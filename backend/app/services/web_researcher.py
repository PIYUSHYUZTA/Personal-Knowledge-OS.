"""
Web researcher service for autonomous knowledge acquisition.
Fetches URLs, extracts content, validates code, and prepares for ingestion.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models import WebContent, VerificationStatus
from app.core.sandbox import SandboxExecution

logger = logging.getLogger(__name__)


class WebContentExtractor:
    """Extracts content from HTML with security checks."""

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL against security rules.

        Returns: (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid scheme: {parsed.scheme}. Only http/https allowed."

            # Check hostname
            if not parsed.hostname:
                return False, "No hostname in URL"

            # Block localhost
            if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                return False, "Localhost URLs not allowed for security"

            # Check domain whitelist/blacklist
            domain = parsed.hostname.lower()

            # Block list check first (blocks take priority)
            for blocked_domain in settings.WEB_BLOCKED_DOMAINS:
                if domain.endswith(blocked_domain):
                    return False, f"Domain blocked: {blocked_domain}"

            # Whitelist check (if enabled)
            if settings.WEB_TRUSTED_DOMAINS:
                is_trusted = any(domain.endswith(trusted) for trusted in settings.WEB_TRUSTED_DOMAINS)
                if not is_trusted:
                    logger.warning(f"URL domain not in trusted list: {domain}")
                    # For now, allow but log warning - can be strict in production

            return True, None

        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    @staticmethod
    async def fetch_url(url: str) -> Tuple[Optional[str], Dict[str, any]]:
        """
        Fetch URL content with timeout and error handling.

        Returns: (html_content, metadata)
        """
        metadata = {
            "fetch_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status_code": None,
            "content_type": None,
            "final_url": url,
            "error_message": None,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.WEB_CONTENT_TIMEOUT) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": settings.WEB_CONTENT_USER_AGENT},
                    follow_redirects=True,
                )

                metadata["status_code"] = response.status_code
                metadata["final_url"] = str(response.url)
                metadata["content_type"] = response.headers.get("content-type", "text/html")

                # Check for success
                if response.status_code != 200:
                    metadata["error_message"] = f"HTTP {response.status_code}"
                    return None, metadata

                # Check content size
                content_size = len(response.content)
                if content_size > settings.WEB_CONTENT_MAX_SIZE:
                    metadata["error_message"] = f"Content too large: {content_size} bytes"
                    return None, metadata

                return response.text, metadata

        except httpx.TimeoutException:
            metadata["error_message"] = f"Timeout after {settings.WEB_CONTENT_TIMEOUT}s"
            return None, metadata
        except httpx.ConnectError as e:
            metadata["error_message"] = f"Connection failed: {str(e)}"
            return None, metadata
        except httpx.HTTPError as e:
            metadata["error_message"] = f"HTTP error: {str(e)}"
            return None, metadata
        except Exception as e:
            metadata["error_message"] = f"Fetch error: {str(e)}"
            logger.error(f"Web fetch failed for {url}: {str(e)}", exc_info=True)
            return None, metadata

    @staticmethod
    def parse_html(html: str, url: str, custom_selector: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Parse HTML and extract main content.

        Returns: (text_content, extraction_metadata)
        """
        metadata = {
            "parser": "BeautifulSoup4",
            "extraction_method": "heuristic",
            "selector_used": custom_selector,
            "character_count": 0,
            "language": "en",
            "encoding": "utf-8",
        }

        try:
            soup = BeautifulSoup(html, "lxml")

            # If custom selector provided, use it
            if custom_selector:
                try:
                    element = soup.select_one(custom_selector)
                    if element:
                        metadata["extraction_method"] = "css_selector"
                        text = element.get_text(separator="\n", strip=True)
                        metadata["character_count"] = len(text)
                        return text, metadata
                except Exception as e:
                    logger.warning(f"Custom selector failed: {str(e)}")

            # Default extraction: Remove script, style, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # Try common article containers
            article_selectors = [
                "article",
                ".article-content",
                ".post-content",
                ".entry-content",
                "main",
                ".main-content",
            ]

            content = None
            for selector in article_selectors:
                element = soup.select_one(selector)
                if element:
                    metadata["extraction_method"] = f"selector_{selector}"
                    metadata["selector_used"] = selector
                    content = element.get_text(separator="\n", strip=True)
                    break

            # Fallback: body text
            if not content:
                body = soup.find("body")
                if body:
                    content = body.get_text(separator="\n", strip=True)
                else:
                    content = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            text = "\n".join(lines)

            # Extract charset if available
            charset_meta = soup.find("meta", {"charset": True})
            if charset_meta:
                metadata["encoding"] = charset_meta.get("charset", "utf-8")

            metadata["character_count"] = len(text)
            return text, metadata

        except Exception as e:
            logger.error(f"HTML parsing failed: {str(e)}", exc_info=True)
            metadata["error_message"] = str(e)
            return "", metadata

    @staticmethod
    def extract_code_blocks(html: str) -> List[Dict[str, str]]:
        """
        Extract code snippets from HTML.

        Returns: List of {language, code, line_number}
        """
        codes = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find <code> and <pre> blocks with language hints
            code_blocks = soup.find_all(["code", "pre"])

            for idx, block in enumerate(code_blocks):
                if block.name == "pre" and block.find("code"):
                    continue
                # Try to detect language
                language = "plaintext"
                class_attr = block.get("class", [])
                if isinstance(class_attr, list):
                    class_str = " ".join(class_attr)
                else:
                    class_str = class_attr

                # Common class patterns: language-python, lang-py, hljs-python, etc.
                for match in re.findall(r"language-(\w+)|lang-(\w+)|hljs-(\w+)", class_str):
                    detected = next((m for m in match if m), None)
                    if detected:
                        language = detected
                        break

                code_text = block.get_text().strip()

                if code_text and len(code_text) > 10:  # Meaningful code snippet
                    codes.append({
                        "language": language,
                        "code": code_text,
                        "index": idx,
                    })

        except Exception as e:
            logger.warning(f"Code extraction failed: {str(e)}")

        return codes

    @staticmethod
    async def validate_code_snippet(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate code snippet using Phase 6a Sandbox.

        Returns: (is_valid, error_message)
        """
        # Only validate Python for now
        is_valid, error = SandboxExecution.validate_code(
            code=code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES,
        )
        return is_valid, error


class WebResearcherService:
    """High-level research service orchestrating fetching, parsing, and validation."""

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate SHA256 hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    async def research_url(
        url: str,
        user_id: UUID,
        extract_code: bool = True,
        validate_code: bool = True,
        custom_selector: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict:
        """
        Complete research workflow for a single URL.

        Returns: {
            "success": bool,
            "url": str,
            "title": str,
            "domain": str,
            "content": str,
            "content_hash": str,
            "codes_found": int,
            "codes_validated": int,
            "codes": [...],
            "metadata": {...},
            "error": Optional[str],
            "web_content_id": Optional[UUID],
        }
        """
        result = {
            "success": False,
            "url": url,
            "title": None,
            "domain": None,
            "content": "",
            "content_hash": None,
            "codes_found": 0,
            "codes_validated": 0,
            "codes": [],
            "metadata": {},
            "error": None,
            "web_content_id": None,
        }

        # Step 1: Validate URL
        is_valid_url, url_error = WebContentExtractor.validate_url(url)
        if not is_valid_url:
            result["error"] = url_error
            logger.warning(f"Invalid URL {url}: {url_error}")
            return result

        result["domain"] = urlparse(url).hostname

        # Step 2: Fetch URL
        html, fetch_metadata = await WebContentExtractor.fetch_url(url)
        result["metadata"].update(fetch_metadata)

        if html is None:
            result["error"] = fetch_metadata.get("error_message", "Failed to fetch URL")
            logger.warning(f"Failed to fetch {url}: {result['error']}")
            return result

        # Step 3: Parse content
        content, parse_metadata = WebContentExtractor.parse_html(html, url, custom_selector)
        result["metadata"].update(parse_metadata)
        result["content"] = content

        if not content:
            result["error"] = "No content extracted"
            logger.warning(f"No content extracted from {url}")
            return result

        # Step 4: Extract code blocks
        codes = []
        if extract_code:
            codes = WebContentExtractor.extract_code_blocks(html)
            result["codes_found"] = len(codes)

        # Step 5: Validate codes
        validated_codes = []
        if validate_code and codes:
            for code_block in codes:
                is_valid, error = await WebContentExtractor.validate_code_snippet(
                    code_block["code"]
                )
                if is_valid:
                    code_block["valid"] = True
                    validated_codes.append(code_block)
                    result["codes_validated"] += 1
                else:
                    code_block["valid"] = False
                    code_block["error"] = error

            result["codes"] = validated_codes + [c for c in codes if not c.get("valid", False)]

        # Step 6: Calculate hash and create WebContent record
        content_hash = WebResearcherService.generate_content_hash(content)
        result["content_hash"] = content_hash

        # Extract title from HTML
        try:
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            if title_tag:
                result["title"] = title_tag.get_text().strip()
        except Exception:
            pass

        # Step 7: Create database record (if session provided)
        if db:
            try:
                # Separate verified and unverified codes
                verified_codes = [c for c in result["codes"] if c.get("valid", False)]
                unverified_codes = [c for c in result["codes"] if not c.get("valid", False)]

                # Determine verification status
                verification_status = VerificationStatus.VERIFIED
                if unverified_codes and not verified_codes:
                    verification_status = VerificationStatus.FAILED
                elif unverified_codes:
                    verification_status = VerificationStatus.UNVERIFIED

                web_content = WebContent(
                    user_id=user_id,
                    source_url=url,
                    content_hash=content_hash,
                    title=result["title"],
                    domain=result["domain"],
                    # Phase 7a: Store content and codes
                    content_text=result["content"],
                    code_blocks_json=verified_codes,  # Store verified codes for ingestion
                    verification_status=verification_status,
                    unverified_codes=unverified_codes,  # Store failed codes for review
                    metadata_=result["metadata"],
                )
                db.add(web_content)
                db.commit()
                result["web_content_id"] = web_content.id
                logger.info(f"Created WebContent record for {url}")
            except Exception as e:
                logger.error(f"Failed to create WebContent record: {str(e)}")

        result["success"] = True
        logger.info(f"Successfully researched {url}: {result['codes_found']} codes found, {result['codes_validated']} validated")
        return result

    @staticmethod
    async def batch_research(
        urls: List[str],
        user_id: UUID,
        extract_code: bool = True,
        validate_code: bool = True,
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """Research multiple URLs in parallel."""
        # For now, sequential (can optimize with asyncio.gather)
        results = []
        for url in urls:
            result = await WebResearcherService.research_url(
                url=url,
                user_id=user_id,
                extract_code=extract_code,
                validate_code=validate_code,
                db=db,
            )
            results.append(result)

        return results
