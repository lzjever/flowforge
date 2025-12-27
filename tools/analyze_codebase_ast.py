#!/usr/bin/env python3
"""
AST Analyzer for FlowForge Codebase

Analyzes core code files and generates a compact reference document for LLMs.
"""
import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json


class ASTAnalyzer(ast.NodeVisitor):
    """AST visitor to extract class and function information."""
    
    def __init__(self):
        self.classes: Dict[str, Dict[str, Any]] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.current_class: Optional[str] = None
        self.current_method: Optional[str] = None
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class information."""
        bases = [self._get_name(base) for base in node.bases]
        docstring = ast.get_docstring(node)
        
        methods = {}
        properties = {}
        class_vars = {}
        
        # Store current class context
        old_class = self.current_class
        self.current_class = node.name
        
        # Visit class body
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(item, is_method=True)
                if method_info:
                    methods[item.name] = method_info
            elif isinstance(item, ast.AsyncFunctionDef):
                method_info = self._extract_function_info(item, is_method=True, is_async=True)
                if method_info:
                    methods[item.name] = method_info
            elif isinstance(item, ast.Assign):
                # Try to extract class variables
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_vars[target.id] = self._get_value_repr(item.value)
        
        self.classes[node.name] = {
            'bases': bases,
            'docstring': docstring or '',
            'methods': methods,
            'properties': properties,
            'class_vars': class_vars,
            'decorators': [self._get_name(d) for d in node.decorator_list]
        }
        
        self.current_class = old_class
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function information."""
        if self.current_class is None:  # Module-level function
            func_info = self._extract_function_info(node, is_method=False)
            if func_info:
                self.functions[node.name] = func_info
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Extract async function information."""
        if self.current_class is None:  # Module-level function
            func_info = self._extract_function_info(node, is_method=False, is_async=True)
            if func_info:
                self.functions[node.name] = func_info
        self.generic_visit(node)
    
    def _extract_function_info(self, node: ast.FunctionDef | ast.AsyncFunctionDef, 
                               is_method: bool = False, is_async: bool = False) -> Optional[Dict[str, Any]]:
        """Extract detailed function/method information."""
        # Skip private methods that start with __ (except special methods)
        special_methods = ['__init__', '__call__', '__repr__', '__str__', '__eq__', '__hash__', '__len__', '__getitem__', '__setitem__']
        if node.name.startswith('__') and node.name not in special_methods:
            return None
        
        # Skip private methods (starting with _) for module-level functions
        if not is_method and node.name.startswith('_'):
            return None
        
        docstring = ast.get_docstring(node)
        args = []
        defaults = {}
        
        # Extract arguments
        args_list = node.args
        num_defaults = len(args_list.defaults)
        num_args = len(args_list.args)
        
        for i, arg in enumerate(args_list.args):
            arg_name = arg.arg
            if arg_name == 'self' or arg_name == 'cls':
                continue
            
            arg_info = {
                'name': arg_name,
                'annotation': self._get_annotation(arg.annotation) if arg.annotation else None,
                'default': None
            }
            
            # Check for default value
            default_index = i - (num_args - num_defaults)
            if default_index >= 0:
                arg_info['default'] = self._get_value_repr(args_list.defaults[default_index])
            
            args.append(arg_info)
        
        # Extract return annotation
        return_annotation = None
        if hasattr(node, 'returns') and node.returns:
            return_annotation = self._get_annotation(node.returns)
        
        return {
            'name': node.name,
            'docstring': docstring or '',
            'args': args,
            'return_annotation': return_annotation,
            'is_async': is_async,
            'decorators': [self._get_name(d) for d in node.decorator_list]
        }
    
    def _get_name(self, node: ast.AST) -> str:
        """Get string representation of an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
    
    def _get_annotation(self, node: ast.AST) -> str:
        """Get type annotation string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
    
    def _get_value_repr(self, node: ast.AST) -> str:
        """Get string representation of a value."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return repr(node.s)
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)


def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        analyzer = ASTAnalyzer()
        analyzer.visit(tree)
        
        return {
            'file': str(file_path.relative_to(Path.cwd())),
            'classes': analyzer.classes,
            'functions': analyzer.functions
        }
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        return {'file': str(file_path), 'error': str(e)}


