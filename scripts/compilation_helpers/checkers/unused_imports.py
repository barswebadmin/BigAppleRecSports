"""Unused import detection using AST analysis."""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

from scripts.compilation_helpers.repo_path_resolvers import get_relative_path
from scripts.compilation_helpers.checkers._checkers_common import create_error, parse_file_ast


class ImportCollector(ast.NodeVisitor):
    """Collect all imports from an AST with their aliases and line numbers."""
    
    def __init__(self):
        self.imports_map: Dict[str, tuple[str, int, str]] = {}
    
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name
            asname = alias.asname if alias.asname else name.split(".")[0]
            self.imports_map[asname] = (name, node.lineno, "import")
    
    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            name = f"{module}.{alias.name}" if module else alias.name
            asname = alias.asname if alias.asname else alias.name
            self.imports_map[asname] = (name, node.lineno, "from")


class NameCollector(ast.NodeVisitor):
    """Collect all names used in an AST (for detecting unused imports)."""
    
    def __init__(self):
        self.used_names: Set[str] = set()
        self.__all__: Set[str] = set()
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and isinstance(node.value.ctx, ast.Load):
            self.used_names.add(node.value.id)
        elif isinstance(node.value, ast.Attribute):
            self.visit(node.value)
        self.generic_visit(node)
    
    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name) and isinstance(node.value.ctx, ast.Load):
            self.used_names.add(node.value.id)
        self.generic_visit(node)
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and isinstance(node.func.ctx, ast.Load):
            self.used_names.add(node.func.id)
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Capture __all__ assignments to track re-exported names."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            self.__all__.add(elt.value)
                        elif isinstance(elt, ast.Str):
                            self.__all__.add(elt.s)
        self.generic_visit(node)


def _has_exception_comment(file_path: Path, line_num: int) -> bool:
    """Check if an import line has a comment indicating it should be ignored."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            return False
        
        import_line = lines[line_num - 1].rstrip()
        if '#' in import_line:
            comment_part = import_line.split('#', 1)[1].strip().lower()
            if any(keyword in comment_part for keyword in ['noqa', 'validated necessary', 'needed', 'required']):
                return True
        
        if line_num < len(lines):
            next_line = lines[line_num].strip()
            if next_line.startswith('#') and any(keyword in next_line.lower() for keyword in ['noqa', 'validated necessary', 'needed', 'required']):
                return True
        
        return False
    except Exception:
        return False


def _is_import_used(alias_name: str, full_name: str, import_type: str, used_names: Set[str], __all__: Set[str], file_path: Optional[Path] = None, line_num: Optional[int] = None) -> bool:
    """Check if an import is actually used in the code."""
    if file_path and line_num and _has_exception_comment(file_path, line_num):
        return True
    
    if alias_name in used_names or alias_name in __all__:
        return True
    
    if import_type == "from":
        module_parts = full_name.split(".")
        if len(module_parts) > 1 and module_parts[0] in used_names:
            return True
    
    if alias_name == "__all__" or (alias_name.startswith("_") and not alias_name.startswith("__")):
        return True
    
    return False


def _format_import_statement(full_name: str, alias_name: str, import_type: str) -> str:
    """Format an import statement for display."""
    if import_type == "import":
        import_stmt = f"import {full_name}"
        base_name = full_name.split(".")[0]
        if alias_name != base_name:
            import_stmt += f" as {alias_name}"
        return import_stmt
    
    module_part = full_name.rsplit(".", 1)[0] if "." in full_name else ""
    name_part = full_name.rsplit(".", 1)[-1] if "." in full_name else full_name
    
    import_stmt = f"from {module_part} import {name_part}" if module_part else f"import {name_part}"
    if alias_name != name_part:
        import_stmt += f" as {alias_name}"
    
    return import_stmt


def _find_import_block_end(file_path: Path) -> int:
    """Find the line number where the import block ends."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0
    
    in_import_block = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        
        if line.startswith('import ') or line.startswith('from '):
            in_import_block = True
            continue
        
        if in_import_block:
            if (line[0] in [' ', '\t'] or stripped in [')', ']'] or stripped.startswith(')') or stripped.startswith(']')):
                continue
            return i
    
    return 0


class PostImportVisitor(ast.NodeVisitor):
    """Visitor that only processes nodes after the import block."""
    
    def __init__(self, start_line: int, collector: NameCollector):
        self.start_line = start_line
        self.collector = collector
    
    def visit(self, node):
        lineno = getattr(node, 'lineno', 0)
        if lineno >= self.start_line:
            self.collector.visit(node)
        else:
            for child in ast.iter_child_nodes(node):
                self.visit(child)


def get_unused_imports(file_path: Path, src_root: Path) -> List[dict]:
    """Detect unused imports in a Python file.
    
    Args:
        file_path: Full path to the Python file
        src_root: Root of the src directory for calculating relative paths
    
    Returns:
        List of error dictionaries for unused imports
    """
    tree = parse_file_ast(file_path)
    if not tree:
        return []

    import_end_line = _find_import_block_end(file_path)
    
    import_collector = ImportCollector()
    name_collector = NameCollector()
    import_collector.visit(tree)
    
    if import_end_line > 0:
        post_import_visitor = PostImportVisitor(import_end_line, name_collector)
        post_import_visitor.visit(tree)
    else:
        name_collector.visit(tree)
    
    unused = []
    rel_path = get_relative_path(file_path, src_root)
    for alias_name, (full_name, line_num, import_type) in import_collector.imports_map.items():
        if _is_import_used(alias_name, full_name, import_type, name_collector.used_names, name_collector.__all__, file_path, line_num):
            continue
        
        import_stmt = _format_import_statement(full_name, alias_name, import_type)
        unused.append(create_error(rel_path, "F401", f"Unused import: {import_stmt}", line_num))
    
    return unused
