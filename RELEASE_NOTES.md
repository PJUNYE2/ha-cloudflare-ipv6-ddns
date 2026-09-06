# 1.0.0

- 中文和英文配置界面：输入 API Token 与域名即可。
- 自动识别 Zone ID 和 HAOS 本机的稳定公网 IPv6。
- 定时同步 Cloudflare AAAA，支持手动同步、地址与最近同步时间实体。
- 支持重新认证、Token 更换、网卡指定和代理选项。
- 无 IPv6、网络中断或记录冲突时保留原解析。

安装：将本仓库作为 HACS 自定义仓库添加，类别选择 Integration，下载并重启 Home Assistant，然后添加 Cloudflare IPv6 DDNS 集成。
