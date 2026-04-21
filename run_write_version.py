import os
version = os.environ.get('VERSION', '0.0.0').lstrip('v')
with open('version.py', 'w', encoding='utf-8') as f:
    f.write(f'version = "{version}"\n')