import ast
import os

def check_sql_injection(node, filepath):
    # Check if this is a call to 'text'
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'text':
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (text with f-string)")
            elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (text with % formatting)")
            elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == 'format':
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (text with .format())")

    # Check if this is a call to '.execute()' directly
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'execute':
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (execute with f-string)")
            elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (execute with % formatting)")
            elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == 'format':
                print(f"Potential SQL injection found in {filepath} at line {node.lineno} (execute with .format())")


def audit():
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            check_sql_injection(node, filepath)
                    except Exception as e:
                        print(f"Error parsing {filepath}: {e}")

audit()
