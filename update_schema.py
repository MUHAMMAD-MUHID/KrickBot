import re

with open(r'f:\Projects\KrickBot\app\query_pipeline\text_to_sql.py', 'r', encoding='utf-8') as f:
    code = f.read()

with open(r'f:\Projects\KrickBot\extracted_schema.txt', 'r', encoding='utf-8') as f:
    schema = f.read()

new_code = re.sub(
    r'SCHEMA_CONTEXT = \"\"\"(.*?)\"\"\"',
    'SCHEMA_CONTEXT = \"\"\"' + schema.replace('\\', '\\\\') + '\n\"\"\"',
    code,
    flags=re.DOTALL
)

with open(r'f:\Projects\KrickBot\app\query_pipeline\text_to_sql.py', 'w', encoding='utf-8') as f:
    f.write(new_code)

print('Updated SCHEMA_CONTEXT successfully.')
