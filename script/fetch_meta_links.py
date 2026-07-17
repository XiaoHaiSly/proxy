import os
import requests

REPO = "MetaCubeX/meta-rules-dat"
BRANCH = "meta"
DIRS = ["geo/geosite", "geo/geoip"]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "links", "links-meta.txt")

HEADERS = {"User-Agent": "Mozilla/5.0"}
_token = os.environ.get("GITHUB_TOKEN")
if _token:
    HEADERS["Authorization"] = f"token {_token}"


def list_yaml_files(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    items = resp.json()
    return [
        item["name"] for item in items
        if item.get("type") == "file" and item["name"].lower().endswith((".yaml", ".yml"))
    ]


def main():
    lines = []
    for d in DIRS:
        files = list_yaml_files(d)
        print(f"[{d}] 发现 {len(files)} 个 yaml 文件")
        for fname in files:
            name = fname.rsplit(".", 1)[0]
            raw_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{d}/{fname}"
            lines.append(f"{name} {raw_url}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# 自动生成，来自 MetaCubeX/meta-rules-dat（geo/geosite + geo/geoip），请勿手动编辑\n")
        f.write("\n".join(lines) + "\n")

    print(f"共写入 {len(lines)} 条链接 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
