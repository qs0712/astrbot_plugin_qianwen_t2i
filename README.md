# astrbot_plugin_qianwen_t2i — 自然语言文生图插件

直接通过自然语言触发文生图，无需记忆任何指令。支持阿里云百炼 DashScope 全系列生图模型和豆包 Seedream。

## 功能

- **自然语言触发** — 说「帮我画一只小猫」即可生成图片，无需 `/` 前缀
- **百炼全模型支持** — qwen-image-2.0-pro / qwen-image-2.0 / qwen-image-plus / wan2.6-t2i / wanx-v1
- **豆包 Seedream** — doubao-seedream-4.0
- **同步调用** — 百炼接口使用同步模式，无需异步轮询，兼容所有 API Key 类型
- **API 地址可配** — 所有 API 端点均可通过管理后台手动配置
- **AstrBot 管理后台配置** — 所有参数通过 `_conf_schema.json` 在管理后台可视化配置

## 安装

将整个 `astrbot_plugin_qianwen_t2i` 目录放入 AstrBot 的 `plugins` 目录，重启即可。

依赖项会自动安装（`aiohttp>=3.9`）。

## 配置

在 AstrBot 管理后台 → 插件管理 → 千文生图 中进行可视化配置：

### 基础配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `provider` | 服务商选择：`dashscope` / `seedream` | `dashscope` |

### 阿里云百炼 DashScope

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `dashscope_base_url` | API 地址 | `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |
| `dashscope_api_key` | API Key | — |
| `dashscope_model` | 模型名称 | `qwen-image-2.0-pro` |
| `dashscope_size` | 输出尺寸 | `1024*1024` |
| `dashscope_n` | 每次生成张数 | `1` |

可选模型：
- `qwen-image-2.0-pro` — Qwen Image 2.0 Pro（推荐，质量最高）
- `qwen-image-2.0` — Qwen Image 2.0
- `qwen-image-plus` — Qwen Image Plus
- `wan2.6-t2i` — 通义万相 2.6
- `wanx-v1` — 通义万相 v1

### 豆包 Seedream

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `seedream_base_url` | Seedream API 地址 | `https://ark.cn-beijing.volces.com/api/v3/images/generations` |
| `seedream_api_key` | API Key（火山引擎 Ark） | — |
| `seedream_model` | 模型名称 | `doubao-seedream-4.0` |
| `seedream_size` | 输出尺寸 | `1024x1024` |

### 高级配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `timeout` | 请求超时（秒） | `120` |

## 使用

直接发送自然语言即可触发，例如：

- `帮我画一只小猫在草地上玩耍`
- `画一张夕阳下的海滩`
- `生成一个赛博朋克风格的未来城市`
- `来张星空图`
- `帮我画一幅水墨山水画`

也支持以「画」「生成」「绘制」结尾的句子：

- `我想要一个可爱的小狗头像设计，请帮我画`
- `一个古代武侠场景，帮我生成`

### 误触发过滤

以下结尾的名词不会被识别为画图请求：漫画、动画、油画、国画、水墨画、壁画、版画 等。

## 获取 API Key

- **阿里云百炼**：前往 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 创建 API Key
- **豆包 Seedream**：前往 [火山引擎 Ark](https://console.volcengine.com/ark/) 开通 Seedream 模型并获取 API Key