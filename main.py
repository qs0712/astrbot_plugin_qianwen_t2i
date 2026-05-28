import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import aiohttp
import mcp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image
from astrbot.api.star import Context, Star, StarTools

from .api_backends import RATIO_MAP_DASHSCOPE, RATIO_MAP_SEEDREAM, create_backend


EXPLICIT_KW = re.compile(
    r"(?:帮我画|帮我生成|帮我设计|来[一这]?张|(?:画|生成|设计)[一这]?[个只张幅条枚块份]?|出图)\s*(?P<prompt>.+)"
)

ENDING_KW = re.compile(r"^(.{2,}?)(绘制|生成|画)\s*$")

ENDING_BLACKLIST = frozenset(
    {"漫", "动", "插", "油", "国", "壁", "版", "书画", "水墨", "壁纸", "油画", "国画", "漫画", "动画"}
)

COMBINED_REGEX = (
    r"(?:.*(?:帮我画|帮我生成|帮我设计|来[一这]?张|(?:画|生成|设计)[一这]?[个只张幅条枚块份]?|出图).*)"
    r"|"
    r"(?:.+(?:绘制|生成|画)\s*$)"
)

RATIO_PATTERN = re.compile(r"(?<!\d)(?P<ratio>\d{1,2}:\d{1,2})(?!\d)")


class Text2ImgPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_qianwen_t2i")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _llm_tool_text_result(message: str) -> mcp.types.CallToolResult:
        text = str(message or "").strip()
        if not text:
            text = "The tool completed without additional details."
        return mcp.types.CallToolResult(
            content=[mcp.types.TextContent(type="text", text=text)]
        )

    def _extract_prompt(self, message: str) -> str:
        m = EXPLICIT_KW.search(message)
        if m:
            prompt = m.group("prompt").strip()
            if len(prompt) >= 2:
                return prompt

        m = ENDING_KW.match(message)
        if m:
            prompt = m.group(1).strip()
            if len(prompt) >= 2 and not self._is_false_positive(prompt):
                return prompt

        return ""

    def _is_false_positive(self, prompt: str) -> bool:
        for word in ENDING_BLACKLIST:
            if prompt.endswith(word):
                return True
        return False

    def _parse_ratio(self, prompt: str, provider: str) -> Tuple[str, Optional[str]]:
        m = RATIO_PATTERN.search(prompt)
        if not m:
            return prompt, None

        ratio_key = m.group("ratio")
        ratio_map = RATIO_MAP_DASHSCOPE if provider == "dashscope" else RATIO_MAP_SEEDREAM
        mapped_size = ratio_map.get(ratio_key)
        if not mapped_size:
            return prompt, None

        cleaned = prompt[: m.start()] + prompt[m.end():]
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned, mapped_size

    def _get_provider(self) -> str:
        return self.config.get("provider", "dashscope")

    def _check_api_key(self) -> Optional[str]:
        provider = self._get_provider()
        if provider == "dashscope" and not self.config.get("dashscope_api_key"):
            return "阿里云百炼 API Key 未配置，请在插件配置中设置 dashscope_api_key。"
        if provider == "seedream" and not self.config.get("seedream_api_key"):
            return "豆包 Seedream API Key 未配置，请在插件配置中设置 seedream_api_key。"
        return None

    async def _download_image(self, url: str, timeout: int = 60) -> Optional[Path]:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()

            suffix = ".png"
            if url.lower().endswith((".jpg", ".jpeg")):
                suffix = ".jpg"
            elif url.lower().endswith(".webp"):
                suffix = ".webp"

            tmp = tempfile.NamedTemporaryFile(
                dir=self.data_dir, suffix=suffix, delete=False
            )
            tmp.write(data)
            tmp.close()
            return Path(tmp.name)
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None

    async def _do_generate(self, prompt: str, ratio_size: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        if ratio_size is None:
            provider = self._get_provider()
            prompt, ratio_size = self._parse_ratio(prompt, provider)
        backend = create_backend(self.config)
        success, result = await backend.generate(prompt, size=ratio_size)
        return success, result, prompt

    @filter.regex(COMBINED_REGEX)
    async def on_draw_request(self, event: AstrMessageEvent):
        message = event.message_str.strip()
        prompt = self._extract_prompt(message)
        if not prompt:
            return

        key_error = self._check_api_key()
        if key_error:
            yield event.plain_result(f"⚠️ {key_error}")
            return

        provider_label = "百炼" if self._get_provider() == "dashscope" else "豆包 Seedream"
        yield event.plain_result(f"🎨 正在通过{provider_label}生成图片，prompt: {prompt}")

        success, result, _ = await self._do_generate(prompt)

        if not success:
            yield event.plain_result(f"❌ 图片生成失败：{result}")
            return

        if result.startswith("data:image"):
            yield event.plain_result("✅ 图片生成成功，但因平台限制无法直接发送 Base64 图片")
            return

        local_path = await self._download_image(
            result, timeout=int(self.config.get("timeout", 60))
        )
        if local_path:
            yield event.plain_result("✅ 图片生成成功，正在发送...")
            yield event.chain_result([Image.fromFileSystem(str(local_path))])
        else:
            yield event.plain_result(f"❌ 图片下载失败，请检查网络或直接访问：\n{result}")

    @filter.llm_tool(name="draw_image")
    async def draw_image(self, event: AstrMessageEvent, prompt: str):
        """根据提示词生成图片。

        Args:
            prompt(string): 图片提示词，描述想要的图片内容（主体、场景、风格等）
        """
        prompt = (prompt or "").strip()
        if not prompt:
            return self._llm_tool_text_result("未提供图片描述，请提供 prompt 参数。")

        key_error = self._check_api_key()
        if key_error:
            return self._llm_tool_text_result(key_error)

        provider_label = "百炼" if self._get_provider() == "dashscope" else "豆包 Seedream"
        await event.send(event.plain_result(f"🎨 正在通过{provider_label}生成图片，请稍候..."))

        provider = self._get_provider()
        cleaned, ratio_size = self._parse_ratio(prompt, provider)
        if ratio_size is None:
            orig = getattr(event, "message_str", "") or ""
            _, ratio_size = self._parse_ratio(orig, provider)

        success, result, cleaned_prompt = await self._do_generate(cleaned, ratio_size=ratio_size)
        if not success:
            return self._llm_tool_text_result(f"图片生成失败：{result}")

        if result.startswith("data:image"):
            return self._llm_tool_text_result(
                f"图片已生成 (Base64 格式)，prompt: {cleaned_prompt}"
            )

        local_path = await self._download_image(
            result, timeout=int(self.config.get("timeout", 60))
        )
        if local_path:
            await event.send(event.chain_result([Image.fromFileSystem(str(local_path))]))
            return self._llm_tool_text_result(
                f"图片生成成功并已发送。prompt: {cleaned_prompt}"
            )
        else:
            return self._llm_tool_text_result(
                f"图片生成成功但下载失败，请检查网络。原始地址: {result}"
            )