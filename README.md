# rOB0t - QQ TeamSpeak 服务器状态查询机器人

这是一个轻量级的 Python 机器人脚本（`qq_ts_bot.py`），用于在 **QQ 群聊或私聊中实时查询 TeamSpeak (TS) 服务器状态**（如在线人数、频道信息等）。

> [!NOTE]
> 本项目接入的是**非官方 QQ 个人号协议**（基于 OneBot 11 标准），无需申请腾讯官方 QQ 机器人接口即可部署使用。

## 前置依赖（运行必要前提）

> 运行 `qq_ts_bot.py` 前，必须提前部署并配置好以下 **3 个核心组件/插件**，缺少任意一项脚本均无法正常收发消息：

1. **NapCat (NapCatQQ)**：非官方 QQ 协议端，负责登录 QQ 账号并将消息事件通过 HTTP 推送至本地端口。
2. **Shell (NapCat.Shell 运行环境)**：用于承载与运行无头版 NapCat 服务及后台守护进程。
3. **Flask**：Python 轻量级 Web 框架，脚本通过它监听 NapCat 转发的 QQ 消息事件并触发查询逻辑。
