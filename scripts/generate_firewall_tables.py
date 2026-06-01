#!/usr/bin/env python3
"""Generate LaTeX longtable rows from v5.15.conf firewall and NAT sections.
Usage: python scripts/generate_firewall_tables.py [path/to/v5.15.conf]
Outputs: generated_firewall_tables.tex in the same folder as the config.
This tries to match the table column ordering used in vyos_documentation.tex.
"""
import sys
import re
from pathlib import Path


def read_blocks(text):
    """Yield (rule_no, block_text) for top-level 'rule N { ... }' occurrences inside given text.
    Uses brace-depth scanning so it works for nested configs.
    """
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r"\brule\s+(\d+)\s*\{", text[i:])
        if not m:
            break
        # adjust index to match
        start_idx = i + m.start()
        rule_no = int(m.group(1))
        # find opening brace position
        brace_pos = text.find('{', start_idx + m.end() - m.start())
        if brace_pos == -1:
            i = start_idx + 1
            continue
        depth = 0
        j = brace_pos
        while j < n:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0:
                    # include from start_idx to j
                    block_text = text[start_idx:j+1]
                    yield (rule_no, block_text)
                    i = j+1
                    break
            j += 1
        else:
            break


def extract_field(block_text, key):
    # look for key "value"
    m = re.search(rf'{key}\s+"([^"]+)"', block_text)
    if m:
        return m.group(1)
    return ''


def extract_interface(block_text, which):
    # which: inbound-interface or outbound-interface
    m = re.search(rf'{which}\s*\{{[^}}]*name\s+"([^"]+)"', block_text)
    if m:
        return m.group(1)
    # also sometimes name is on next lines without braces: inbound-interface { name "eth0" }
    m2 = re.search(rf'{which}\s*\{{[\s\S]*?name\s+"([^"]+)"', block_text)
    if m2:
        return m2.group(1)
    return ''


def extract_destination(block_text):
    addr = ''
    port = ''
    maddr = re.search(r'destination\s*\{[\s\S]*?address\s+"?([^"\s}]+)"?', block_text, re.S)
    if maddr:
        addr = maddr.group(1).strip().strip('"')
    mport = re.search(r'destination\s*\{[\s\S]*?port\s+"?([^"\}]+)"?', block_text, re.S)
    if mport:
        port = mport.group(1).strip().strip('"')
    # some NAT destination blocks have port directly under rule
    if not addr:
        m = re.search(r'destination\s*\{[^}]*address\s+([^\s}]+)', block_text)
        if m:
            addr = m.group(1).strip()
    return addr, port


def extract_source(block_text):
    m = re.search(r'source\s*\{[\s\S]*?address\s+"?([^"\s}]+)"?', block_text, re.S)
    if m:
        return m.group(1).strip().strip('"')
    return ''


def extract_translation(block_text):
    m = re.search(r'translation\s*\{[\s\S]*?address\s+"?([^"\s}]+)"?', block_text, re.S)
    if m:
        return m.group(1).strip().strip('"')
    return ''


def extract_protocol(block_text):
    m = re.search(r'protocol\s+"?([^"\s}]+)"?', block_text)
    if m:
        return m.group(1).strip()
    return ''


def get_full_rule_block(conf_text, rule_no):
    # find 'rule <n> {' and return the balanced block starting at that brace
    pat = re.compile(r'\brule\s+' + str(rule_no) + r'\s*\{')
    m = pat.search(conf_text)
    if not m:
        return ''
    start = conf_text.find('{', m.start())
    if start == -1:
        return ''
    depth = 0
    i = start
    n = len(conf_text)
    while i < n:
        if conf_text[i] == '{':
            depth += 1
        elif conf_text[i] == '}':
            depth -= 1
            if depth == 0:
                return conf_text[m.start():i+1]
        i += 1
    return ''


def latex_escape(s):
    return s.replace('_', '\\_')


def gen_dnat_rows(conf_text):
    # find the nat { destination { ... } } section
    out = []
    # extract the nat.destination top-level block
    nat_m = re.search(r'nat\s*\{', conf_text)
    if not nat_m:
        return out
    # find the 'destination {' that is inside nat block by locating the first destination following nat and extracting its balanced braces
    nat_start = nat_m.start()
    # find destination occurrence after nat_start
    dest_pos = conf_text.find('destination', nat_start)
    if dest_pos == -1:
        return out
    # find the opening brace for that destination
    open_brace = conf_text.find('{', dest_pos)
    if open_brace == -1:
        return out
    # extract balanced block
    depth = 0
    j = open_brace
    n = len(conf_text)
    while j < n:
        if conf_text[j] == '{':
            depth += 1
        elif conf_text[j] == '}':
            depth -= 1
            if depth == 0:
                dest_block = conf_text[open_brace+1:j]
                break
        j += 1
    else:
        return out
    for rule_no, block in read_blocks(dest_block):
        desc = extract_field(block, 'description')
        in_if = extract_interface(block, 'inbound-interface')
        addr, port = extract_destination(block)
        proto = extract_protocol(block)
        trans = extract_translation(block)
        # fallback: try to populate any missing fields from the full config rule block
        full = get_full_rule_block(conf_text, rule_no)
        if full:
            desc = desc or extract_field(full, 'description')
            in_if = in_if or extract_interface(full, 'inbound-interface')
            if not addr or not port:
                a, p = extract_destination(full)
                addr = addr or a
                port = port or p
            proto = proto or extract_protocol(full)
            trans = trans or extract_translation(full)
        # format: rule & desc & in & destaddr & port & proto & translation \\
        out.append(f"{rule_no} & {latex_escape(desc)} & {in_if} & {addr} & {port} & {proto} & {trans} \\\\")
    return out


