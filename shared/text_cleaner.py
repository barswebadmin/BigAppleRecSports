import re


class TextCleaner:
    """Utilities for cleaning and formatting text from webhook data"""
    
    @staticmethod
    def clean_title_formatting(text: str) -> str:
        """Clean up title formatting issues like double hyphens, stray parentheses, etc."""
        if not text:
            return ""
        
        # Remove double hyphens with optional spaces: -- or - - 
        text = re.sub(r'\s*-\s*-\s*', ' - ', text)
        # Remove stray opening/closing parentheses without pairs
        text = re.sub(r'\([^)]*$', '', text)
        text = re.sub(r'^[^(]*\)', '', text)
        # Clean up multiple spaces and hyphen sequences
        text = re.sub(r'\s+', ' ', text)
        text = text.strip(' -')
        text = re.sub(r'(\s*-\s*){2,}', ' - ', text)
        
        return text.strip()
