import sys, os

# Load the NEW_TEMPLATE from _new_template.py
spec = {}
exec(open('render/_new_template.py', encoding='utf-8').read(), spec)
new_tpl = spec['NEW_TEMPLATE']

# Read ui_generator.py
with open('render/ui_generator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start and end of the html_template string
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'html_template = """<!DOCTYPE html>' in line:
        start_idx = i
    if start_idx != -1 and '</html>"""' in line:
        end_idx = i
        break

if start_idx == -1 or end_idx == -1:
    print("ERROR: Could not find html_template block.")
    sys.exit(1)

# Construct the new file content
new_lines = lines[:start_idx]
new_lines.append('    html_template = """' + new_tpl + '"""\n')
new_lines.extend(lines[end_idx+1:])

with open('render/ui_generator.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("SUCCESS: ui_generator.py updated with restored V32 template.")
