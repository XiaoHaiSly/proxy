"""
只负责生成 mihomo 格式 (yaml + mrs)，写入 rule/mihomo/domain/ 和 rule/mihomo/ipcidr/。
由 .github/workflows/mrs.yml 独立触发运行。

- ../links-domain.txt  只提取 domain/domain_suffix (domain_keyword/domain_regex 仍不被 mrs 支持)
  -> 写到 mihomo/domain/
- ../links-ipcidr.txt  只提取 ip_cidr (source_ip_cidr 不被 mrs 支持)
  -> 写到 mihomo/ipcidr/
- ../links-mixed.txt   不预设类型，自动检测：纯域名只写 domain/，纯IP只写 ipcidr/，
  两者都有就两边各写一份。

注意：如果 links-*.txt 里有 srs:/adguard: 类型的输入，这里依然需要调用
sing-box 做 decompile/convert 拿到中间格式，所以 mrs.yml 里也会装 sing-box，
但绝不会往 rule/singbox/ 写任何文件。
"""
import os
import concurrent.futures
import tempfile

import common

CATEGORIES = [
    ("../links-domain.txt", "./mihomo/domain", common.DOMAIN_FIELDS, "domain"),
    ("../links-ipcidr.txt", "./mihomo/ipcidr", common.IPCIDR_FIELDS, "ipcidr"),
]

MIXED_LINKS_PATH = "../links-mixed.txt"
DOMAIN_OUTPUT_DIR = "./mihomo/domain"
IPCIDR_OUTPUT_DIR = "./mihomo/ipcidr"


def build_domain_mrs(filtered, name, output_dir):
    domain_lines = sorted(filtered.get('domain', set()))
    domain_lines += sorted('+.' + d.lstrip('.') for d in filtered.get('domain_suffix', set()))
    if not domain_lines:
        return False
    yaml_path = os.path.join(output_dir, f"{name}.yaml")
    mrs_path = os.path.join(output_dir, f"{name}.mrs")
    common.yaml.safe_dump({'payload': domain_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "domain", "yaml", yaml_path, mrs_path])
    return True


def build_ipcidr_mrs(filtered, name, output_dir):
    ip_lines = sorted(filtered.get('ip_cidr', set()))
    if not ip_lines:
        return False
    yaml_path = os.path.join(output_dir, f"{name}.yaml")
    mrs_path = os.path.join(output_dir, f"{name}.mrs")
    common.yaml.safe_dump({'payload': ip_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "ipcidr", "yaml", yaml_path, mrs_path])
    return True


def build_one(name_link, work_dir, output_dir, keep_fields, category_label):
    custom_name, link = name_link
    try:
        name, unified = common.link_to_unified(link, work_dir, custom_name)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，无法作为规则源导入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        filtered, dropped = common.filter_unified(unified, keep_fields)
        if dropped:
            print(f"[提示] {name} ({category_label}): 忽略了不属于此分类的字段 {dropped}，"
                  f"如需保留请把此链接也加进对应的 links-*.txt")

        mrs_unsupported = set(filtered.keys()) - common.MIHOMO_MRS_SUPPORTED
        if mrs_unsupported:
            print(f"[提示] {name} ({category_label}): 以下字段 mihomo mrs 不支持，已跳过: {sorted(mrs_unsupported)}")

        if category_label == "domain":
            produced = build_domain_mrs(filtered, name, output_dir)
        else:
            produced = build_ipcidr_mrs(filtered, name, output_dir)

        if produced:
            print(f"[完成] {link} -> mihomo/{category_label}/{name}.mrs")
        else:
            print(f"[跳过] {link}：过滤后没有可生成 mrs 的规则")
    except Exception as e:
        print(f"[出错] {link} 处理失败，已跳过，原因：{e}")


def build_one_mixed(name_link, work_dir):
    custom_name, link = name_link
    try:
        name, unified = common.link_to_unified(link, work_dir, custom_name)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，无法作为规则源导入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        domain_part, ipcidr_part, leftover = common.split_mixed_unified(unified)
        if leftover:
            print(f"[提示] {name} (mixed): 以下字段既不算域名也不算IP，两边都不会写: {leftover}")

        mrs_unsupported = set(domain_part.keys()) - common.MIHOMO_MRS_SUPPORTED
        if mrs_unsupported:
            print(f"[提示] {name} (mixed/domain): 以下字段 mihomo mrs 不支持，已跳过: {sorted(mrs_unsupported)}")

        wrote = []
        if build_domain_mrs(domain_part, name, DOMAIN_OUTPUT_DIR):
            wrote.append("domain")
        if build_ipcidr_mrs(ipcidr_part, name, IPCIDR_OUTPUT_DIR):
            wrote.append("ipcidr")

        if wrote:
            print(f"[完成] {link} (mixed) -> mihomo/{{{','.join(wrote)}}}/{name}.mrs")
        else:
            print(f"[跳过] {link}：过滤后没有可生成 mrs 的规则")
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
