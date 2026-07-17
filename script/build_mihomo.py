import os
import concurrent.futures
import tempfile

import common

# 三个来源统一处理：每条链接不论写在哪个文件里，都会按自身实际包含的
# 字段自动拆成 domain / ip 两部分，分别写入 mihomo/<name>/ 下
LINKS_FILES = [
    "../links/links-domain.txt",
    "../links/links-ipcidr.txt",
    "../links/links-mixed.txt",
    "../links/links-meta.txt",
]

OUTPUT_ROOT = "../rule/mihomo"


def build_domain_files(filtered, name, out_dir):
    domain_lines = sorted(filtered.get('domain', set()))
    domain_lines += sorted('+.' + d.lstrip('.') for d in filtered.get('domain_suffix', set()))
    if not domain_lines:
        return False
    os.makedirs(out_dir, exist_ok=True)
    yaml_path = os.path.join(out_dir, f"{name}_Domain.yaml")
    mrs_path = os.path.join(out_dir, f"{name}_Domain.mrs")
    common.yaml.safe_dump({'payload': domain_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "domain", "yaml", yaml_path, mrs_path])
    return True


def build_ip_files(filtered, name, out_dir):
    ip_lines = sorted(filtered.get('ip_cidr', set()))
    if not ip_lines:
        return False
    os.makedirs(out_dir, exist_ok=True)
    yaml_path = os.path.join(out_dir, f"{name}_IP.yaml")
    mrs_path = os.path.join(out_dir, f"{name}_IP.mrs")
    common.yaml.safe_dump({'payload': ip_lines}, open(yaml_path, 'w', encoding='utf-8'), allow_unicode=True)
    common.run(["mihomo", "convert-ruleset", "ipcidr", "yaml", yaml_path, mrs_path])
    return True


def build_one(name_link, work_dir):
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
            print(f"[提示] {name}: 以下字段既不算域名也不算IP，已跳过: {leftover}")

        mrs_unsupported = set(domain_part.keys()) - common.MIHOMO_MRS_SUPPORTED
        if mrs_unsupported:
            print(f"[提示] {name}: 以下字段 mihomo mrs 不支持，已跳过: {sorted(mrs_unsupported)}")

        out_dir = os.path.join(OUTPUT_ROOT, name)
        wrote = []
        if build_domain_files(domain_part, name, out_dir):
            wrote.append("Domain")
        if build_ip_files(ipcidr_part, name, out_dir):
            wrote.append("IP")

        if wrote:
            print(f"[完成] {link} -> mihomo/{name}/ ({','.join(wrote)})")
        else:
            print(f"[跳过] {link}：过滤后没有可生成 mrs 的规则")
    except Exception as e:
        print(f"[出错] {link} 处理失败，已跳过，原因：{e}")


def main():
    with tempfile.TemporaryDirectory() as work_dir:
        os.makedirs(OUTPUT_ROOT, exist_ok=True)

        all_links = []
        for links_path in LINKS_FILES:
            all_links.extend(common.read_links(links_path))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda nl: build_one(nl, work_dir), all_links))


if __name__ == '__main__':
    main()
