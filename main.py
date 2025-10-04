import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
from moviepy.editor import VideoFileClip
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter, EventMessageType
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp


def _blocking_gif_to_mp4(input_path: str, output_path: str):
    """
    一个独立的、阻塞的函数，用于在单独的线程中执行视频转换，避免阻塞事件循环。
    """
    # 使用 MoviePy 在独立线程中执行转换。这里尽量减少控制台输出并关闭音频轨道。
    # 对于某些 GIF，MoviePy 可能无法正确读取 fps，这里提供默认值 15。
    with VideoFileClip(input_path) as clip:
        fps = clip.fps if clip.fps is not None else 15
        clip.write_videofile(
            output_path,
            codec="libx264",
            preset="ultrafast",
            audio=False,
            fps=fps,
            verbose=False,
            logger=None,
        )


@register(
    "astrbot_plugin_gif_to_video",
    "氕氙",
    "GIF转视频分析插件，自动为默认服务商或手动指定的服务商启用GIF转视频避免报错。",
    "2.0.0",
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
        self.default_provider_id = None
        self.ffmpeg_available = False

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
                # 预先尝试解析默认服务商（若可用）以降低首次触发时的延迟
                try:
                    self.default_provider_id = self._get_default_provider_id()
                except Exception:
                    self.default_provider_id = None
                logger.info(
                    f"{self.PLUGIN_NAME} 已加载，运行在【自动模式】，默认服务商: {self.default_provider_id}"
                )

    def _get_default_provider_id(self) -> str | None:
        """通过匹配实例来获取当前默认的 LLM 服务商 ID。"""
        try:
            curr_provider = self.context.provider_manager.curr_provider_inst
            if not curr_provider:
                logger.warning("无法从 provider_manager 获取到当前的服务商实例。")
                return None

            # 遍历所有服务商，通过匹配实例找到其 ID
            # 遍历字典项以匹配实例 -> ID
            for provider_id, provider_inst in self.context.provider_manager.get_all_providers().items():
                if provider_inst is curr_provider:
                    return provider_id

            logger.warning("无法为当前服务商实例找到匹配的 ID。")
            return None
        except Exception as e:
            logger.error(
                f"通过 provider_manager 获取默认服务商 ID 时出错: {e}", exc_info=True
            )
            return None

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_gif_message(self, event: AstrMessageEvent, **kwargs):
        if not self.ffmpeg_available:
            return

        # 1. 检查消息中是否包含 GIF
        gif_url = None
        # 两种常见消息结构都尝试兼容：直接的 raw_message 段 或者携带 file/url 的 segment
        if event.message_obj and hasattr(event.message_obj, "raw_message"):
            raw_message = event.message_obj.raw_message
            if "message" in raw_message and isinstance(raw_message["message"], list):
                for segment in raw_message["message"]:
                    seg_type = segment.get("type")
                    data = segment.get("data", {})
                    file_name = data.get("file", "") or data.get("name", "")
                    url = data.get("url") or data.get("uri")
                    if seg_type == "image" and file_name.lower().endswith(".gif"):
                        gif_url = url
                        break
        if not gif_url:
            return

        # 2. 检查插件是否为当前会话启用
        # 获取当前会话使用的 provider 实例
        provider_inst = self.context.get_using_provider(umo=event.unified_msg_origin)
        if not provider_inst:
            return

        provider_id = None
        for p_id, p_inst in self.context.provider_manager.get_all_providers().items():
            if p_inst is provider_inst:
                provider_id = p_id
                break
        if not provider_id:
            return

        enabled_provider_id = self.config.get("enabled_provider_id", "")
        is_enabled = False
        if enabled_provider_id:  # 手动模式
            is_enabled = provider_id == enabled_provider_id
        else:  # 自动模式
            if self.default_provider_id is None:
                self.default_provider_id = self._get_default_provider_id()
            if self.default_provider_id:
                is_enabled = provider_id == self.default_provider_id

        if not is_enabled:
            return

        # 3. 执行转换和发送
        await event.send(event.plain_result("检测到 GIF，正在转换..."))
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            local_gif_path = temp_path / "input.gif"
            local_mp4_path = temp_path / "output.mp4"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(gif_url) as resp:
                        resp.raise_for_status()
                        content = await resp.read()
                        with open(local_gif_path, "wb") as f:
                            f.write(content)
            except aiohttp.ClientError as e:
                logger.error(f"下载 GIF 失败 ({gif_url}): {e}", exc_info=True)
                await event.send(event.plain_result("抱歉，下载 GIF 时出错。"))
                event.stop_event()
                return

            try:
                await asyncio.to_thread(
                    _blocking_gif_to_mp4, str(local_gif_path), str(local_mp4_path)
                )
            except Exception as e:
                logger.error(f"GIF 转换 MP4 失败: {e}", exc_info=True)
                await event.send(event.plain_result("抱歉，处理 GIF 时出错。"))
                event.stop_event()
                return

            # 4. 发送视频并中断事件
            await event.send(
                event.chain_result([Comp.Video.fromFileSystem(str(local_mp4_path))])
            )
            event.stop_event()