def gen_snat_rows(conf_text):
    out = []
    # find nat.source block by locating 'source' after the top-level nat
    nat_m = re.search(r'nat\s*\{', conf_text)
    if not nat_m:
        return out
    nat_start = nat_m.start()
    src_pos = conf_text.find('source', nat_start)
    if src_pos == -1:
        return out
    open_brace = conf_text.find('{', src_pos)
    if open_brace == -1:
        return out
    depth = 0
    j = open_brace
    n = len(conf_text)
    while j < n:
        if conf_text[j] == '{':
            depth += 1
        elif conf_text[j] == '}':
            depth -= 1
            if depth == 0:
                src_block = conf_text[open_brace+1:j]
                break
        j += 1
    else:
        return out
    for rule_no, block in read_blocks(src_block):
        # rule numbers here parsed inside source rules
        out_if = extract_interface(block, 'outbound-interface')
        src = extract_source(block)
        proto = extract_protocol(block)
        trans = extract_translation(block)
        desc = extract_field(block, 'description')
        # fallback: populate missing fields from full config block
        full = get_full_rule_block(conf_text, rule_no)
        if full:
            desc = desc or extract_field(full, 'description')
            out_if = out_if or extract_interface(full, 'outbound-interface')
            src = src or extract_source(full)
            proto = proto or extract_protocol(full)
            trans = trans or extract_translation(full)
        # format similar to tex SNAT table seen: rule & desc & Out & Source & Proto & Prevod \\\n        out.append(f"{rule_no} & {latex_escape(desc)} & {out_if} & {src} & {proto} & {trans} \\\\")
    return out


def gen_firewall_table(conf_text, ip_version='ipv6', chain='forward'):
    # locate firewall -> ipv6/ipv4 -> forward/input/output -> filter -> { ... }
    out = []
    # extract the ip_version block from firewall
    fw_m = re.search(r'firewall\s*\{', conf_text)
    if not fw_m:
        return out
    # locate the ip_version block (ipv4 or ipv6)
    ip_pos = conf_text.find(ip_version, fw_m.start())
    if ip_pos == -1:
        return out
    ip_open = conf_text.find('{', ip_pos)
    if ip_open == -1:
        return out
    # extract balanced ip block
    depth = 0
    j = ip_open
    n = len(conf_text)
    ip_block = ''
    while j < n:
        if conf_text[j] == '{':
            depth += 1
        elif conf_text[j] == '}':
            depth -= 1
            if depth == 0:
                ip_block = conf_text[ip_open+1:j]
                break
        j += 1
    if not ip_block:
        return out
    # find chain inside ip_block
    chain_pos = ip_block.find(chain)
    if chain_pos == -1:
        return out
    chain_open = ip_block.find('{', chain_pos)
    if chain_open == -1:
        return out
    # extract filter block inside chain
    depth = 0
    k = chain_open
    filt_block = ''
    while k < len(ip_block):
        if ip_block[k] == '{':
            depth += 1
        elif ip_block[k] == '}':
            depth -= 1
            if depth == 0:
                # ip_block[chain_open+1:k] contains chain content; look for 'filter' inside
                chain_content = ip_block[chain_open+1:k]
                fpos = chain_content.find('filter')
                if fpos == -1:
                    return out
                fopen = chain_content.find('{', fpos)
                if fopen == -1:
                    return out
                # extract filter content
                depth2 = 0
                m2 = fopen
                while m2 < len(chain_content):
                    if chain_content[m2] == '{':
                        depth2 += 1
                    elif chain_content[m2] == '}':
                        depth2 -= 1
                        if depth2 == 0:
                            filt_block = chain_content[fopen+1:m2]
                            break
                    m2 += 1
                break
        k += 1
    if not filt_block:
        return out
    for rule_no, block in read_blocks(filt_block):
        action = extract_field(block, 'action') or ''
        desc = extract_field(block, 'description')
        in_if = extract_interface(block, 'inbound-interface')
        out_if = extract_interface(block, 'outbound-interface')
        src = extract_source(block)
        dst_addr, dst_port = extract_destination(block)
        proto = extract_protocol(block)
        # fallback: populate any missing fields from full config block
        full = get_full_rule_block(conf_text, rule_no)
        if full:
            action = action or extract_field(full, 'action')
            desc = desc or extract_field(full, 'description')
            in_if = in_if or extract_interface(full, 'inbound-interface')
            out_if = out_if or extract_interface(full, 'outbound-interface')
            src = src or extract_source(full)
            fdst, fport = extract_destination(full)
            dst_addr = dst_addr or fdst
            dst_port = dst_port or fport
            proto = proto or extract_protocol(full)
        # For forward table row we follow the column order used in vyos_documentation.tex
        # Rule & Action & Description & In & Out & Source & Destination & Port & Proto
        out.append((rule_no, f"{rule_no} & {action} & {latex_escape(desc)} & {in_if} & {out_if} & {src} & {dst_addr} & {dst_port} & {proto} \\\\") )
    # sort by rule_no
    out_sorted = [r for (_, r) in sorted(out, key=lambda x: x[0])]
    return out_sorted


