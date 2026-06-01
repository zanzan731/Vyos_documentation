#!/usr/bin/env python3
"""
patch_md_with_tex_tables.py

Usage:
  python patch_md_with_tex_tables.py vyos_documentation.tex vyos_documentation.md > vyos_documentation.fixed.md

What it does:
- Scans the .tex file for \begin{longtable}...\end{longtable} blocks
- Converts each LaTeX longtable (rows separated by '&' and ending with '\\') into a Markdown table
- Finds a matching table in the .md file by matching the header row content and replaces the broken table in the .md with the generated Markdown table

This is a pragmatic post-processing step to repair large tables that Pandoc's LaTeX reader mishandles.
"""
import re
import sys

if len(sys.argv) != 3:
    print("Usage: python patch_md_with_tex_tables.py input.tex input.md > output.md", file=sys.stderr)
    sys.exit(2)

tex_path = sys.argv[1]
md_path = sys.argv[2]

tex = open(tex_path, encoding='utf-8').read()
md = open(md_path, encoding='utf-8').read()

# Helper transformations
def clean_cell(cell):
    cell = cell.strip()
    # convert \texttt{foo} -> `foo`
    cell = re.sub(r"\\texttt\{([^}]*)\}", r"`\1`", cell)
    # convert \textbf{foo} -> **foo**
    cell = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", cell)
    # remove other simple braces around text \emph{...} -> ...
    cell = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", cell)
    # remove curly braces leftovers
    cell = cell.replace('{', '').replace('}', '')
    # replace LaTeX escaped underscore
    cell = cell.replace('\\_', '_')
    # strip leftover LaTeX spacing commands
    cell = re.sub(r"\\[a-zA-Z]+", '', cell)
    return cell.strip()

# Extract longtable blocks
longtable_re = re.compile(r"\\begin\{longtable\}\{([^}]*)\}(.*?)\\end\{longtable\}", re.S)
blocks = longtable_re.findall(tex)

converted_tables = []
for colspec, body in blocks:
    # body may contain \endfirsthead or other longtable commands; we only want rows with & and ending with \\
    # Extract candidate rows: lines containing '&' and ending with '\\' or lines with '&' then '\\hline'
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # skip longtable head/footer markers
        if line.startswith('\\endfirsthead') or line.startswith('\\endhead') or line.startswith('\\caption'):
            continue
        # accumulate lines that contain & and end with \\
        if '&' in line:
            # remove trailing \hline and similar
            line_clean = re.sub(r"\\hline", '', line)
            # trim trailing \\
            line_clean = re.sub(r"\\\\\s*$", '', line_clean)
            line_clean = line_clean.strip()
            if line_clean:
                rows.append(line_clean)
        else:
            # sometimes full row might be split across lines; naive approach: ignore
            continue
    if not rows:
        continue
    # Convert rows from LaTeX ' & ' to list of cells
    table = []
    for r in rows:
        # split on unescaped &
        parts = [clean_cell(c) for c in re.split(r'(?<!\\)&', r)]
        table.append(parts)
    # determine max columns
    maxcols = max(len(r) for r in table)
    # normalize rows to maxcols
    for r in table:
        if len(r) < maxcols:
            r.extend([''] * (maxcols - len(r)))
    # Build markdown table string
    header = table[0]
    sep = ['---'] * maxcols
    md_lines = []
    md_lines.append('| ' + ' | '.join(header) + ' |')
    md_lines.append('| ' + ' | '.join(sep) + ' |')
    for r in table[1:]:
        md_lines.append('| ' + ' | '.join(r) + ' |')
    # store original first header text to match in md
    header_key = ' | '.join([h.lower() for h in header])
    converted_tables.append((header_key, '\n'.join(md_lines)))

# Now patch md: for each converted table, find a matching table header in the md and replace the whole table block
out_lines = md.splitlines()
output = []
i = 0
n = len(out_lines)
while i < n:
    line = out_lines[i]
    # If a markdown table header line, try to match
    if line.strip().startswith('|') and '|' in line:
        # collect contiguous table block
        j = i
        table_block = []
        while j < n and out_lines[j].strip().startswith('|'):
            table_block.append(out_lines[j])
            j += 1
        # derive header key from first header row
        header_row = table_block[0]
        # normalize header row for matching
        hcells = [c.strip().strip('*`') for c in header_row.strip().strip('|').split('|')]
        header_key = ' | '.join([c.lower() for c in hcells])
        replaced = False
        for hk, md_table in converted_tables:
            # match if header_key contains the hk or hk contains header_key (fuzzy)
            if hk in header_key or header_key in hk:
                # replace this block with md_table
                output.append(md_table)
                i = j
                replaced = True
                break
        if replaced:
            continue
        else:
            # no matching converted table — keep original block
            output.extend(table_block)
            i = j
            continue
    else:
        output.append(line)
        i += 1

sys.stdout.write('\n'.join(output))
