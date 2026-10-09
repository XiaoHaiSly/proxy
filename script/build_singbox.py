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
RULES_OUTPUT_ROOT = "../rules/singbox"


def write_domain(filtered, name, out_dir):
    if not filtered:
        return False
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{name}.json")
    srs_path = os.path.join(out_dir, f"{name}.srs")
    common.unified_to_singbox_json(filtered, json_path)
    common.run(["sing-box", "rule-set", "compile", "--output", srs_path, json_path])
    return True


def write_ip(filtered, name, out_dir):
    if not filtered:
        return False
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{name}.json")
    srs_path = os.path.join(out_dir, f"{name}.srs")
    common.unified_to_singbox_json(filtered, json_path)
    common.run(["sing-box", "rule-set", "compile", "--output", srs_path, json_path])
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
            print(f"[Skip] {link}: mihomo does not provide an official MRS reverse conversion tool, srs cannot handle this input")
            continue
        if not unified:
            print(f"[Skip] {link}: no rules were parsed")
            continue
        unified_list.append(unified)

    if not unified_list:
        return

    unified = merge_unified(unified_list)
    domain_part, ipcidr_part, leftover = common.split_mixed_unified(unified)
    if leftover:
        print(f"[Info] {name}: the following fields are neither domain nor IP and were skipped: {leftover}")

    domain_dir = os.path.join(output_root, "domain")
    ipcidr_dir = os.path.join(output_root, "ipcidr")
    wrote = []
    if write_domain(domain_part, name, domain_dir):
        wrote.append("Domain")
    if write_ip(ipcidr_part, name, ipcidr_dir):
        wrote.append("IP")

    if wrote:
        print(f"[Done] {name} -> {output_root}/{{domain,ipcidr}}/ ({','.join(wrote)}), total {len(links)} source(s)")
    else:
        print(f"[Skip] {name}: no domain or IP rules could be recognized")


def run_group(links_files, output_root, work_dir):
    os.makedirs(output_root, exist_ok=True)
    groups = group_links(links_files)

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
