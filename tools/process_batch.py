import sys
sys.path.append('tools')
from progress_tracker import load_state, next_batch, save_state, mark_done
from util_fs import read, write_once
from ast_scan import scan
from exception_io_detect import detect as detect_io
from config_concurrency_detect import detect as detect_config
from api_catalog import catalog
from docstring_writer import apply as apply_docstrings
from comment_updater import revise
from ast_guard import ast_equal_ignoring_docs

# Load state
state = load_state('tools/.docgen_state.json')

# Get batch
batch = next_batch(state, 250)

# Save state after getting batch
save_state('tools/.docgen_state.json', state)

# Process each file
for file_path in batch:
    try:
        # Read file
        code = read(file_path)
        
        # Check marker
        if "DOCGEN:LLM-FIRST@v4" in code:
            mark_done(state, file_path, 'skipped')
            continue
        
        # Scan AST
        ast_info = scan(code)
        
        # Detect facts
        facts_io = detect_io(code, ast_info)
        facts_config = detect_config(code, ast_info)
        facts = {**facts_io, **facts_config}
        
        # Build API catalog
        api_cat = catalog(file_path, code, ast_info)
        
        # For templates, use dummy templates for now
        templates = {
            'function': '"""Function {name}.\n\nArgs:\n    {args}\n\nReturns:\n    {returns}\n"""',
            'class': '"""Class {name}.\n\nAttributes:\n    {attrs}\n"""',
            'module': '"""Module {name}.\n\n{description}\n"""'
        }
        
        # Generate/merge docstrings
        new_code = apply_docstrings(code, facts, templates, "DOCGEN:LLM-FIRST@v4")
        
        # Update comments
        new_code = revise(new_code, facts)
        
        # Verify AST equivalence
        if not ast_equal_ignoring_docs(code, new_code):
            mark_done(state, file_path, 'error')
            continue
        
        # Write once if changes
        if code != new_code:
            write_once(file_path, new_code)
            mark_done(state, file_path, 'updated')
        else:
            mark_done(state, file_path, 'unchanged')
        
        # Persist progress
        save_state('tools/.docgen_state.json', state)
        
    except Exception as e:
        mark_done(state, file_path, 'error')
        save_state('tools/.docgen_state.json', state)

# Final save
save_state('tools/.docgen_state.json', state)

print(f"Processed {len(batch)} files")