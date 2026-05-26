# Changelog

## v1.0.0 (2026-05-26)

- 初始版本
- 自然语言触发文生图，无需 `/` 前缀
- 支持阿里云百炼 DashScope 全系列生图模型（qwen-image-2.0-pro / qwen-image-2.0 / qwen-image-plus / wan2.6-t2i / wanx-v1）
- 支持豆包 Seedream 4.0
- 同步调用模式，兼容所有 DashScope API Key 类型
- Prompt 比例识别（16:9 / 1:1 / 9:16 等）
- 随机种子机制，避免图片雷同
- LLM Agent 工具注册（draw_image），支持 Agent 自动调用
- AstrBot 管理后台可视化配置