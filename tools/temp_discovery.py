import os
import sys
import glob
sys.path.append('tools')
from util_fs import hash_text, exists, read

include = ['**/*.py']
exclude = ['**/.venv/**', '**/site-packages/**', '**/__pycache__/**', '**/build/**', '**/dist/**', '**/migrations/**', '**/tests/**']

def list_py_files(include, exclude):
    files = []
    for pattern in include:
        files.extend(glob.glob(pattern, recursive=True))
    # Filter out excluded
    filtered = []
    for f in files:
        excluded = False
        for ex in exclude:
            if glob.fnmatch.fnmatch(f, ex):
                excluded = True
                break
        if not excluded:
            filtered.append(f)
    return filtered

files = list_py_files(include, exclude)

def is_package(file_path):
    dir_path = os.path.dirname(file_path)
    return os.path.exists(os.path.join(dir_path, '__init__.py'))

packages = [f for f in files if is_package(f)]
modules = [f for f in files if not is_package(f)]
packages.sort()
modules.sort()
sorted_files = packages + modules

text = '\n'.join(sorted_files)
discovery_hash = hash_text(text)

hash_file = 'tools/.docgen_discovery.hash'
if not exists(hash_file) or read(hash_file) != discovery_hash:
    with open(hash_file, 'w', encoding='utf-8') as f:
        f.write(discovery_hash)

print('Sorted list of files:')
for f in sorted_files:
    print(f)
print(f'Discovery hash: {discovery_hash}')