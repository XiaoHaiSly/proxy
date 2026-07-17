import os
import concurrent.futures
import tempfile

import common

CATEGORIES = [
    ("../links-domain.txt", "./singbox/domain", common.DOMAIN_FIELDS, "domain"),
    ("../links-ipcidr.txt", "./singbox/ipcidr", common.IPCIDR_FIELDS, "ipcidr"),
]

MIXED_LINKS_PATH = "../links-mixed.txt"
DOMAIN_OUTPUT_DIR = "./singbox/domain"
IPCIDR_OUTPUT_DIR = "./singbox/ipcidr"


def write_singbox(filtered, name, output_dir):
    json_path = os.path.join(output_dir, f"{name}.json")
    srs_path = os.path.join(output_dir, f"{name}.srs")
    common.unified_to_singbox_json(filtered, json_path)
    common.run(["sing-box", "rule-set", "compile", "--output", srs_path, json_path])


def build_one(name_link, work_dir, output_dir, keep_fields, category_label):
    custom_name, link = name_link
    try:
        name, unified = common.link_to_unified(link, work_dir, custom_name)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，srs.yml 无法处理此输入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        filtered, dropped = common.filter_unified(unified, keep_fields)
        if dropped:
            print(f"[提示] {name} ({category_label}): 忽略了不属于此分类的字段 {dropped}，如需保留请把此链接也加进对应的 links-*.txt")
        if not filtered:
            print(f"[跳过] {link}：过滤后没有属于 {category_label} 分类的规则")
            return

        write_singbox(filtered, name, output_dir)
        print(f"[完成] {link} -> singbox/{category_label}/{name}.json + .srs")
    except Exception as e:
        print(f"[出错] {link} 处理失败，已跳过，原因：{e}")


def build_one_mixed(name_link, work_dir):
    custom_name, link = name_link
    try:
        name, unified = common.link_to_unified(link, work_dir, custom_name)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，srs.yml 无法处理此输入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        domain_part, ipcidr_part, leftover = common.split_mixed_unified(unified)
        if leftover:
            print(f"[提示] {name} (mixed): 以下字段既不算域名也不算IP，两边都不会写: {leftover}")

        wrote = []
        if domain_part:
            write_singbox(domain_part, name, DOMAIN_OUTPUT_DIR)
            wrote.append("domain")
        if ipcidr_part:
            write_singbox(ipcidr_part, name, IPCIDR_OUTPUT_DIR)
            wrote.append("ipcidr")

        if wrote:
            print(f"[完成] {link} (mixed) -> singbox/{{{','.join(wrote)}}}/{name}.json + .srs")
        else:
            print(f"[跳过] {link}：识别不出域名或IP规则")
    except Exception as e:
        print(f"[出错] {link} 处理失败，已跳过，原因：{e}")


def main():
    with tempfile.TemporaryDirectory() as work_dir:
        for links_path, output_dir, keep_fields, category_label in CATEGORIES:
            os.makedirs(output_dir, exist_ok=True)
            links = common.read_links(links_path)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(
                    lambda nl: build_one(nl, work_dir, output_dir, keep_fields, category_label),
                    links
                ))

        os.makedirs(DOMAIN_OUTPUT_DIR, exist_ok=True)
        os.makedirs(IPCIDR_OUTPUT_DIR, exist_ok=True)
        mixed_links = common.read_links(MIXED_LINKS_PATH)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda nl: build_one_mixed(nl, work_dir), mixed_links))


if __name__ == '__main__':
    main()
