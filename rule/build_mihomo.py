"""
只负责生成 mihomo 格式 (yaml + mrs)，写入 rule/mihomo/。
由 .github/workflows/mrs.yml 独立触发运行。

注意：如果 links.txt 里有 srs:/adguard: 类型的输入，这里依然需要调用
sing-box 做 decompile/convert 拿到中间格式，所以 mrs.yml 里也会装 sing-box，
但绝不会往 rule/singbox/ 写任何文件。
"""
import os
import concurrent.futures
import tempfile

import common

OUTPUT_DIR = "./mihomo"


def build_one(link, work_dir):
    try:
        name, unified = common.link_to_unified(link, work_dir)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，无法作为规则源导入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        unsupported = set(unified.keys()) - common.MIHOMO_MRS_SUPPORTED
        if unsupported:
            print(f"[提示] {name}: 以下规则类型 mihomo mrs 不支持，已跳过: {sorted(unsupported)}")

        domain_lines = sorted(unified.get('domain', set()))
        domain_lines += sorted('+.' + d.lstrip('.') for d in unified.get('domain_suffix', set()))
        ip_lines = sorted(unified.get('ip_cidr', set()))

        produced = False

        if domain_lines:
            yaml_path = os.path.join(OUTPUT_DIR, f"{name}.yaml")
            mrs_path = os.path.join(OUTPUT_DIR, f"{name}.mrs")
            common.yaml.safe_dump({'payload': domain_lines}, open(yaml_path, 'w', encoding='utf-8'),
                                   allow_unicode=True)
            common.run(["mihomo", "convert-ruleset", "domain", "yaml", yaml_path, mrs_path])
            produced = True

        if ip_lines:
            yaml_path_ip = os.path.join(OUTPUT_DIR, f"{name}-ip.yaml")
            mrs_path_ip = os.path.join(OUTPUT_DIR, f"{name}-ip.mrs")
            common.yaml.safe_dump({'payload': ip_lines}, open(yaml_path_ip, 'w', encoding='utf-8'),
                                   allow_unicode=True)
            common.run(["mihomo", "convert-ruleset", "ipcidr", "yaml", yaml_path_ip, mrs_path_ip])
            produced = True

        if produced:
            print(f"[完成] {link} -> mihomo/{name}.mrs")
        else:
            print(f"[跳过] {link}：没有 domain/domain_suffix/ip_cidr，未生成 mrs")
    except Exception as e:
        print(f"[出错] {link} 处理失败，已跳过，原因：{e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    links = common.read_links("../links.txt")
    with tempfile.TemporaryDirectory() as work_dir:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda l: build_one(l, work_dir), links))


if __name__ == '__main__':
    main()
