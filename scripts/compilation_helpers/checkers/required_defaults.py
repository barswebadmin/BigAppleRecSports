"""Check for required fields/parameters with defaults using AST analysis."""

import ast
from pathlib import Path
from typing import List, Optional

from scripts.compilation_helpers.repo_path_resolvers import get_relative_path
from scripts.compilation_helpers.checkers._checkers_common import create_error, parse_file_ast


def _has_none_in_union(annotation: ast.BinOp) -> bool:
    """Check if a BinOp union contains None."""
    if isinstance(annotation.right, ast.Constant) and annotation.right.value is None:
        return True
    if isinstance(annotation.left, ast.Constant) and annotation.left.value is None:
        return True
    if isinstance(annotation.left, ast.BinOp):
        return _has_none_in_union(annotation.left)
    if isinstance(annotation.right, ast.BinOp):
        return _has_none_in_union(annotation.right)
    return False


def _has_none_in_union_args(slice_node: ast.expr) -> bool:
    """Check if Union args contain None."""
    if hasattr(ast, 'Index') and isinstance(slice_node, ast.Index):
        slice_node = slice_node.value  # type: ignore[attr-defined]
    
    if isinstance(slice_node, ast.Tuple):
        return any(isinstance(elt, ast.Constant) and elt.value is None for elt in slice_node.elts)
    return isinstance(slice_node, ast.Constant) and slice_node.value is None


def _is_optional_type(annotation: ast.expr) -> bool:
    """Check if a type annotation is Optional, Union[T, None], or uses | None syntax."""
    # Python 3.10+ union syntax: str | Path | None
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _has_none_in_union(annotation)
    
    # Optional[T] or Union[T, None]
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        name_id = annotation.value.id
        if name_id == "Optional":
            return True
        if name_id == "Union":
            return _has_none_in_union_args(annotation.slice)
    
    return False


def _is_pydantic_model_class(node: ast.ClassDef) -> bool:
    """Check if a class inherits from BaseModel or ApiModel."""
    model_names = {"BaseModel", "ApiModel"}
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in model_names:
            return True
        if isinstance(base, ast.Attribute) and base.attr in model_names:
            return True
    return False


def _is_field_with_ellipsis_default(value: ast.Call) -> bool:
    """Check if Field() call has default=... (which means required, no default)."""
    if not isinstance(value.func, ast.Name) or value.func.id != "Field":
        return False
    
    for kw in value.keywords:
        if kw.arg == "default":
            return isinstance(kw.value, ast.Constant) and kw.value.value is ...
        if kw.arg == "default_factory":
            return False  # default_factory means it has a default
    return False


def _has_real_default(value: ast.expr) -> bool:
    """Check if a default value is real (not Field(default=...))."""
    if not isinstance(value, ast.Call):
        return True
    return not _is_field_with_ellipsis_default(value)


def _get_type_name(annotation: ast.expr) -> str:
    """Get type name from annotation for error messages."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        return annotation.value.id
    return "Type"


def _get_field_name(target: ast.expr) -> str:
    """Get field name from assignment target."""
    return target.id if isinstance(target, ast.Name) else "unknown"


class RequiredDefaultsChecker(ast.NodeVisitor):
    """AST visitor to find required fields/parameters with defaults."""
    
    def __init__(self, file_path: Path, src_root: Path):
        self.file_path = file_path
        self.src_root = src_root
        self.rel_path = get_relative_path(file_path, src_root)
        self.errors: List[dict] = []
        self.current_class_is_model = False
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check for Pydantic models."""
        self.current_class_is_model = _is_pydantic_model_class(node)
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and item.value is not None:
                self._check_class_field(item)
        
        self.generic_visit(node)
        self.current_class_is_model = False
    
    def _is_overload(self, node: ast.FunctionDef) -> bool:
        """Check if function is decorated with @overload."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "overload":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "overload":
                return True
        return False
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check for required params with defaults."""
        # Skip overloads - they're type hints only and defaults are part of the signature pattern
        if self._is_overload(node):
            self.generic_visit(node)
            return
        
        if not node.args.defaults:
            self.generic_visit(node)
            return
        
        required_count = len(node.args.args) - len(node.args.defaults)
        
        for arg in node.args.args[required_count:]:
            if arg.annotation and not _is_optional_type(arg.annotation):
                self.errors.append(create_error(
                    self.rel_path,
                    "REQ_DEFAULT",
                    f"Required parameter '{arg.arg}' has default value",
                    arg.lineno
                ))
        
        self.generic_visit(node)
    
    def _check_class_field(self, node: ast.AnnAssign) -> None:
        """Check a class field for required field with default."""
        if not self.current_class_is_model:
            return
        if not node.annotation or _is_optional_type(node.annotation):
            return
        if not node.value or not _has_real_default(node.value):
            return
        
        field_name = _get_field_name(node.target)
        type_name = _get_type_name(node.annotation)
        self.errors.append(create_error(
            self.rel_path,
            "REQ_DEFAULT",
            f"Required field '{field_name}' should not have a default. "
            f"Make it Optional[{type_name}] or remove the default.",
            node.lineno
        ))


def check_required_defaults(file_path: Path, src_root: Path) -> List[dict]:
    """Check for required fields/parameters with defaults.
    
    Args:
        file_path: Full path to the Python file
        src_root: Root of the src directory for calculating relative paths
    
    Returns:
        List of error dictionaries for violations
    """
    tree = parse_file_ast(file_path)
    if not tree:
        return []
    
    checker = RequiredDefaultsChecker(file_path, src_root)
    checker.visit(tree)
    return checker.errors
