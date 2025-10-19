import asyncio
import shutil
import tempfile
from pathlib import Path
import threading
import time
import hashlib

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
from astrbot.api.star import Context, Star, StarTools, register
import astrbot.api.message_components as Comp


def _blocking_gif_to_mp4(input_path: str, output_path: str):
    """
    一个独立的、阻塞的函数，用于在单独的线程中执行视频转换，避免阻塞事件循环。
    """
    # 使用 MoviePy 在独立线程中执行转换。这里尽量减少控制台输出并关闭音频轨道。
    # 对于某些 GIF，MoviePy 可能无法正确读取 fps，这里提供默认值 15。
    with VideoFileClip(input_path) as clip:
        fps = clip.fps if clip.fps is not None else 15
        try:
            # 尝试使用新版本 MoviePy 的参数（不包含 verbose 和 logger）
            clip.write_videofile(
                output_path,
                codec="libx264",
                preset="ultrafast",
                audio=False,
                fps=fps,
            )
        except TypeError as e:
            if "verbose" in str(e):
                # 如果仍然报错 verbose 参数问题，尝试使用旧版本参数
                logger.warning(
                    f"[astrbot_plugin_gif_to_video] MoviePy 版本兼容性问题，尝试使用旧参数: {e}"
                )
                clip.write_videofile(
                    output_path,
                    codec="libx264",
                    preset="ultrafast",
                    audio=False,
                    fps=fps,
                    verbose=False,
                    logger=None,
                )
            else:
                # 如果是其他参数错误，直接抛出
                raise


