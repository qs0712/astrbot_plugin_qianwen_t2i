# Changelog

## v1.1.0 (2026-05-26)

- 新增 `draw_image` LLM Tool 注册，Agent 可自动调用生图
- 新增尺寸格式强制兜底：DashScope 自动纠正为 `*` 分隔，Seedream 自动纠正为 `x` 分隔
- 修复配置中尺寸分隔符不匹配导致的 HTTP 400 错误
- 默认比例改为 4:3（百炼 2048\*1536 / Seedream 2048x1536）
- 提示词中的比例关键词（如 `16:9`）优先级高于配置框默认值
- 作者改为 吃不饱的小乔

## v1.0.0 (2026-05-26)

- 初始版本
- 自然语言触发文生图，无需 `/` 前缀
- 支持阿里云百炼 DashScope 全系列生图模型（qwen-image-2.0-pro / qwen-image-2.0 / qwen-image-plus / wan2.6-t2i / wanx-v1）
- 支持豆包 Seedream 4.0
- 同步调用模式，兼容所有 DashScope API Key 类型
- Prompt 比例识别（16:9 / 1:1 / 9:16 等）
- 随机种子机制，避免图片雷同
- AstrBot 管理后台可视化配置