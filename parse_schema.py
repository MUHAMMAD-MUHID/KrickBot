import re
import os

with open(r'f:\Projects\KrickBot\schema.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# We are looking for CREATE TABLE `name` ( ... ) ENGINE...
blocks = re.findall(r'CREATE TABLE `([^`]+)` \((.*?)\).*?;', sql, re.DOTALL | re.IGNORECASE)

clean_schema = []
for table_name, columns_text in blocks:
    lines = columns_text.split('\n')
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('PRIMARY KEY') or line.startswith('KEY') or line.startswith('UNIQUE KEY') or line.startswith('CONSTRAINT'):
            continue
        # Remove trailing commas
        line = re.sub(r',$', '', line)
        # Extract column name and type roughly
        match = re.match(r'`([^`]+)`\s+([a-zA-Z0-9_]+(\([^)]+\))?)', line)
        if match:
            col_name = match.group(1)
            col_type = match.group(2)
            clean_lines.append(f'  {col_name} {col_type}')
    
    if clean_lines:
        table_def = f'CREATE TABLE {table_name} (\n' + ',\n'.join(clean_lines) + '\n);'
        clean_schema.append(table_def)

print(f'Found {len(clean_schema)} tables.')

result = '\n\n'.join(clean_schema)
with open(r'f:\Projects\KrickBot\extracted_schema.txt', 'w', encoding='utf-8') as out:
    out.write(result)
