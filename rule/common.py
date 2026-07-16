"""
共享解析库。

build_singbox.py 和 build_mihomo.py 都从这里导入，
两者各自独立运行、各自只负责写自己的输出目录，互不依赖。

统一中间格式:
    unified: dict[str, set[str]]
    key 是 sing-box 字段名 (domain / domain_suffix / domain_keyword /
        domain_regex / ip_cidr / source_ip_cidr / port / source_port / geoip)
    value 是该类型下的地址集合
"""
import pandas as pd
import os
import json
import requests
import yaml
import ipaddress
import subprocess
from io import StringIO

MAP_DICT = {'DOMAIN-SUFFIX': 'domain_suffix', 'HOST-SUFFIX': 'domain_suffix', 'host-suffix': 'domain_suffix',
            'DOMAIN': 'domain', 'HOST': 'domain', 'host': 'domain',
            'DOMAIN-KEYWORD': 'domain_keyword', 'HOST-KEYWORD': 'domain_keyword', 'host-keyword': 'domain_keyword',
            'IP-CIDR': 'ip_cidr', 'ip-cidr': 'ip_cidr', 'IP-CIDR6': 'ip_cidr', 'IP6-CIDR': 'ip_cidr',
            'SRC-IP-CIDR': 'source_ip_cidr', 'GEOIP': 'geoip', 'DST-PORT': 'port',
            'SRC-PORT': 'source_port', "URL-REGEX": "domain_regex", "DOMAIN-REGEX": "domain_regex"}

# mihomo mrs 目前只支持这两种 behavior，其余类型只能留在 srs/json 里
MIHOMO_MRS_SUPPORTED = {'domain', 'domain_suffix', 'ip_cidr'}

HEADERS = {'User-Agent': 'Mozilla/5.0'}


# ------------------------------------------------------------
# 输入类型识别: 支持前缀协议强制指定，或按扩展名自动判断
#   srs:<url>       -> sing-box 二进制规则集，走 decompile（需要 sing-box）
#   json:<url>       -> sing-box source json，直接读
#   mrs:<url>         -> mihomo 二进制，官方无反解工具，直接跳过并警告
#   adguard:<url>     -> AdGuard filter 文本，走 sing-box convert --type adguard（需要 sing-box）
#   不带前缀        -> 按扩展名 .srs/.json/.mrs 自动判断，其余一律走文本/yaml解析
# ------------------------------------------------------------
def detect_source(link):
    for prefix in ('srs:', 'json:', 'mrs:', 'adguard:'):
        if link.startswith(prefix):
            return prefix[:-1], link[len(prefix):]
    lower = link.lower()
    if lower.endswith('.srs'):
        return 'srs', link
    if lower.endswith('.mrs'):
        return 'mrs', link
    if lower.endswith('.json'):
        return 'json', link
    return 'text', link


def base_name(link):
    name = os.path.basename(link.split('?')[0])
    for ext in ('.srs', '.mrs', '.json', '.yaml', '.yml', '.list', '.txt', '.conf'):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break
    return name or 'rule'


def read_links(links_path="../links.txt"):
    with open(links_path, 'r', encoding='utf-8') as f:
        links = f.read().splitlines()
    return [l.strip() for l in links if l.strip() and not l.strip().startswith('#')]


def download_to_file(url, path):
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    with open(path, 'wb') as f:
        f.write(resp.content)


def run(cmd):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result


# ------------------------------------------------------------
# 文本规则源解析 (clash yaml / surge list / quantumultx list / 纯域名文本)
# ------------------------------------------------------------
def read_yaml_from_url(url):
    return yaml.safe_load(requests.get(url, headers=HEADERS, timeout=60).text)


def read_list_from_url(url):
    response = requests.get(url, headers=HEADERS, timeout=60)
    if response.status_code != 200:
        return None
    csv_data = StringIO(response.text)
    df = pd.read_csv(csv_data, header=None, names=['pattern', 'address', 'other', 'other2', 'other3'],
                      on_bad_lines='skip')
    filtered_rows = [row for _, row in df.iterrows() if 'AND' not in str(row['pattern'])]
    return pd.DataFrame(filtered_rows, columns=['pattern', 'address', 'other', 'other2', 'other3'])


def is_ipv4_or_ipv6(address):
    try:
        ipaddress.IPv4Network(address)
        return 'ipv4'
    except ValueError:
        try:
            ipaddress.IPv6Network(address)
            return 'ipv6'
        except ValueError:
            return None


