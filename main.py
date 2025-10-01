import asyncio
import shutil
import tempfile
import aiohttp
from moviepy.editor import VideoFileClip
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter, AstrMessageEvent
import astrbot.api.message_components as Comp
from astrbot.api.star import Context, Star, register

# 插件的默认提示词
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

@register( "astrbot_plugin_gif_to_video","氕氙","GIF转视频分析插件，自动为默认服务商或手动指定的服务商启用GIF转视频避免报错。","1.1.1","https://github.com/piexian/astrbot_plugin_gif_to_video"
)
class GifToVideoPlugin(Star):
    """
    一个智能的GIF 适配插件。
    - 自动模式：当配置为空时，自动为 AstrBot 的全局默认服务商工作。
    - 手动模式：当配置不为空时，严格按照配置列表中的服务商 ID 工作。
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.default_provider_id = self._get_default_provider_id()
        self.ffmpeg_available = False
        plugin_name = "astrbot_plugin_gif_to_video"

        # 在插件加载时检查 FFmpeg 是否存在 
        if shutil.which("ffmpeg") is None:
            logger.error(
                f"插件 [{plugin_name}] 加载失败：未在系统中找到核心依赖 FFmpeg。"
                "GIF 转换功能将无法使用。请参照 README.md 安装 FFmpeg 后重启 AstrBot。"
            )
        else:
            self.ffmpeg_available = True
            enabled_providers = self.config.get("enabled_providers", [])
            if enabled_providers:
                logger.info(
                    f"{plugin_name} 已加载，运行在【手动模式】，适配服务商: {enabled_providers}"
                )
            else:
                logger.info(
                    f"{plugin_name} 已加载，运行在【自动模式】，将适配默认服务商: {self.default_provider_id or '未设置'}"
                )

    def _get_default_provider_id(self) -> str | None:
        """从 AstrBot 的主配置中获取默认的 LLM 服务商 ID。"""
        try:
            main_config = self.context.get_config()
            return main_config.get("llm", {}).get("default_provider_id")
        except Exception as e:
            logger.error(f"无法获取默认服务商 ID: {e}", exc_info=True)
            return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def adapt_gif_smartly(self, event: AstrMessageEvent):
        # 如果 FFmpeg 不可用，则不执行任何操作
        if not self.ffmpeg_available:
            return

        provider = self.context.provider_manager.get_using_provider(
            umo=event.unified_msg_origin
        )
        if not provider:
            return

        enabled_providers = self.config.get("enabled_providers", [])
        is_enabled = False
        if enabled_providers:
            is_enabled = provider.id in enabled_providers
        else:
            is_enabled = provider.id == self.default_provider_id

        if not is_enabled:
            return

        gif_element = next(
            (
                e
                for e in event.message_obj.message
                if isinstance(e, Comp.Image) and e.url and e.url.lower().endswith(".gif")
            ),
            None,
        )

        if not gif_element:
            return

        event.should_call_llm(False)

        yield event.plain_result(f"检测到 GIF，正在为模型 `{provider.id}` 进行动态内容转换...")

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                local_gif_path = f"{temp_dir}/input.gif"
                async with aiohttp.ClientSession() as session:
                    async with session.get(gif_element.url) as resp:
                        resp.raise_for_status()
                        with open(local_gif_path, "wb") as f:
                            f.write(await resp.read())

                local_mp4_path = f"{temp_dir}/output.mp4"
                
                await asyncio.to_thread(
                    _blocking_gif_to_mp4, local_gif_path, local_mp4_path
                )

                # **智能提示词处理**
                final_prompt = self.config.get("custom_prompt", DEFAULT_PROMPT)
                if self.config.get("auto_translate_prompt", False):
                    translation_provider = provider
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
                            prompt=f"Translate the following text into English. Output only the translated text itself, without any extra explanations or introductions:\n\n---\n\n{final_prompt}",
                            **translation_kwargs,
                        )
                        final_prompt = translation_resp.text
                    except Exception as e:
                        logger.error(f"使用 '{translation_provider.id}' 翻译失败: {e}")
                        if (
                            self.config.get("fallback_to_main_provider", True)
                            and translation_provider is not provider
                        ):
                            logger.info("翻译失败，尝试使用主服务商进行回退翻译...")
                            try:
                                fallback_resp = await provider.text_chat(
                                    prompt=f"Translate the following text into English. Output only the translated text itself, without any extra explanations or introductions:\n\n---\n\n{final_prompt}"
                                )
                                final_prompt = fallback_resp.text
                            except Exception as e2:
                                logger.error(f"主服务商回退翻译同样失败: {e2}")
                        else:
                            logger.warning("翻译失败且未启用回退，将使用原始提示词。")

                llm_resp = await event.request_llm(
                    prompt=final_prompt, image_urls=[local_mp4_path]
                )
                analysis_result = f"✨ 动态解析结果：\n{llm_resp.text}"
            except Exception as e:
                logger.error(f"为 `{provider.id}` 处理 GIF 时发生错误: {e}", exc_info=True)
                analysis_result = (
                    f"抱歉，为模型 `{provider.id}` 分析 GIF 时出错（它可能不支持视频格式）。"
                )

        await event.send(event.plain_result(analysis_result))