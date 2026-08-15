import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.graphql.schema import schema
type_map = schema.schema_converter.type_map
def get_base_type(t):
    t_name = type(t).__name__
    if t_name in ["StrawberryOptional", "StrawberryList"]:
        return get_base_type(t.of_type)
    return t
def get_type_name(t):
    base = get_base_type(t)
    if hasattr(base, "__name__"):
        return base.__name__
    if hasattr(base, "name"):
        return base.name
    return str(base)
def generate_mock_value(t):
    t_name = type(t).__name__
    if t_name == "StrawberryOptional":
        return generate_mock_value(t.of_type)
    if t_name == "StrawberryList":
        return "[" + generate_mock_value(t.of_type) + "]"
    name = get_type_name(t)
    if name == "String": return '"string"'
    if name == "Int": return "0"
    if name == "Float" or name == "Decimal": return "0.0"
    if name == "Boolean": return "true"
    if name == "UUID" or name == "ID": return '"00000000-0000-0000-0000-000000000000"'
    if name == "DateTime": return '"2023-01-01T00:00:00Z"'
    if name == "Date": return '"2023-01-01"'
    if name == "JSON": return '"{}"'
    
    # Enum
    mapped_type = type_map.get(name)
    if mapped_type and hasattr(mapped_type, "values"):
        return mapped_type.values[0].name
        
    # Input object
    if mapped_type and hasattr(mapped_type.definition, "is_input") and mapped_type.definition.is_input:
        fields_str = []
        for f in getattr(mapped_type.definition, "fields", []):
            val = generate_mock_value(f.type)
            fields_str.append(f"{getattr(f, 'python_name', '') or f.name}: {val}")
        return "{ " + ", ".join(fields_str) + " }"
        
    return '""'
def get_scalar_selection(t, depth=0):
    if depth > 1:
        return ""
    base = get_base_type(t)
    name = get_type_name(base)
    mapped_type = type_map.get(name)
    
    if not mapped_type or not hasattr(mapped_type, "definition") or getattr(mapped_type.definition, "is_input", False):
        return ""
        
    fields = getattr(mapped_type.definition, "fields", [])
    if not fields:
        return ""
        
    selection = []
    for f in fields:
        f_name = getattr(f, 'python_name', '') or f.name
        f_base = get_type_name(f.type)
        if f_base in ["String", "Int", "Float", "Boolean", "ID", "UUID", "DateTime", "Date", "JSON", "Decimal"]:
            selection.append(f_name)
        elif type_map.get(f_base) and hasattr(type_map[f_base], "values"):
            selection.append(f_name) # Enum is a leaf
    
    if not selection and fields:
        # no scalars found, try picking the first object field
        sub = get_scalar_selection(fields[0].type, depth + 1)
        if sub:
            selection.append(f"{getattr(fields[0], 'python_name', '') or fields[0].name} {sub}")
            
    if not selection:
        return ""
        
    return "{\n    " + "\n    ".join(selection) + "\n  }"
def generate_markdown():
    md = "# Postman GraphQL API Samples\n\n"
    md += "This document contains ready-to-copy sample queries and mutations for Postman.\n"
    md += "Each request requires the appropriate headers to be set in Postman's **Headers** tab.\n\n"
    
    md += "## Standard Headers Required\n"
    md += "For most authenticated requests, you should include the following headers:\n"
    md += "```http\n"
    md += "Content-Type: application/json\n"
    md += "Authorization: Bearer <your_jwt_token>\n"
    md += "X-Tenant-ID: <your_tenant_uuid>\n"
    md += "```\n\n"
    md += "---\n\n"
    
    query_type = type_map.get("Query")
    mutation_type = type_map.get("Mutation")
    
    if query_type:
        md += "## Queries\n\n"
        for field in getattr(query_type.definition, "fields", []):
            name = getattr(field, 'python_name', '') or field.name
            args_str = ""
            args = getattr(field, "arguments", [])
            if args:
                args_list = []
                for arg in args:
                    arg_name = getattr(arg, 'python_name', '') or arg.name
                    args_list.append(f"{arg_name}: {generate_mock_value(arg.type)}")
                args_str = "(" + ", ".join(args_list) + ")"
                
            selection = get_scalar_selection(field.type)
            
            md += f"### {name}\n"
            md += "**Headers:**\n"
            md += "```http\n"
            md += "Content-Type: application/json\n"
            md += "Authorization: Bearer <your_jwt_token>\n"
            md += "X-Tenant-ID: <your_tenant_uuid>\n"
            md += "```\n"
            md += "**Body (GraphQL):**\n"
            md += "```graphql\n"
            md += f"query {{\n  {name}{args_str} {selection}\n}}\n"
            md += "```\n\n"
            
    if mutation_type:
        md += "## Mutations\n\n"
        for field in getattr(mutation_type.definition, "fields", []):
            name = getattr(field, 'python_name', '') or field.name
            args_str = ""
            args = getattr(field, "arguments", [])
            if args:
                args_list = []
                for arg in args:
                    arg_name = getattr(arg, 'python_name', '') or arg.name
                    args_list.append(f"{arg_name}: {generate_mock_value(arg.type)}")
                args_str = "(" + ", ".join(args_list) + ")"
                
            selection = get_scalar_selection(field.type)
            
            md += f"### {name}\n"
            md += "**Headers:**\n"
            md += "```http\n"
            md += "Content-Type: application/json\n"
            md += "Authorization: Bearer <your_jwt_token>\n"
            md += "X-Tenant-ID: <your_tenant_uuid>\n"
            md += "```\n"
            md += "**Body (GraphQL):**\n"
            md += "```graphql\n"
            md += f"mutation {{\n  {name}{args_str} {selection}\n}}\n"
            md += "```\n\n"
            
    artifact_path = "C:\\Users\\Admin\\.gemini\\antigravity-ide\\brain\\7ae18e1a-eeb2-4049-b9e8-436ebd7ff714\\postman_samples.md"
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(md)
        
    print(f"Postman samples generated successfully at {artifact_path}.")
if __name__ == '__main__':
    generate_markdown()