def parse_and_convert_to_dataframe(link):
    if link.endswith('.yaml') or link.endswith('.yml') or link.endswith('.txt'):
        try:
            yaml_data = read_yaml_from_url(link)
            rows = []
            if not isinstance(yaml_data, str):
                items = yaml_data.get('payload', [])
            else:
                items = yaml_data.splitlines()[0].split()
            for item in items:
                address = item.strip("'")
                if ',' not in item:
                    if is_ipv4_or_ipv6(item):
                        pattern = 'IP-CIDR'
                    elif address.startswith('+') or address.startswith('.'):
                        pattern = 'DOMAIN-SUFFIX'
                        address = address[1:]
                        if address.startswith('.'):
                            address = address[1:]
                    else:
                        pattern = 'DOMAIN'
                else:
                    pattern, address = item.split(',', 1)
                if ',' in address:
                    address = address.split(',', 1)[0]
                rows.append({'pattern': pattern.strip(), 'address': address.strip(), 'other': None})
            return pd.DataFrame(rows, columns=['pattern', 'address', 'other'])
        except Exception:
            return read_list_from_url(link)
    return read_list_from_url(link)


def text_source_to_unified(link):
    df = parse_and_convert_to_dataframe(link)
    if df is None or df.empty:
        return None
    df = df[~df['pattern'].astype(str).str.contains('#', na=False)].reset_index(drop=True)
    df = df[df['pattern'].isin(MAP_DICT.keys())].reset_index(drop=True)
    df = df.drop_duplicates().reset_index(drop=True)
    df['pattern'] = df['pattern'].replace(MAP_DICT)

    unified = {}
    for pattern, addresses in df.groupby('pattern')['address'].apply(list).to_dict().items():
        unified.setdefault(pattern, set()).update(a.strip() for a in addresses)
    return unified


# ------------------------------------------------------------
# sing-box json <-> unified （需要 sing-box 二进制的分支都在这里）
# ------------------------------------------------------------
def singbox_json_to_unified(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    unified = {}
    for rule in data.get('rules', []):
        if 'type' in rule:  # 跳过 logical rule，两边都不支持这种组合规则
            continue
        for key, values in rule.items():
            if isinstance(values, list):
                unified.setdefault(key, set()).update(str(v) for v in values)
    return unified


def unified_to_singbox_json(unified, json_path):
    result_rules = {"version": 2, "rules": []}
    for pattern in sorted(unified.keys()):
        addresses = sorted(unified[pattern])
        if addresses:
            result_rules["rules"].append({pattern: addresses})
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result_rules, f, ensure_ascii=False, indent=2)


def srs_url_to_unified(url, work_dir, name):
    srs_path = os.path.join(work_dir, f"{name}.srs")
    json_path = os.path.join(work_dir, f"{name}.decompiled.json")
    download_to_file(url, srs_path)
    run(["sing-box", "rule-set", "decompile", "--output", json_path, srs_path])
    return singbox_json_to_unified(json_path)


def json_url_to_unified(url, work_dir, name):
    json_path = os.path.join(work_dir, f"{name}.src.json")
    download_to_file(url, json_path)
    return singbox_json_to_unified(json_path)


def adguard_url_to_unified(url, work_dir, name):
    txt_path = os.path.join(work_dir, f"{name}.adguard.txt")
    json_path = os.path.join(work_dir, f"{name}.adguard.json")
    srs_tmp = os.path.join(work_dir, f"{name}.adguard.srs")
    download_to_file(url, txt_path)
    # sing-box convert --type adguard 只能直接产出 srs，没有 source json 选项
    # 所以先转成 srs 再 decompile 回 json，绕一圈换取统一中间格式
    run(["sing-box", "rule-set", "convert", "--type", "adguard", "--output", srs_tmp, txt_path])
    run(["sing-box", "rule-set", "decompile", "--output", json_path, srs_tmp])
    return singbox_json_to_unified(json_path)


def link_to_unified(link, work_dir):
    """把一条 link 解析成 (name, unified) 或 (name, None)。
    kind == 'mrs' 时返回 (name, 'UNSUPPORTED')，调用方据此打印跳过信息。"""
    kind, url = detect_source(link)
    name = base_name(url)

    if kind == 'mrs':
        return name, 'UNSUPPORTED'

    if kind == 'srs':
        unified = srs_url_to_unified(url, work_dir, name)
    elif kind == 'json':
        unified = json_url_to_unified(url, work_dir, name)
    elif kind == 'adguard':
        unified = adguard_url_to_unified(url, work_dir, name)
    else:
        unified = text_source_to_unified(url)

    return name, unified
