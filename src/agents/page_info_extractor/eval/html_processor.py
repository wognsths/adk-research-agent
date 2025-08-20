"""HTML preprocessing utilities for cleaning and extracting main content."""

from __future__ import annotations

import re
from typing import Optional

from selectolax.parser import HTMLParser


class HTMLProcessor:
    """Preprocesses HTML content by removing boilerplate and extracting main content."""
    
    # Tags to remove completely (including their content)
    REMOVE_TAGS = {
        'script', 'style', 'meta', 'link', 'title', 'head',
        'noscript', 'iframe', 'object', 'embed', 'applet',
        'canvas', 'svg', 'math', 'audio', 'video', 'source',
        'track', 'map', 'area'
    }
    
    # Tags commonly used for navigation, ads, and boilerplate
    BOILERPLATE_SELECTORS = [
        # Navigation
        'nav', '[role="navigation"]', '.nav', '.navigation', '.menu',
        '.breadcrumb', '.breadcrumbs', '.navbar', '.topbar', '.sidebar',
        
        # Headers and footers
        'header', 'footer', '.header', '.footer', '.site-header', 
        '.site-footer', '.page-header', '.page-footer',
        
        # Ads and social
        '.ad', '.ads', '.advertisement', '.banner', '.promo', '.promotion',
        '.social', '.share', '.sharing', '.social-media', '.social-links',
        
        # Comments and related
        '.comments', '.comment', '.discussion', '.replies',
        '.related', '.related-posts', '.related-articles', '.sidebar',
        
        # Common boilerplate classes/IDs
        '#sidebar', '#footer', '#header', '#nav', '#navigation',
        '.cookie-notice', '.cookie-banner', '.popup', '.modal',
        '.newsletter', '.subscription', '.signup', '.login'
    ]
    
    # Semantic content selectors (in order of preference)
    MAIN_CONTENT_SELECTORS = [
        'main',
        '[role="main"]',
        'article',
        '.main-content',
        '.content',
        '.post-content',
        '.article-content',
        '.entry-content',
        '#content',
        '#main-content',
        '#article',
        '#post',
        '.container .content',
        '.page-content'
    ]

    @classmethod
    def clean_html(cls, html_content: str) -> str:
        """
        Clean HTML content by removing boilerplate and extracting main content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned plain text content
        """
        if not html_content or not html_content.strip():
            return ""
        
        try:
            # Parse HTML
            tree = HTMLParser(html_content)
            
            # Remove unwanted tags completely
            for tag in cls.REMOVE_TAGS:
                for node in tree.css(tag):
                    node.decompose()
            
            # Remove boilerplate elements
            for selector in cls.BOILERPLATE_SELECTORS:
                for node in tree.css(selector):
                    node.decompose()
            
            # Try to extract main content using semantic selectors
            main_content = cls._extract_main_content(tree)
            
            if main_content:
                # Get text from main content
                text = main_content.text(separator=' ', strip=True)
            else:
                # Fallback: get all remaining text
                text = tree.text(separator=' ', strip=True)
            
            # Clean and normalize the text
            cleaned_text = cls._clean_text(text)
            
            return cleaned_text
            
        except Exception:
            # If parsing fails, return original content with basic cleaning
            return cls._clean_text(html_content)

    @classmethod
    def _extract_main_content(cls, tree: HTMLParser) -> Optional[HTMLParser]:
        """Extract the main content section from the parsed HTML tree."""
        
        # Try each selector in order of preference
        for selector in cls.MAIN_CONTENT_SELECTORS:
            nodes = tree.css(selector)
            if nodes:
                # Return the first matching node
                return nodes[0]
        
        # If no semantic selectors found, try to find the largest text block
        return cls._find_largest_content_block(tree)

    @classmethod
    def _find_largest_content_block(cls, tree: HTMLParser) -> Optional[HTMLParser]:
        """Find the HTML element with the most text content."""
        
        best_node = None
        max_text_length = 0
        
        # Check common content containers
        content_tags = ['div', 'section', 'article', 'main']
        
        for tag in content_tags:
            for node in tree.css(tag):
                text_length = len(node.text(strip=True))
                if text_length > max_text_length:
                    max_text_length = text_length
                    best_node = node
        
        # Only return if we found a substantial content block
        if max_text_length > 200:  # Minimum 200 characters
            return best_node
        
        return None

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean and normalize text content."""
        
        if not text:
            return ""
        
        # Remove HTML entities and tags if any remain
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{2,}', '--', text)
        
        # Clean up common artifacts
        text = re.sub(r'\s*[|]\s*', ' | ', text)
        text = re.sub(r'\s*[-]\s*', ' - ', text)
        
        # Remove leading/trailing whitespace and excessive line breaks
        text = text.strip()
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text