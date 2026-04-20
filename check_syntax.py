#!/usr/bin/env python
"""Check Python syntax for all .py files in backend directory."""
import os
import py_compile
import sys

backend_path = r'e:\Personal Knowledge Os\backend'
files_to_check = []
errors_found = []

# Find all .py files recursively
for root, dirs, files in os.walk(backend_path):
    # Skip __pycache__ and venv directories
    dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.pytest_cache']]
    
    for file in files:
        if file.endswith('.py'):
            files_to_check.append(os.path.join(root, file))

# Sort for consistent output
files_to_check.sort()

# Check syntax for each file
print(f"Checking {len(files_to_check)} Python files...\n")
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✓ {filepath}")
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath}")
        print(f"  Error: {e}")
        errors_found.append((filepath, str(e)))

# Report summary
print(f"\n{'='*70}")
print(f"Total files checked: {len(files_to_check)}")
print(f"Files with syntax errors: {len(errors_found)}")

if errors_found:
    print(f"\n{'='*70}")
    print("FILES WITH SYNTAX ERRORS:")
    for filepath, error in errors_found:
        print(f"\n{filepath}:")
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n✓ All files passed syntax check!")
    sys.exit(0)
