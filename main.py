import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
# 兼容不同版本的moviepy
try:
    from moviepy.editor import VideoFileClip  # 旧版本兼容
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip  # 新版本2.x
    except ImportError:
        from moviepy.video import VideoFileClip  # 备用方案
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter, AstrMessageEvent
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
    "2.0.1",
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

    async def terminate(self):
        """插件终止时调用，释放资源"""
        logger.info(f"[{self.PLUGIN_NAME}] 插件已终止")

    @filter.on_llm_request(priority=100)
    async def handle_gif_message(self, event: AstrMessageEvent, req):
        """
        处理包含GIF的消息，将其转换为MP4视频
        """
        if not self.ffmpeg_available:
            return

        # 添加调试日志
        logger.info(f"[{self.PLUGIN_NAME}] 收到LLM请求，检查是否包含GIF")
        
        # 1. 检查消息中是否包含 GIF
        gif_url = None
        gif_file = None
        
        # 检查消息链中的图片组件
        for comp in event.message_obj.message:
            if isinstance(comp, Comp.Image):
                # 检查是否是GIF文件
                if comp.file and comp.file.lower().endswith('.gif'):
                    gif_file = comp.file
                    gif_url = comp.url
                    logger.info(f"[{self.PLUGIN_NAME}] 检测到GIF文件: {gif_file}")
                    break
                # 检查URL是否包含GIF
                elif comp.url and '.gif' in comp.url.lower():
                    gif_url = comp.url
                    logger.info(f"[{self.PLUGIN_NAME}] 检测到GIF URL: {gif_url}")
                    break
        
        if not gif_url and not gif_file:
            logger.debug(f"[{self.PLUGIN_NAME}] 未检测到GIF，跳过处理")
            return

        # 2. 检查插件是否为当前会话启用
        provider_id = getattr(req, 'provider_id', None)
        if not provider_id:
            # 尝试从其他方式获取provider_id
            provider_inst = self.context.get_using_provider(umo=event.unified_msg_origin)
            if provider_inst:
                for p_id, p_inst in self.context.provider_manager.get_all_providers().items():
                    if p_inst is provider_inst:
                        provider_id = p_id
                        break
        
        if not provider_id:
            logger.warning(f"[{self.PLUGIN_NAME}] 无法获取provider_id")
            return

        enabled_provider_id = self.config.get("enabled_provider_id", "")
        is_enabled = False
        if enabled_provider_id:  # 手动模式
            is_enabled = provider_id == enabled_provider_id
            logger.info(f"[{self.PLUGIN_NAME}] 手动模式，检查provider_id: {provider_id} == {enabled_provider_id}")
        else:  # 自动模式
            if self.default_provider_id is None:
                self.default_provider_id = self._get_default_provider_id()
            if self.default_provider_id:
                is_enabled = provider_id == self.default_provider_id
                logger.info(f"[{self.PLUGIN_NAME}] 自动模式，检查provider_id: {provider_id} == {self.default_provider_id}")

        if not is_enabled:
            logger.info(f"[{self.PLUGIN_NAME}] 插件未启用，跳过处理")
            return

        # 3. 执行转换
        logger.info(f"[{self.PLUGIN_NAME}] 开始处理GIF转换")
        
        # 确定GIF源
        gif_source = gif_url if gif_url else gif_file
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            local_gif_path = temp_path / "input.gif"
            local_mp4_path = temp_path / "output.mp4"

            try:
                # 下载或复制GIF文件
                if gif_url and gif_url.startswith(('http://', 'https://')):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(gif_url) as resp:
                            resp.raise_for_status()
                            content = await resp.read()
                            with open(local_gif_path, "wb") as f:
                                f.write(content)
                elif gif_file:
                    # 如果是本地文件路径
                    shutil.copy2(gif_file, local_gif_path)
                else:
                    logger.error(f"[{self.PLUGIN_NAME}] 无效的GIF源")
                    return
            except Exception as e:
                logger.error(f"[{self.PLUGIN_NAME}] 处理GIF失败 ({gif_source}): {e}", exc_info=True)
                return

            try:
                await asyncio.to_thread(
                    _blocking_gif_to_mp4, str(local_gif_path), str(local_mp4_path)
                )
                logger.info(f"[{self.PLUGIN_NAME}] GIF转换成功: {local_mp4_path}")
                
                # 将转换后的视频添加到请求中
                if not hasattr(req, 'image_urls'):
                    req.image_urls = []
                req.image_urls.append(str(local_mp4_path))
                
                # 从消息中移除GIF
                if hasattr(req, 'prompt') and '[图片]' in req.prompt:
                    req.prompt = req.prompt.replace('[图片]', '[视频(GIF已转换)]', 1)
                
                logger.info(f"[{self.PLUGIN_NAME}] 已将转换后的视频添加到请求中")
            except Exception as e:
                logger.error(f"[{self.PLUGIN_NAME}] GIF转换失败: {e}", exc_info=True)
                return
