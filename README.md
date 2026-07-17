Rule Feed

自动抓取、转换并发布代理规则集。

支持生成：

- Mihomo / Clash Meta
  
  - YAML
  - MRS(rule-set)

- sing-box
  
  - JSON
  - SRS(rule-set)

项目通过 GitHub Actions 自动执行规则抓取、转换和发布，可用于 Mihomo、Clash Meta、sing-box 等客户端。

功能特点

- 自动拉取远程规则源
- 支持域名规则和 IP-CIDR 规则
- 自动转换不同客户端格式
- 支持自定义规则源
- GitHub Actions 自动构建
- 支持 Cloudflare Pages 自动部署

使用方式

添加或修改规则源配置文件，填入需要转换的规则链接。

提交代码后，GitHub Actions 会自动执行：

1. 拉取规则数据
2. 解析规则内容
3. 生成 Mihomo / sing-box rule-set
4. 发布生成文件

同时支持手动运行 GitHub Actions。

Cloudflare Pages 部署

如果需要自动发布到 Cloudflare Pages，需要在 GitHub 仓库：

Settings → Secrets and variables → Actions

添加以下变量：

CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_PROJECT_NAME

变量说明：

变量| 作用
CLOUDFLARE_API_TOKEN| Cloudflare API Token，用于授权部署
CLOUDFLARE_ACCOUNT_ID| Cloudflare 账户 ID
CLOUDFLARE_PROJECT_NAME| Cloudflare Pages 项目名称

完成配置后，GitHub Actions 会自动将生成的规则文件部署到 Cloudflare Pages。

注意事项

- Mihomo MRS 格式不支持反解。

支持客户端

- Mihomo
- Clash Meta
- sing-box

生成后的规则文件可直接用于：

- rule-providers
- rule-set

License

MIT
