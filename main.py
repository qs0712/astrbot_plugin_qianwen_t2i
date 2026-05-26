import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import aiohttp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image
from astrbot.api.star import Context, Star, StarTools

from .api_backends import RATIO_MAP_DASHSCOPE, RATIO_MAP_SEEDREAM, create_backend


EXPLICIT_KW = re.compile(
    r"(?:帮我画|(?:画|生成)一(?:个|张|幅)|来一?张|帮我生成)\s*(?P<prompt>.+)"
)

ENDING_KW = re.compile(r"^(.{2,}?)(绘制|生成|画)\s*$")

ENDING_BLACKLIST = frozenset(
    {"漫", "动", "插", "油", "国", "壁", "版", "书画", "水墨", "壁纸", "油画", "国画", "漫画", "动画"}
)

COMBINED_REGEX = (
    r"(?:.*(?:帮我画|(?:画|生成)一(?:个|张|幅)|来一?张|帮我生成).+)"
    r"|"
    r"(?:.+(?:绘制|生成|画)\s*$)"
)

RATIO_PATTERN = re.compile(
    r"(?:[ 　，,。！!]|^)(?P<ratio>\d{1,2}:\d{1,2})(?:[ 　，,。！!]|$)",
)


class Text2ImgPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_qianwen_t2i")
        self.data_dir.mkdir(parents=True, exist_ok=True)

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

    @filter.regex(COMBINED_REGEX)
    async def on_draw_request(self, event: AstrMessageEvent):
        message = event.message_str.strip()
        prompt = self._extract_prompt(message)
        if not prompt:
            return

        config = self.config
        provider = config.get("provider", "dashscope")

        if provider == "dashscope" and not config.get("dashscope_api_key"):
            yield event.plain_result(
                "⚠️ 阿里云百炼 API Key 未配置，请在插件配置中设置 dashscope_api_key。"
            )
            return
        if provider == "seedream" and not config.get("seedream_api_key"):
            yield event.plain_result(
                "⚠️ 豆包 Seedream API Key 未配置，请在插件配置中设置 seedream_api_key。"
            )
            return

        prompt, ratio_size = self._parse_ratio(prompt, provider)

        provider_label = "百炼" if provider == "dashscope" else "豆包 Seedream"
        info_parts = [f"🎨 正在通过{provider_label}生成图片"]
        if ratio_size:
            info_parts.append(f"，尺寸: {ratio_size}")
        info_parts.append(f"，prompt: {prompt}")
        yield event.plain_result("".join(info_parts))

        backend = create_backend(config)
        success, result = await backend.generate(prompt, size=ratio_size)

        if not success:
            yield event.plain_result(f"❌ 图片生成失败：{result}")
            return

        if result.startswith("data:image"):
            yield event.plain_result("✅ 图片生成成功！正在发送...")
            logger.info("图片生成成功 (Base64)")
            yield event.plain_result("[已生成图片，但因平台限制无法直接以 Base64 格式发送]")
            return

        local_path = await self._download_image(
            result, timeout=int(config.get("timeout", 60))
        )
        if local_path:
            yield event.plain_result("✅ 图片生成成功，正在发送...")
            yield event.chain_result([Image.fromFileSystem(str(local_path))])
        else:
            yield event.plain_result(f"❌ 图片下载失败，请检查网络或直接访问：\n{result}")