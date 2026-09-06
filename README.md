# Cloudflare IPv6 DDNS for Home Assistant

在 **PVE / HAOS** 上，将 Home Assistant 虚拟机自己的公网 IPv6 自动同步到 Cloudflare。中文界面，只填 **API Token + 完整域名**，不需要 YAML、脚本定时任务或手动找 Zone ID。

[通过 HACS 添加仓库](https://my.home-assistant.io/redirect/hacs_repository/?owner=PJUNYE2&repository=ha-cloudflare-ipv6-ddns&category=integration) · [安装后添加集成](https://my.home-assistant.io/redirect/config_flow_start/?domain=cloudflare_ipv6_ddns)

## 安装

1. 打开上方 HACS 链接，下载 **Cloudflare IPv6 DDNS**。或在 HACS 右上角 → 自定义存储库中添加 `https://github.com/PJUNYE2/ha-cloudflare-ipv6-ddns`，类别选 **集成 / Integration**，然后下载。
2. 重启 Home Assistant。
3. 设置 → 设备与服务 → 添加集成 → 搜索 **Cloudflare IPv6 DDNS**。
4. 填写 Token 和完整域名，例如 `ha.example.com`，提交即可。

这是可通过 **HACS 自定义仓库**安装的集成，尚未加入 HACS 默认商店。

要求 Home Assistant **2025.1+**，Linux 网络环境；主要面向 PVE 中桥接网络的 HAOS 虚拟机。HA 2026.3+ 支持显示随集成提供的本地图标。

## 创建 Cloudflare Token

在 [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens) 创建自定义 Token：

| 权限 | 用途 |
|---|---|
| Zone → Zone → Read（区域 → 区域 → 读取） | 自动查找 Zone ID |
| Zone → DNS → Edit（区域 → DNS → 编辑） | 读取、创建和更新 AAAA |

资源只授权你自己的目标域名。使用 API Token，**不要使用 Global API Key**。Token 仅保存在 HA 配置存储中；请保护 HA 备份，不要把 Token 提交到 GitHub。

## 默认行为

- 启动立即同步，每 **5 分钟**检查一次，网卡自动识别。
- 直接读取 HA Core 所在网络命名空间的网卡地址。标准 HAOS Core 使用宿主网络，因此获得的是 **HAOS 虚拟机**的 IPv6，不是 PVE 宿主机、路由器或出口查询网站返回的地址。
- 排除临时、弃用、未完成 DAD、DAD 失败、ULA 和链路本地地址；允许稳定隐私地址。
- 多个稳定地址时，优先保留当前 DNS 中仍有效的地址，减少切换。
- 找不到有效 IPv6、网络暂时断开时，保留原 DNS，稍后重试。
- 没有 AAAA 时创建；地址或代理选项变化时更新；已有记录的 TTL 和其他元数据保留。
- 每次读取 Cloudflare，能够纠正远端手动修改；没有变化时不写入。
- 同名 CNAME 或多个 AAAA 会报错，不会擅自删除。A、TXT 等其他记录不修改。
- 默认设为 **DNS only（灰云）**，包括已有橙云 AAAA。建议使用专用子域名。
- 卸载或删除集成条目不会删除 Cloudflare 上的 DNS 记录。

## 可视化管理

设备页提供：**IPv6 地址**、**最近成功同步**和**立即同步**按钮。IPv6 实体属性包括网卡、同步结果及本次运行以来最近修改时间。同步失败时传感器显示不可用，HA 日志提供原因。

集成的“配置”中可修改：检查间隔（1–60 分钟）、HAOS 网卡名和橙云代理开关。留空网卡即自动；多网卡/策略路由可手动指定，例如 `enp0s18`。不要填 PVE 的 `vmbr0`，除非该接口确实存在于 HAOS 内。

集成菜单的“重新配置”可更换 Token。Token 失效时 HA 会提示重新认证。每个域名添加一条集成，可管理多个域名。即使禁用所有实体，集成的定时同步仍会继续；需要停止同步请禁用集成条目。

## 网络前提

HAOS 必须获得公网 IPv6；仅 PVE 有 IPv6 不够。PVE 网卡通常桥接 LAN，路由器应向 HAOS 下发 IPv6，HA 系统网络中的 IPv6 通常设为自动。

DDNS 不配置路由器/PVE 防火墙、HTTPS 或端口转发。外部访问需放行到 HAOS 对应服务端口，建议配置 HTTPS。纯 AAAA 直连要求客户端支持 IPv6。Cloudflare 普通橙云不支持 HA 默认的 8123 端口；启用橙云需使用其支持的端口和合适的 TLS 配置。若同名旧 A 记录指向其他机器，双栈客户端可能访问错误地址，需要自行处理。

## 开发与验证

```sh
python -m pip install aiohttp pytest pytest-asyncio ruff
python -m pytest tests
ruff check custom_components tests
ruff format --check custom_components tests
```

单元测试覆盖 IPv6 筛选、网卡选择、前缀变化、Cloudflare 状态和记录冲突。GitHub Actions 另外执行 Home Assistant 运行时测试及 hassfest / HACS 校验。模拟测试不代表已在你的实际 HAOS 和 Cloudflare 账户上验证连通性。

## 参考

- [HA 配置流程](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [HACS 集成规范](https://hacs.xyz/docs/publish/integration/)
- [Cloudflare DNS API](https://developers.cloudflare.com/api/resources/dns/subresources/records/)
- [Cloudflare 支持的代理端口](https://developers.cloudflare.com/fundamentals/reference/network-ports/)

Independent community integration; not affiliated with Cloudflare or Home Assistant.
