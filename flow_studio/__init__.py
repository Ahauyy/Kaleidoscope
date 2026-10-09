"""
Kaleidoscope: Universal Google Flow Automation & Generative Batch Studio
------------------------------------------------------------------------
High-performance Playwright-driven batch synthesis framework for Google Flow
and modern generative web canvas platforms.
"""

__version__ = "2.0.0"
__author__ = "Axell Satria Elarie"
__license__ = "MIT"

from flow_studio.browser import FlowBrowserManager
from flow_studio.canvas import FlowCanvasController
from flow_studio.downloader import FlowImageDownloader
from flow_studio.prompts import PromptTemplateEngine
from flow_studio.ledger import JobLedger

__all__ = [
    "FlowBrowserManager",
    "FlowCanvasController",
    "FlowImageDownloader",
    "PromptTemplateEngine",
    "JobLedger",
]
