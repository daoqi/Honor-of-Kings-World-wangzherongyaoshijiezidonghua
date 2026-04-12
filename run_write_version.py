import os
version = os.getenv('VERSION', '0.0.0')
with open('version.py', 'w', encoding='utf-8') as f:
    f.write(f'version = "{version}"')