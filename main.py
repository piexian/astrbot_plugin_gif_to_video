import asyncio
import shutil
import tempfile
from pathlib import Path

import aiohttp
from moviepy.editor import VideoFileClip

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register

# 插件的默认英文提示词
DEFAULT_PROMPT = "Please describe the dynamic content of this GIF animation (which has been converted to a video for you) in a vivid and concise manner. Please reply in Chinese."


def _blocking_gif_to_mp4(input_path: str, output_path: str):
    """
    一个独立的、阻塞的函数，用于在单独的线程中执行视频转换，避免阻塞事件循环。
    """
    with VideoFileClip(input_path) as clip:
        clip.write_videofile(
            output_path,
            codec="libx264",
            preset="ultrafast",
            verbose=False,
            logger=None,
            fps=clip.fps if clip.fps is not None else 15,
        )


@register(
    "astrbot_plugin_gif_to_video",
    "氕氙",
    "GIF转视频分析插件，自动为默认服务商或手动指定的服务商启用GIF转视频避免报错。",
    "1.3.3",
    "https://github.com/piexian/astrbot_plugin_gif_to_video",
)
class GifToVideoPlugin(Star):
    """
    一个智能的GIF 适配插件。
    - 自动模式：当配置为空时，自动为 AstrBot 的全局默认服务商工作。
    - 手动模式：当配置不为空时，严格按照配置列表中的服务商 ID 工作。
    """

    PLUGIN_NAME = "astrbot_plugin_gif_to_video"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.default_provider_id = self._get_default_provider_id()
        self.ffmpeg_available = False
        self.cached_original_prompt = None
        self.cached_translated_prompt = None

        # 在插件加载时检查 FFmpeg 是否存在
        if shutil.which("ffmpeg") is None:
            logger.error(
                f"插件 [{self.PLUGIN_NAME}] 加载失败：未在系统中找到核心依赖 FFmpeg。"
                "GIF 转换功能将无法使用。请参照 README.md 安装 FFmpeg 后重启 AstrBot。"
            )
        else:
            self.ffmpeg_available = True
            enabled_provider_id = self.config.get("enabled_provider_id", "")
            if enabled_provider_id:
                logger.info(
                    f"{self.PLUGIN_NAME} 已加载，运行在【手动模式】，适配服务商: {enabled_provider_id}"
                )
            else:
                logger.info(
                    f"{self.PLUGIN_NAME} 已加载，运行在【自动模式】，将适配默认服务商: {self.default_provider_id or '未设置'}"
                )

    def _get_default_provider_id(self) -> str | None:
        """从 AstrBot 的主配置中获取默认的 LLM 服务商 ID。"""
        try:
            main_config = self.context.get_config()
            return main_config.get("llm", {}).get("default_provider_id")
        except Exception as e:
            logger.error(f"无法获取默认服务商 ID: {e}", exc_info=True)
            return None

    @filter.on_llm_request()
    async def adapt_gif_smartly(
        self, event: AstrMessageEvent, req: ProviderRequest, **kwargs
    ):
        if not self.ffmpeg_available:
            return

        # 从请求中查找 GIF
        gif_url = next(
            (url for url in req.image_urls if url and url.lower().endswith(".gif")),
            None,
        )
        if not gif_url:
            return

        provider = req.provider
        if not provider:
            return

        # 检查此 provider 是否已启用 GIF 转换
        enabled_provider_id = self.config.get("enabled_provider_id", "")
        is_enabled = (
            provider.id == enabled_provider_id
            if enabled_provider_id
            else provider.id == self.default_provider_id
        )

        if not is_enabled:
            return

        # 发送一个提示，告知用户正在进行转换
        await event.send(
            event.plain_result(
                f"检测到 GIF，正在为模型 `{provider.id}` 进行动态内容转换..."
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            local_gif_path = temp_path / "input.gif"
            local_mp4_path = temp_path / "output.mp4"

            # 1. 下载 GIF
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(gif_url) as resp:
                        resp.raise_for_status()
                        with open(local_gif_path, "wb") as f:
                            f.write(await resp.read())
            except aiohttp.ClientError as e:
                logger.error(f"下载 GIF 失败 ({gif_url}): {e}", exc_info=True)
                await event.send(
                    event.plain_result("抱歉，下载 GIF 时出错，请检查链接是否有效。")
                )
                event.stop_event()  # 停止事件，防止损坏的请求被发送
                return

            # 2. 转换 GIF 为 MP4
            try:
                await asyncio.to_thread(
                    _blocking_gif_to_mp4, str(local_gif_path), str(local_mp4_path)
                )
            except Exception as e:
                logger.error(f"GIF 转换 MP4 失败: {e}", exc_info=True)
                await event.send(
                    event.plain_result(
                        "抱歉，处理 GIF 时出错（可能是文件损坏或格式不受支持）。"
                    )
                )
                event.stop_event()
                return

            # 3. 获取最终提示词
            final_prompt = await self._get_final_prompt(provider)

            # 4. 修改原始请求
            req.prompt = final_prompt
            req.image_urls.remove(gif_url)
            req.image_urls.append(str(local_mp4_path))

    async def _get_final_prompt(self, main_provider) -> str:
        """处理提示词的翻译逻辑（带缓存）"""
        original_prompt = self.config.get("custom_prompt", DEFAULT_PROMPT)
        if not self.config.get("auto_translate_prompt", False):
            return original_prompt

        # 检查缓存
        if (
            self.cached_original_prompt == original_prompt
            and self.cached_translated_prompt
        ):
            return self.cached_translated_prompt

        logger.info("检测到提示词变更或首次运行，正在翻译...")
        translation_provider = main_provider
        translation_provider_id = self.config.get("translation_provider_id")
        if translation_provider_id:
            custom_provider = self.context.provider_manager.get_provider_by_id(
                translation_provider_id
            )
            if custom_provider:
                translation_provider = custom_provider
            else:
                logger.warning(
                    f"指定的翻译服务商 '{translation_provider_id}' 未找到，将回退使用主服务商。"
                )

        translation_model_name = self.config.get("translation_model_name")
        translation_kwargs = (
            {"model": translation_model_name} if translation_model_name else {}
        )

        try:
            translation_resp = await translation_provider.text_chat(
                prompt=f"Translate the following text into English. Output only the translated text itself, without any extra explanations or introductions:\n\n---\n\n{original_prompt}",
                **translation_kwargs,
            )
            translated_text = translation_resp.text
            self.cached_original_prompt = original_prompt
            self.cached_translated_prompt = translated_text
            logger.info("提示词翻译成功并已缓存。")
            return translated_text
        except Exception as e:
            logger.error(f"使用 '{translation_provider.id}' 翻译失败: {e}")
            if (
                self.config.get("fallback_to_main_provider", True)
                and translation_provider is not main_provider
            ):
                logger.info("翻译失败，尝试使用主服务商进行回退翻译...")
                try:
                    fallback_resp = await main_provider.text_chat(
                        prompt=f"Translate the following text into English. Output only the translated text itself, without any extra explanations or introductions:\n\n---\n\n{original_prompt}"
                    )
                    translated_text = fallback_resp.text
                    self.cached_original_prompt = original_prompt
                    self.cached_translated_prompt = translated_text
                    logger.info("提示词回退翻译成功并已缓存。")
                    return translated_text
                except Exception as e2:
                    logger.error(f"主服务商回退翻译同样失败: {e2}")

            logger.warning("翻译失败且未启用回退，将使用原始提示词。")
            return original_prompt
