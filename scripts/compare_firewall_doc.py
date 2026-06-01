import re
from pathlib import Path

root = Path(__file__).resolve().parent
conf = root / '..' / 'v5.15.conf'
tex = root / '..' / 'vyos_documentation.tex'

conf_text = conf.read_text(encoding='utf-8')
tex_text = tex.read_text(encoding='utf-8')

# find description "..." in conf
descs = re.findall(r'description\s+"([^"]+)"', conf_text)
# unique preserve order
seen = set(); unique_descs = []
for d in descs:
    if d not in seen:
        seen.add(d); unique_descs.append(d)

missing_in_tex = []
for d in unique_descs:
    if d not in tex_text:
        missing_in_tex.append(d)

# find potential doc-only entries: words that look like descriptions in tex (dash-separated, lowercase)
doc_descs = set(re.findall(r'[a-z0-9]+(?:-[a-z0-9]+){2,}', tex_text))
missing_in_conf = []
for dd in sorted(doc_descs):
    if dd not in seen:
        missing_in_conf.append(dd)

print(f"Total descriptions in v5.15.conf: {len(unique_descs)}")
print(f"Descriptions missing in vyos_documentation.tex: {len(missing_in_tex)}")
if missing_in_tex:
    print('\nMissing in tex:')
    for d in missing_in_tex:
        print(d)

print('\nPotential dash-keywords found in tex not in conf:')
print(len(missing_in_conf))
if missing_in_conf:
    for d in missing_in_conf[:200]:
        print(d)
