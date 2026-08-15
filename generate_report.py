import os
import ast

def extract_type(node):
    if node is None:
        return "Unknown"
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Subscript):
        value = extract_type(node.value)
        slice_ = extract_type(node.slice)
        return f"{value}[{slice_}]"
    elif isinstance(node, ast.Attribute):
        return f"{extract_type(node.value)}.{node.attr}"
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Tuple):
        return ", ".join(extract_type(n) for n in node.elts)
    elif isinstance(node, ast.List):
        return "[" + ", ".join(extract_type(n) for n in node.elts) + "]"
    elif isinstance(node, ast.BinOp):
        return "BinOp"
    return "ComplexType"

def parse_graphql_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    results = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.endswith('Query') or node.name.endswith('Mutation'):
                op_type = "Query" if node.name.endswith('Query') else "Mutation"
                methods = []
                for child in node.body:
                    if isinstance(child, ast.AsyncFunctionDef) or isinstance(child, ast.FunctionDef):
                        is_graphql_op = False
                        for dec in child.decorator_list:
                            dec_name = extract_type(dec)
                            if 'strawberry.field' in dec_name or 'strawberry.mutation' in dec_name:
                                is_graphql_op = True
                                break
                        if not is_graphql_op:
                            continue
                        
                        docstring = ast.get_docstring(child) or "No description provided."
                        args = []
                        for arg in child.args.args:
                            if arg.arg in ('self', 'info'):
                                continue
                            arg_type = extract_type(arg.annotation) if arg.annotation else "Any"
                            args.append(f"{arg.arg}: {arg_type}")
                        for kwarg in child.args.kwonlyargs:
                            arg_type = extract_type(kwarg.annotation) if kwarg.annotation else "Any"
                            args.append(f"{kwarg.arg}: {arg_type}")
                        
                        ret_type = extract_type(child.returns) if child.returns else "Any"
                        methods.append({
                            "name": child.name,
                            "args": args,
                            "return_type": ret_type,
                            "docstring": docstring
                        })
                if methods:
                    results.append({
                        "module": os.path.basename(os.path.dirname(filepath)),
                        "class_name": node.name,
                        "type": op_type,
                        "methods": methods
                    })
    return results

def main():
    base_dir = r"c:\Users\Admin\Desktop\gubeera_ecom\app"
    all_data = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "graphql.py":
                filepath = os.path.join(root, file)
                parsed = parse_graphql_file(filepath)
                all_data.extend(parsed)
                
    # Group by module
    modules = {}
    for d in all_data:
        mod = d["module"]
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(d)
        
    md = ["# Frontend Integration Report: Next.js API Reference\n"]
    md.append("This document outlines all GraphQL Queries and Mutations available in the backend. It serves as a comprehensive reference for the Next.js frontend team.\n")
    md.append("## General Guidelines\n")
    md.append("- **Authentication**: For authenticated endpoints, include the header `Authorization: Bearer <token>`.\n")
    md.append("- **Tenant Context**: Most endpoints require a tenant context. Include the header `X-Tenant-ID: <uuid>` or ensure the user is logged in to a tenant.\n\n")
    
    for mod, classes in modules.items():
        md.append(f"## Module: `{mod.capitalize()}`\n")
        for cls_data in classes:
            md.append(f"### {cls_data['type']}: `{cls_data['class_name']}`\n")
            for m in cls_data['methods']:
                args_str = ", ".join(m['args'])
                md.append(f"#### `{m['name']}`\n")
                md.append(f"**Arguments:** `({args_str})`  \n")
                md.append(f"**Returns:** `{m['return_type']}`  \n")
                md.append(f"**Description:** {m['docstring']}\n\n")
                
    with open(r"C:\Users\Admin\Desktop\gubeera_ecom\frontend_report.md", "w", encoding="utf-8") as f:
        f.write("frontend_report".join(md))
    print("Report generated.")

if __name__ == '__main__':
    main()