@register(
    "astrbot_plugin_gif_to_video",
    "氕氙",
    "GIF转视频分析插件，自动为默认服务商或手动指定的服务商启用GIF转视频避免报错。",
    "2.0.8",
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
        self._temp_files = set()  # 跟踪临时文件
        self._temp_files_lock = threading.Lock()  # 线程安全锁
        self._cache_dir = (
            StarTools.get_data_dir(self.PLUGIN_NAME) / "cache"
        )  # 使用框架提供的数据目录
        self._cache_dir.mkdir(parents=True, exist_ok=True)  # 确保缓存目录存在

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

    def _get_provider_id_by_instance(self, provider_inst) -> str | None:
        """通过服务商实例获取其ID。使用框架提供的稳定API。"""
        if not provider_inst:
            return None

        try:
            # 首先尝试使用框架提供的稳定API获取所有providers
            all_providers = self.context.get_all_providers()

            # 遍历所有providers，寻找匹配的实例
            for provider in all_providers:
                if provider is provider_inst:
                    # 假设provider对象有id属性
                    return getattr(provider, "id", None)

            # 如果直接比较失败，尝试通过其他属性匹配
            for provider in all_providers:
                # 比较provider的name属性
                if (
                    hasattr(provider, "name")
                    and hasattr(provider_inst, "name")
                    and provider.name == provider_inst.name
                ):
                    return getattr(provider, "id", None)

            logger.warning(f"[{self.PLUGIN_NAME}] 无法为provider实例找到匹配的ID")
            return None
        except Exception as e:
            logger.error(
                f"[{self.PLUGIN_NAME}] 获取provider ID时出错: {e}", exc_info=True
            )
            return None

    def _get_default_provider_id(self) -> str | None:
        """获取当前默认的LLM服务商ID。使用框架提供的稳定API。"""
        try:
            # 使用框架提供的API获取当前使用的provider
            curr_provider = self.context.get_using_provider()

            if not curr_provider:
                logger.warning(f"[{self.PLUGIN_NAME}] 无法获取当前使用的服务商实例。")
                return None

            # 尝试直接获取provider的ID
            provider_id = getattr(curr_provider, "id", None)
            if provider_id:
                return provider_id

            # 如果没有id属性，尝试通过实例匹配
            return self._get_provider_id_by_instance(curr_provider)
        except Exception as e:
            logger.error(
                f"[{self.PLUGIN_NAME}] 获取默认服务商ID时出错: {e}", exc_info=True
            )
            return None

    def _cleanup_temp_files(self):
        """清理所有临时文件"""
        with self._temp_files_lock:
            for temp_file in list(self._temp_files):
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                    # 尝试删除父目录（如果为空）
                    parent_dir = temp_file.parent
                    if parent_dir.exists() and not any(parent_dir.iterdir()):
                        parent_dir.rmdir()
                    self._temp_files.discard(temp_file)
                except Exception as e:
                    logger.warning(
                        f"[{self.PLUGIN_NAME}] 清理临时文件失败 {temp_file}: {e}"
                    )

    def _cleanup_request_temp_files(
        self, temp_dir: Path, gif_path: Path, mp4_path: Path
    ):
        """清理单次请求创建的临时文件和目录"""
        for file_path in [gif_path, mp4_path, temp_dir]:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        # 删除目录及其内容
                        shutil.rmtree(file_path, ignore_errors=True)
            except Exception as e:
                logger.warning(
                    f"[{self.PLUGIN_NAME}] 清理请求临时文件失败 {file_path}: {e}"
                )

    def _register_temp_file(self, file_path: Path):
        """注册临时文件以便后续清理"""
        with self._temp_files_lock:
            self._temp_files.add(file_path)

    def _cleanup_expired_cache(self):
        """清理过期的缓存文件（超过24小时）"""
        try:
            current_time = time.time()
            for cache_file in self._cache_dir.glob("*.mp4"):
                if cache_file.is_file():
                    # 检查文件修改时间
                    file_mtime = cache_file.stat().st_mtime
                    if current_time - file_mtime > 86400:  # 24小时 = 86400秒
                        cache_file.unlink()
                        logger.debug(
                            f"[{self.PLUGIN_NAME}] 清理过期缓存文件: {cache_file}"
                        )
        except Exception as e:
            logger.warning(f"[{self.PLUGIN_NAME}] 清理过期缓存失败: {e}")

    def _get_cache_key(self, gif_source: str) -> str:
        """根据GIF源生成缓存键"""
        # 使用MD5哈希作为缓存键
        return hashlib.md5(gif_source.encode()).hexdigest()

    def _get_cached_video_path(self, gif_source: str) -> Path | None:
        """获取缓存的视频文件路径（如果存在且未过期）"""
        cache_key = self._get_cache_key(gif_source)
        cached_file = self._cache_dir / f"{cache_key}.mp4"

        if cached_file.exists():
            # 检查文件是否在24小时内
            current_time = time.time()
            file_mtime = cached_file.stat().st_mtime
            if current_time - file_mtime <= 86400:  # 24小时内
                logger.info(f"[{self.PLUGIN_NAME}] 使用缓存文件: {cached_file}")
                return cached_file

        return None

    def _cache_video_file(self, gif_source: str, video_path: Path) -> Path:
        """将转换后的视频文件缓存"""
        cache_key = self._get_cache_key(gif_source)
        cached_file = self._cache_dir / f"{cache_key}.mp4"

        try:
            # 复制文件到缓存目录
            shutil.copy2(video_path, cached_file)
            logger.info(f"[{self.PLUGIN_NAME}] 缓存视频文件: {cached_file}")
            return cached_file
        except Exception as e:
            logger.warning(f"[{self.PLUGIN_NAME}] 缓存视频文件失败: {e}")
            return video_path  # 如果缓存失败，返回原路径

    async def terminate(self):
        """插件终止时调用，释放资源"""
        logger.info(f"[{self.PLUGIN_NAME}] 插件已终止，清理临时文件")
        self._cleanup_temp_files()
        # 可选：在插件终止时清理过期缓存
        # self._cleanup_expired_cache()

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
                if comp.file and comp.file.lower().endswith(".gif"):
                    gif_file = comp.file
                    gif_url = comp.url
                    logger.info(f"[{self.PLUGIN_NAME}] 检测到GIF文件: {gif_file}")
                    break
                # 检查URL是否包含GIF
                elif comp.url and ".gif" in comp.url.lower():
                    gif_url = comp.url
                    logger.info(f"[{self.PLUGIN_NAME}] 检测到GIF URL: {gif_url}")
                    break

        if not gif_url and not gif_file:
            logger.debug(f"[{self.PLUGIN_NAME}] 未检测到GIF，跳过处理")
            return

        # 2. 检查插件是否为当前会话启用
        provider_id = getattr(req, "provider_id", None)
        if not provider_id:
            # 尝试从其他方式获取provider_id
            try:
                provider_inst = self.context.get_using_provider()
                if provider_inst:
                    # 尝试直接获取provider的ID
                    provider_id = getattr(provider_inst, "id", None)
                    if not provider_id:
                        # 如果没有id属性，尝试通过实例匹配
                        provider_id = self._get_provider_id_by_instance(provider_inst)
            except Exception as e:
                logger.debug(f"[{self.PLUGIN_NAME}] 获取provider时出错: {e}")

        if not provider_id:
            logger.debug(f"[{self.PLUGIN_NAME}] 无法获取provider_id，插件将跳过处理")
            return

        enabled_provider_id = self.config.get("enabled_provider_id", "")
        is_enabled = False
        if enabled_provider_id:  # 手动模式
            is_enabled = provider_id == enabled_provider_id
            logger.info(
                f"[{self.PLUGIN_NAME}] 手动模式，检查provider_id: {provider_id} == {enabled_provider_id}"
            )
        else:  # 自动模式
            if self.default_provider_id is None:
                self.default_provider_id = self._get_default_provider_id()
            if self.default_provider_id:
                is_enabled = provider_id == self.default_provider_id
                logger.info(
                    f"[{self.PLUGIN_NAME}] 自动模式，检查provider_id: {provider_id} == {self.default_provider_id}"
                )

        if not is_enabled:
            logger.info(f"[{self.PLUGIN_NAME}] 插件未启用，跳过处理")
            return

        # 3. 执行转换
        logger.info(f"[{self.PLUGIN_NAME}] 开始处理GIF转换")

        # 确定GIF源
        gif_source = gif_url if gif_url else gif_file

        # 首先检查缓存
        cached_video = self._get_cached_video_path(gif_source)
        if cached_video:
            # 使用缓存的文件
            video_path = cached_video

            # 从消息对象中移除原始的GIF图片组件
            for i, comp in enumerate(event.message_obj.message):
                if isinstance(comp, Comp.Image) and (
                    comp.file == gif_file or comp.url == gif_url
                ):
                    event.message_obj.message.pop(i)
                    break

            # 将转换后的视频添加到请求中
            if not hasattr(req, "image_urls"):
                req.image_urls = []
            req.image_urls.append(str(video_path))

            # 从消息中移除GIF
            if hasattr(req, "prompt") and "[图片]" in req.prompt:
                req.prompt = req.prompt.replace("[图片]", "[视频(GIF已转换，缓存)]", 1)

            logger.info(f"[{self.PLUGIN_NAME}] 使用缓存视频，已添加到请求中")
            return

        # 定期清理过期缓存（每次转换前检查一次）
        self._cleanup_expired_cache()

        # 创建持久化的临时目录，不会在with块结束时自动删除
        temp_dir = Path(tempfile.mkdtemp(prefix="astrbot_gif_convert_"))
        local_gif_path = temp_dir / "input.gif"
        local_mp4_path = temp_dir / "output.mp4"

        # 注册临时文件以便后续清理
        self._register_temp_file(local_gif_path)
        self._register_temp_file(local_mp4_path)
        self._register_temp_file(temp_dir)

        try:
            # 下载或复制GIF文件
            if gif_url and gif_url.startswith(("http://", "https://")):
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

            try:
                await asyncio.to_thread(
                    _blocking_gif_to_mp4, str(local_gif_path), str(local_mp4_path)
                )
                logger.info(f"[{self.PLUGIN_NAME}] GIF转换成功: {local_mp4_path}")

                # 缓存转换后的视频文件
                video_path = self._cache_video_file(gif_source, local_mp4_path)

                # 从消息对象中移除原始的GIF图片组件
                for i, comp in enumerate(event.message_obj.message):
                    if isinstance(comp, Comp.Image) and (
                        comp.file == gif_file or comp.url == gif_url
                    ):
                        event.message_obj.message.pop(i)
                        break

                # 将转换后的视频添加到请求中
                if not hasattr(req, "image_urls"):
                    req.image_urls = []
                req.image_urls.append(str(video_path))

                # 从消息中移除GIF
                if hasattr(req, "prompt") and "[图片]" in req.prompt:
                    req.prompt = req.prompt.replace("[图片]", "[视频(GIF已转换)]", 1)

                logger.info(
                    f"[{self.PLUGIN_NAME}] 已将转换后的视频添加到请求中，并移除了原始GIF"
                )
            except Exception as e:
                logger.error(f"[{self.PLUGIN_NAME}] GIF转换失败: {e}", exc_info=True)
                return
        except Exception as e:
            logger.error(
                f"[{self.PLUGIN_NAME}] 处理GIF失败 ({gif_source}): {e}",
                exc_info=True,
            )
            return
        finally:
            # 确保清理本次请求创建的临时文件和目录
            self._cleanup_request_temp_files(temp_dir, local_gif_path, local_mp4_path)
