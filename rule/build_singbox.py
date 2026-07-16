"""
只负责生成 sing-box 格式 (json + srs)，写入 rule/singbox/。
由 .github/workflows/srs.yml 独立触发运行，不涉及 mihomo。
"""
import os
import concurrent.futures
import tempfile

import common

OUTPUT_DIR = "./singbox"


def build_one(link, work_dir):
    try:
        name, unified = common.link_to_unified(link, work_dir)

        if unified == 'UNSUPPORTED':
            print(f"[跳过] {link}：mihomo 官方未提供 mrs 反解工具，srs.yml 无法处理此输入")
            return
        if not unified:
            print(f"[跳过] {link}：未解析出任何规则")
            return

        json_path = os.path.join(OUTPUT_DIR, f"{name}.json")
        srs_path = os.path.join(OUTPUT_DIR, f"{name}.srs")
        common.unified_to_singbox_json(unified, json_path)
        common.run(["sing-box", "rule-set", "compile", "--output", srs_path, json_path])
        print(f"[完成] {link} -> singbox/{name}.json + .srs")
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