def main():
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('v5.15.conf')
    text = cfg_path.read_text(encoding='utf-8')
    out_path = cfg_path.with_name('generated_firewall_tables.tex')
    parts = []
    def make_longtable(col_spec, header_titles, rows):
        hdr = []
        hdr.append(f"\\begin{{longtable}}{{{col_spec}}}")
        hdr.append('\\hline')
        hdr.append(' & '.join([f"\\textbf{{{t}}}" for t in header_titles]) + ' \\\\')
        hdr.append('\\hline')
        hdr.append('\\endfirsthead')
        hdr.append('\\hline')
        hdr.append(' & '.join([f"\\textbf{{{t}}}" for t in header_titles]) + ' \\\\')
        hdr.append('\\hline')
        hdr.append('\\endhead')
        # append rows
        hdr.extend(rows)
        hdr.append('\\hline')
        hdr.append('\\end{longtable}')
        return '\n'.join(hdr)

    # IPv4 DNAT (nat.destination)
    dnat_rows = gen_dnat_rows(text)
    dnat_table = make_longtable('|l|l|l|l|p{2.2cm}|l|l|', ['Pravilo','Opis','In','Destination','Port','Proto/Notes','Prevod / cilj'], dnat_rows)
    parts.append('% IPv4 DNAT from nat.destination')
    parts.append(dnat_table)

    # IPv4 SNAT (nat.source)
    snat_rows = gen_snat_rows(text)
    snat_table = make_longtable('|l|l|l|l|l|l|', ['Pravilo','Opis','Out','Source','Proto/Notes','Prevod / opomba'], snat_rows)
    parts.append('% IPv4 SNAT from nat.source')
    parts.append(snat_table)

    # IPv4 forward
    ipv4_forward = gen_firewall_table(text, 'ipv4', 'forward')
    ipv4_forward_table = make_longtable('|l|l|l|l|l|l|l|p{2.2cm}|l|', ['Rule','Action','Opis','In','Out','Source','Destination','Port','Proto/Notes'], ipv4_forward)
    parts.append('% IPv4 forward rules')
    parts.append(ipv4_forward_table)

    # IPv4 input
    ipv4_input = gen_firewall_table(text, 'ipv4', 'input')
    ipv4_input_table = make_longtable(
        '|l|l|l|l|l|l|p{2.2cm}|l|',
        ['Rule','Action','Opis','In','Source','Destination','Port','Proto/Notes'],
        ipv4_input
    )

    parts.append('% IPv4 input rules')
    parts.append(ipv4_input_table)

    # IPv4 output
    ipv4_output = gen_firewall_table(text, 'ipv4', 'output')
    ipv4_output_table = make_longtable(
        '|l|l|l|l|l|l|l|p{2.2cm}|l|',
        ['Rule','Action','Opis','In','Out','Source','Destination','Port','Proto/Notes'],
        ipv4_output
    )

    parts.append('% IPv4 output rules')
    parts.append(ipv4_output_table)


    # IPv6 forward
    ipv6_forward = gen_firewall_table(text, 'ipv6', 'forward')
    ipv6_forward_table = make_longtable('|l|l|l|l|l|l|l|p{2.2cm}|l|', ['Rule','Action','Opis','In','Out','Source','Destination','Port','Proto/Notes'], ipv6_forward)
    parts.append('% IPv6 forward rules')
    parts.append(ipv6_forward_table)

    # IPv6 input
    ipv6_input = gen_firewall_table(text, 'ipv6', 'input')
    ipv6_input_table = make_longtable(
        '|l|l|l|l|l|l|p{2.2cm}|l|',
        ['Rule','Action','Opis','In','Source','Destination','Port','Proto/Notes'],
        ipv6_input
    )

    parts.append('% IPv6 input rules')
    parts.append(ipv6_input_table)

    # IPv6 output
    ipv6_output = gen_firewall_table(text, 'ipv6', 'output')
    ipv6_output_table = make_longtable(
        '|l|l|l|l|l|l|l|p{2.2cm}|l|',
        ['Rule','Action','Opis','In','Out','Source','Destination','Port','Proto/Notes'],
        ipv6_output
    )

    parts.append('% IPv6 output rules')
    parts.append(ipv6_output_table)


    out_text = '\n\n'.join(parts)
    out_path.write_text(out_text, encoding='utf-8')
    print(f'Wrote {out_path}')

if __name__ == '__main__':
    main()
