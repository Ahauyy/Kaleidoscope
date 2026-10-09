import os
import re
import itertools
from typing import Dict, Any, List, Optional

class PromptTemplateEngine:
    """
    Dynamic Prompt Engineering & Matrix Generator for Generative Synthesis.
    Supports variable interpolation ({{var}} / {var}) and Cartesian prompt matrices.
    """

    def __init__(self, template: str, default_variables: Optional[Dict[str, Any]] = None):
        self.template = template
        self.default_variables = default_variables or {}

    @classmethod
    def from_file(cls, filepath: str, default_variables: Optional[Dict[str, Any]] = None):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt template file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return cls(content.strip(), default_variables)

    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Renders template substituting tokens like {{key}} or {key}.
        """
        context = {**self.default_variables, **(variables or {})}
        rendered = self.template

        # 1. Substitute {{var}}
        for key, value in context.items():
            pattern = re.compile(r'\{\{\s*' + re.escape(str(key)) + r'\s*\}\}', re.IGNORECASE)
            rendered = pattern.sub(str(value), rendered)

        # 2. Substitute {var} if not double-bracketed
        for key, value in context.items():
            pattern = re.compile(r'(?<!\{)\{' + re.escape(str(key)) + r'\}(?!\})', re.IGNORECASE)
            rendered = pattern.sub(str(value), rendered)

        # Clean multiple spaces and whitespace
        rendered = re.sub(r'[ \t]+', ' ', rendered).strip()
        return rendered

    @staticmethod
    def generate_matrix(template_str: str, matrix_axes: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generates a combinatorial matrix of rendered prompts and their variable maps.
        Example matrix_axes:
            {"style": ["cinematic", "vintage"], "lighting": ["golden hour", "studio"]}
        Returns list of dicts: [{"prompt": "...", "variables": {...}}, ...]
        """
        keys = list(matrix_axes.keys())
        value_lists = [matrix_axes[k] for k in keys]

        results = []
        engine = PromptTemplateEngine(template_str)

        for combo in itertools.product(*value_lists):
            var_map = dict(zip(keys, combo))
            rendered = engine.render(var_map)
            results.append({
                "prompt": rendered,
                "variables": var_map
            })

        return results
