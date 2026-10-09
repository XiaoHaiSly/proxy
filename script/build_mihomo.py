import os
import concurrent.futures
import tempfile
from collections import defaultdict

import common

RULES_LINKS_FILES = [
    "../links/links-domain.txt",
    "../links/links-ipcidr.txt",
    "../links/links-mixed.txt",
]
RULES_OUTPUT_ROOT = "../rules/mihomo"


def build_domain_files(filtered, name, out_dir):
    domain_lines = sorted(filtered.get('domain', set()))
    domain_lines += sorted('+.' + d.lstrip('.') for d in filtered.get('domain_suffix', set()))
    if not domain_lines:
        return False
    os.makedirs(out_dir, exist_ok=True)
    yaml_path = os.path.join(out_dir, f"{name}.yaml")
    mrs_path = os.path.join(out_dir, f"{name}.mrs")
    common.yaml.safe_dump({'payload': domain_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "domain", "yaml", yaml_path, mrs_path])
    return True


def build_ip_files(filtered, name, out_dir):
    ip_lines = sorted(filtered.get('ip_cidr', set()))
    if not ip_lines:
        return False
    os.makedirs(out_dir, exist_ok=True)
    yaml_path = os.path.join(out_dir, f"{name}.yaml")
    mrs_path = os.path.join(out_dir, f"{name}.mrs")
    common.yaml.safe_dump({'payload': ip_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "ipcidr", "yaml", yaml_path, mrs_path])
    return True


def merge_unified(unified_list):
    merged = {}
    for unified in unified_list:
        for key, values in unified.items():
            merged.setdefault(key, set()).update(values)
    return merged


def group_links(links_files):
    """Group by name. Multiple sources with the same name (e.g. geosite+geoip) are merged
    to avoid multiple threads writing to the same output directory at the same time.
    """
    groups = defaultdict(list)
    for links_path in links_files:
        for custom_name, link in common.read_links(links_path):
            kind, url = common.detect_source(link)
            name = custom_name or common.base_name(url)
            groups[name].append(link)
    return groups


def build_group(name, links, work_dir, output_root):
    unified_list = []
    for link in links:
        try:
            _, unified = common.link_to_unified(link, work_dir, name)
        except Exception as e:
            print(f"[Error] Failed to process {link}, skipped. Reason: {e}")
            continue

        if unified == 'UNSUPPORTED':
            print(f"[Skip] {link}: mihomo does not provide an official MRS reverse conversion tool, so it cannot be imported as a rule source")
            continue
        if not unified:
            print(f"[Skip] {link}: no rules were parsed")
            continue
        if name in ('google', 'twitter'):
            print(f"[Debug] {name} <- {link} parsed fields: { {k: len(v) for k, v in unified.items()} }")
        unified_list.append(unified)

    if not unified_list:
        return

    unified = merge_unified(unified_list)
    domain_part, ipcidr_part, leftover = common.split_mixed_unified(unified)
    if leftover:
        print(f"[Info] {name}: the following fields are neither domain nor IP and were skipped: {leftover}")

    mrs_unsupported = set(domain_part.keys()) - common.MIHOMO_MRS_SUPPORTED
    if mrs_unsupported:
        print(f"[Info] {name}: the following fields are not supported by mihomo MRS and were skipped: {sorted(mrs_unsupported)}")

    domain_dir = os.path.join(output_root, "domain")
    ipcidr_dir = os.path.join(output_root, "ipcidr")
    wrote = []
    if build_domain_files(domain_part, name, domain_dir):
        wrote.append("Domain")
    if build_ip_files(ipcidr_part, name, ipcidr_dir):
        wrote.append("IP")

    if wrote:
        print(f"[Done] {name} -> {output_root}/{{domain,ipcidr}}/ ({','.join(wrote)}), total {len(links)} source(s)")
    else:
        print(f"[Skip] {name}: no rules left to generate MRS after filtering")


def run_group(links_files, output_root, work_dir):
    os.makedirs(output_root, exist_ok=True)
    groups = group_links(links_files)

    multi = {name: len(links) for name, links in groups.items() if len(links) > 1}
    print(f"[Group Stats] {output_root}: {len(groups)} names, {len(multi)} with multiple sources")
    if 'google' in groups:
        print(f"[Group Stats] google sources: {groups['google']}")
    if 'twitter' in groups:
        print(f"[Group Stats] twitter sources: {groups['twitter']}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(
            lambda item: build_group(item[0], item[1], work_dir, output_root),
            groups.items(),
        ))


def main():
    with tempfile.TemporaryDirectory() as work_dir:
        run_group(RULES_LINKS_FILES, RULES_OUTPUT_ROOT, work_dir)


if __name__ == '__main__':
    main()