def format_compact_doc(analysis_results: List[Dict[str, Any]]) -> str:
    """Format analysis results into a compact document."""
    lines = []
    lines.append("# FlowForge Core API Reference (Compact)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Compact reference for LLM code generation. Extracted from AST analysis.")
    lines.append("")
    
    # Group by file
    for result in analysis_results:
        if 'error' in result:
            continue
        
        file_path = result['file']
        lines.append(f"## {file_path}")
        lines.append("")
        
        # Classes
        if result['classes']:
            for class_name, class_info in sorted(result['classes'].items()):
                lines.append(f"### {class_name}")
                
                # Bases (compact)
                if class_info['bases']:
                    bases_str = ', '.join(class_info['bases'])
                    lines.append(f"Bases: {bases_str}")
                
                # Docstring (first line only, compact)
                if class_info['docstring']:
                    first_line = class_info['docstring'].split('\n')[0].strip()
                    if first_line:
                        lines.append(f"{first_line}")
                
                # Methods (compact format)
                if class_info['methods']:
                    for method_name, method_info in sorted(class_info['methods'].items()):
                        # Build method signature (compact)
                        sig_parts = []
                        if method_info['is_async']:
                            sig_parts.append("async")
                        sig_parts.append(method_name)
                        
                        # Args
                        args_str = []
                        for arg in method_info['args']:
                            arg_str = arg['name']
                            if arg['annotation']:
                                arg_str += f":{arg['annotation']}"
                            if arg['default']:
                                arg_str += f"={arg['default']}"
                            args_str.append(arg_str)
                        
                        sig = f"{' '.join(sig_parts)}({', '.join(args_str)})"
                        if method_info['return_annotation']:
                            sig += f" -> {method_info['return_annotation']}"
                        
                        # Add docstring (first line only, compact)
                        doc = ""
                        if method_info['docstring']:
                            first_line = method_info['docstring'].split('\n')[0].strip()
                            if first_line:
                                # Remove trailing period for compactness
                                first_line = first_line.rstrip('.')
                                doc = f"  # {first_line}"
                        
                        lines.append(f"  {sig}{doc}")
                
                lines.append("")
        
        # Module-level functions (only if not already in a class)
        if result['functions']:
            lines.append("### Functions")
            for func_name, func_info in sorted(result['functions'].items()):
                # Skip if it's a method from a class
                is_class_method = any(func_name in cls_info['methods'] 
                                    for cls_info in result['classes'].values())
                if is_class_method:
                    continue
                
                sig_parts = []
                if func_info['is_async']:
                    sig_parts.append("async")
                sig_parts.append(func_name)
                
                args_str = []
                for arg in func_info['args']:
                    arg_str = arg['name']
                    if arg['annotation']:
                        arg_str += f":{arg['annotation']}"
                    if arg['default']:
                        arg_str += f"={arg['default']}"
                    args_str.append(arg_str)
                
                sig = f"{' '.join(sig_parts)}({', '.join(args_str)})"
                if func_info['return_annotation']:
                    sig += f" -> {func_info['return_annotation']}"
                
                doc = ""
                if func_info['docstring']:
                    first_line = func_info['docstring'].split('\n')[0].strip()
                    if first_line:
                        first_line = first_line.rstrip('.')
                        doc = f"  # {first_line}"
                
                lines.append(f"  {sig}{doc}")
        
        lines.append("")
    
    return '\n'.join(lines)


def main():
    """Main entry point."""
    # Core files to analyze
    core_files = [
        'flowforge/routine.py',
        'flowforge/flow.py',
        'flowforge/slot.py',
        'flowforge/event.py',
        'flowforge/connection.py',
        'flowforge/error_handler.py',
        'flowforge/job_state.py',
        'flowforge/execution_tracker.py',
        'flowforge/utils/serializable.py',
        'flowforge/serialization_utils.py',
    ]
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Analyze files
    results = []
    for file_path_str in core_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            print(f"Analyzing {file_path_str}...", file=sys.stderr)
            result = analyze_file(file_path)
            results.append(result)
        else:
            print(f"Warning: {file_path_str} not found", file=sys.stderr)
    
    # Generate compact document
    doc = format_compact_doc(results)
    
    # Output
    output_file = project_root / 'docs' / 'source' / 'api_reference_compact.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(doc)
    
    print(f"\nCompact API reference generated: {output_file}", file=sys.stderr)
    print(f"Total size: {len(doc)} characters, {len(doc.splitlines())} lines", file=sys.stderr)
    
    # Write to file only (don't print to stdout to avoid mixing with stderr)
    # The file is already written above


if __name__ == '__main__':
    main()

