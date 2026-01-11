#!/usr/bin/env python3
"""
Abstract base class for remote code fetchers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class RemoteFetcher(ABC):
    """Abstract base class for fetching remote code."""
    
    @abstractmethod
    def fetch(self, identifier: str, temp_dir: Path) -> Path:
        """
        Fetch remote code to a temporary directory.
        
        Args:
            identifier: Project/function identifier (e.g., function name, project name)
            temp_dir: Temporary directory to store fetched code
        
        Returns:
            Path to directory containing fetched code
        """
        pass
    
    @abstractmethod
    def check_credentials(self) -> bool:
        """
        Check if credentials are configured.
        
        Returns:
            True if credentials are available
        """
        pass
