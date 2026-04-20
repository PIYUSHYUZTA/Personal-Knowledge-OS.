#!/usr/bin/env python
"""
Comprehensive Python syntax checker for backend directory.
Uses ast module to parse and check all .py files.
"""
import os
import ast
import sys
from pathlib import Path

def check_python_syntax(filepath):
    """
    Check if a Python file has valid syntax.
    Returns (is_valid, error_message)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg} - {e.text}"
    except UnicodeDecodeError as e:
        return False, f"UnicodeDecodeError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def main():
    """Main function to check all Python files."""
    backend_path = Path(r'e:\Personal Knowledge Os\backend')
    
    # Directories to skip
    skip_dirs = {'__pycache__', 'venv', '.venv', '.pytest_cache', '.git', 'node_modules'}
    
    files_to_check = []
    
    # Find all .py files
    for py_file in backend_path.rglob('*.py'):
        # Skip files in skip directories
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
        files_to_check.append(py_file)
    
    files_to_check.sort()
    
    # Check each file
    errors = []
    print(f"Checking {len(files_to_check)} Python files...\n")
    print("=" * 80)
    
    for filepath in files_to_check:
        is_valid, error = check_python_syntax(filepath)
        rel_path = filepath.relative_to(backend_path)
        
        if is_valid:
            print(f"✓ {rel_path}")
        else:
            print(f"✗ {rel_path}")
            errors.append((rel_path, error))
    
    # Summary
    print("\n" + "=" * 80)
    print(f"Total files checked: {len(files_to_check)}")
    print(f"Files with syntax errors: {len(errors)}")
    print("=" * 80)
    
    if errors:
        print("\nFILES WITH SYNTAX ERRORS:\n")
        for filepath, error in errors:
            print(f"{filepath}:")
            print(f"  {error}\n")
        return 1
    else:
        print("\n✓ All files passed syntax check!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
