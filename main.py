import asyncio
import hashlib
import shutil
import tempfile
import threading
import time
from pathlib import Path

import aiohttp
from PIL import Image

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
    "GIF 转视频适配插件，自动替换 GIF 为 MP4 与多帧预览，避免服务商报错。",
    "2.3.0",
    "https://github.com/piexian/astrbot_plugin_gif_to_video",
)
class GifToVideoPlugin(Star):
    """
    一个智能的 GIF 适配插件。
    - 自动模式：当配置为空时，自动为 AstrBot 的全局默认服务商工作。
    - 手动模式：当配置不为空时，严格按照配置列表中的服务商 ID 工作。
    - GIF 预览：自动提取多帧图片，帮助任意多模态 LLM 理解动图内容。
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
        self._frame_cache_dir = self._cache_dir / "frames"
        self._frame_cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_ttl = 86400  # 24 小时
        self.preview_frame_count = max(
            1, int(self.config.get("preview_frame_count", 4))
        )

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
                try:
                    self.default_provider_id = self._get_default_provider_id()
                except Exception:
                    self.default_provider_id = None
                logger.info(
                    f"{self.PLUGIN_NAME} 已加载，运行在【自动模式】，默认服务商: {self.default_provider_id}"
                )

    def _get_provider_map(self) -> dict[str, object]:
        """获取 provider_id -> provider 实例的映射。"""
        provider_manager = getattr(self.context, "provider_manager", None)
        if provider_manager:
            inst_map = getattr(provider_manager, "inst_map", None)
            if isinstance(inst_map, dict) and inst_map:
                return inst_map

        providers = self.context.get_all_providers()
        if isinstance(providers, dict):
            return providers

        provider_map: dict[str, object] = {}
        if providers:
            for idx, provider in enumerate(providers):
                provider_id = getattr(provider, "provider_id", None) or getattr(
                    provider, "id", None
                )
                if not provider_id:
                    provider_config = getattr(provider, "provider_config", {})
                    if isinstance(provider_config, dict):
                        provider_id = provider_config.get("id")
                if not provider_id:
                    provider_id = f"provider_{idx}"
                provider_map[provider_id] = provider
        return provider_map

    def _get_provider_id_by_instance(self, provider_inst) -> str | None:
        """通过服务商实例获取其ID。使用框架提供的稳定API。"""
        if not provider_inst:
            return None

        provider_id = getattr(provider_inst, "provider_id", None) or getattr(
            provider_inst, "id", None
        )
        if provider_id:
            return provider_id

        provider_config = getattr(provider_inst, "provider_config", {})
        if isinstance(provider_config, dict):
            provider_id = provider_config.get("id")
            if provider_id:
                return provider_id

        try:
            provider_map = self._get_provider_map()
            for pid, provider in provider_map.items():
                if provider is provider_inst:
                    return pid

            for pid, provider in provider_map.items():
                if (
                    hasattr(provider, "name")
                    and hasattr(provider_inst, "name")
                    and provider.name == provider_inst.name
                ):
                    return pid
                if provider.__class__ == provider_inst.__class__:
                    return pid

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
            curr_provider = self.context.get_using_provider(umo="default")

            if not curr_provider:
                logger.warning(f"[{self.PLUGIN_NAME}] 无法获取当前使用的服务商实例。")
                return None

            # 尝试直接获取provider的ID
            provider_id = getattr(curr_provider, "provider_id", None) or getattr(
                curr_provider, "id", None
            )
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
                        shutil.rmtree(file_path, ignore_errors=True)
            except Exception as e:
                logger.warning(
                    f"[{self.PLUGIN_NAME}] 清理请求临时文件失败 {file_path}: {e}"
                )

    def _register_temp_file(self, file_path: Path):
        """注册临时文件以便后续清理"""
        with self._temp_files_lock:
            self._temp_files.add(file_path)

    def _is_cache_entry_valid(self, path: Path) -> bool:
        try:
            return time.time() - path.stat().st_mtime <= self._cache_ttl
        except FileNotFoundError:
            return False

    def _cleanup_expired_cache(self):
        """清理过期的缓存文件（超过24小时）"""
        try:
            current_time = time.time()
            for cache_file in self._cache_dir.glob("*.mp4"):
                if (
                    cache_file.is_file()
                    and current_time - cache_file.stat().st_mtime > self._cache_ttl
                ):
                    cache_file.unlink()
                    logger.debug(f"[{self.PLUGIN_NAME}] 清理过期缓存文件: {cache_file}")

            for frame_dir in self._frame_cache_dir.glob("*"):
                if frame_dir.is_dir():
                    try:
                        if current_time - frame_dir.stat().st_mtime > self._cache_ttl:
                            shutil.rmtree(frame_dir, ignore_errors=True)
                            logger.debug(
                                f"[{self.PLUGIN_NAME}] 清理过期帧缓存: {frame_dir}"
                            )
                    except FileNotFoundError:
                        continue
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

        if cached_file.exists() and self._is_cache_entry_valid(cached_file):
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

    def _get_preview_frame_dir(self, cache_key: str) -> Path:
        return self._frame_cache_dir / cache_key

    def _get_cached_preview_frames(self, cache_key: str) -> list[Path]:
        frame_dir = self._get_preview_frame_dir(cache_key)
        if frame_dir.exists() and self._is_cache_entry_valid(frame_dir):
            frames = sorted(frame_dir.glob("*.png"))
            if frames:
                return frames
        return []

    def _generate_preview_frames(self, video_path: Path, cache_key: str) -> list[Path]:
        """生成 GIF 的预览帧，帮助非视频模型理解完整动图。"""
        frame_dir = self._get_preview_frame_dir(cache_key)
        frame_dir.mkdir(parents=True, exist_ok=True)
        generated_frames: list[Path] = []

        try:
            with VideoFileClip(str(video_path)) as clip:
                duration = clip.duration or 0
                sample_count = max(1, self.preview_frame_count)

                for idx in range(sample_count):
                    if duration <= 0:
                        t = 0
                    else:
                        fraction = (idx + 0.5) / sample_count
                        t = min(max(fraction * duration, 0), max(duration - 0.01, 0))
                    try:
                        frame = clip.get_frame(t)
                    except Exception as frame_error:
                        logger.warning(
                            f"[{self.PLUGIN_NAME}] 提取第 {idx} 帧失败: {frame_error}"
                        )
                        continue
                    frame_image = Image.fromarray(frame)
                    frame_path = frame_dir / f"{cache_key}_frame_{idx}.png"
                    frame_image.save(frame_path)
                    generated_frames.append(frame_path)

            if generated_frames:
                # 更新目录时间戳，便于 TTL 计算
                frame_dir.touch(exist_ok=True)
            return generated_frames
        except Exception as e:
            logger.warning(
                f"[{self.PLUGIN_NAME}] 生成 GIF 预览帧失败: {e}", exc_info=True
            )
            shutil.rmtree(frame_dir, ignore_errors=True)
            return []

    def _ensure_preview_frames(self, cache_key: str, video_path: Path) -> list[Path]:
        """获取或生成 GIF 的预览帧。"""
        cached_frames = self._get_cached_preview_frames(cache_key)
        if cached_frames:
            return cached_frames
        return self._generate_preview_frames(video_path, cache_key)

    def _inject_preview_hint(self, prompt: str | None, frame_count: int) -> str:
        """在 prompt 中注入说明，提醒 LLM 已附带多帧图片。"""
        if frame_count > 0:
            hint = f"[系统提示] GIF 已被拆分为 {frame_count} 帧图片，请综合所有帧理解整段动画。"
        else:
            hint = (
                "[系统提示] GIF 已转换为视频，但当前服务商仅支持图片，"
                "本次未能生成预览帧，请结合上下文理解该动图。"
            )
        prompt = prompt or ""
        if hint in prompt:
            return prompt
        marker = "[视频(GIF已转换)]"
        if marker in prompt:
            return prompt.replace(marker, f"{marker}{hint}")
        return f"{hint}\n{prompt}" if prompt else hint

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
            logger.warning(f"[{self.PLUGIN_NAME}] FFmpeg不可用，跳过GIF处理")
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
        logger.info(f"[{self.PLUGIN_NAME}] 获取到provider_id: {provider_id}")

        if not provider_id:
            # 尝试从其他方式获取provider_id
            try:
                provider_inst = self.context.get_using_provider(
                    umo=event.unified_msg_origin
                )
                logger.info(
                    f"[{self.PLUGIN_NAME}] 从上下文获取到provider实例: {provider_inst}"
                )
                logger.info(
                    f"[{self.PLUGIN_NAME}] Provider实例类型: {type(provider_inst)}"
                )
                logger.info(
                    f"[{self.PLUGIN_NAME}] Provider实例属性: {[attr for attr in dir(provider_inst) if not attr.startswith('_')]}"
                )

                if provider_inst:
                    # 尝试直接获取provider的ID
                    provider_id = getattr(
                        provider_inst, "provider_id", None
                    ) or getattr(provider_inst, "id", None)
                    logger.info(
                        f"[{self.PLUGIN_NAME}] 从实例获取到provider_id: {provider_id}"
                    )
                    if not provider_id:
                        # 如果没有id属性，尝试通过实例匹配
                        provider_id = self._get_provider_id_by_instance(provider_inst)
                        logger.info(
                            f"[{self.PLUGIN_NAME}] 通过实例匹配获取到provider_id: {provider_id}"
                        )

                        # 如果还是无法获取，尝试获取所有providers进行调试
                        if not provider_id:
                            try:
                                # 获取provider_manager的inst_map进行调试
                                inst_map = getattr(
                                    self.context.provider_manager, "inst_map", {}
                                )
                                logger.info(
                                    f"[{self.PLUGIN_NAME}] 所有可用的providers: {list(inst_map.keys())}"
                                )
                                for pid, p in inst_map.items():
                                    if p is provider_inst:
                                        logger.info(
                                            f"[{self.PLUGIN_NAME}] 找到匹配的provider: {pid}"
                                        )
                                        provider_id = pid
                                        break
                            except Exception as debug_e:
                                logger.error(
                                    f"[{self.PLUGIN_NAME}] 调试获取所有providers失败: {debug_e}"
                                )
            except Exception as e:
                logger.error(
                    f"[{self.PLUGIN_NAME}] 获取provider时出错: {e}", exc_info=True
                )

        if not provider_id:
            logger.error(f"[{self.PLUGIN_NAME}] 无法获取provider_id，插件将跳过处理")
            return
        else:
            try:
                setattr(req, "provider_id", provider_id)
            except Exception:
                pass

        enabled_provider_id = self.config.get("enabled_provider_id", "")
        logger.info(
            f"[{self.PLUGIN_NAME}] 配置的enabled_provider_id: '{enabled_provider_id}'"
        )
        logger.info(
            f"[{self.PLUGIN_NAME}] 当前default_provider_id: '{self.default_provider_id}'"
        )

        is_enabled = False
        if enabled_provider_id:  # 手动模式
            is_enabled = provider_id == enabled_provider_id
            logger.info(
                f"[{self.PLUGIN_NAME}] 手动模式，检查provider_id: {provider_id} == {enabled_provider_id} = {is_enabled}"
            )
        else:  # 自动模式
            if self.default_provider_id is None:
                self.default_provider_id = self._get_default_provider_id()
                logger.info(
                    f"[{self.PLUGIN_NAME}] 重新获取default_provider_id: {self.default_provider_id}"
                )
            if self.default_provider_id:
                is_enabled = provider_id == self.default_provider_id
                logger.info(
                    f"[{self.PLUGIN_NAME}] 自动模式，检查provider_id: {provider_id} == {self.default_provider_id} = {is_enabled}"
                )
            else:
                logger.warning(
                    f"[{self.PLUGIN_NAME}] 无法获取default_provider_id，自动模式失败"
                )

        if not is_enabled:
            logger.warning(
                f"[{self.PLUGIN_NAME}] 插件未启用，跳过处理。当前provider: {provider_id}, 配置: {enabled_provider_id}, 默认: {self.default_provider_id}"
            )
            return

        # 3. 执行转换
        logger.info(f"[{self.PLUGIN_NAME}] 开始处理GIF转换")

        # 确定GIF源
        gif_source = gif_url if gif_url else gif_file
        cache_key = self._get_cache_key(gif_source)

        # 首先检查缓存
        video_path = self._get_cached_video_path(gif_source)
        if not video_path:
            # 定期清理过期缓存（每次转换前检查一次）
            self._cleanup_expired_cache()

            # 创建持久化的临时目录
            temp_dir = Path(tempfile.mkdtemp(prefix="astrbot_gif_convert_"))
            local_gif_path = temp_dir / "input.gif"
            local_mp4_path = temp_dir / "output.mp4"

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
                    shutil.copy2(gif_file, local_gif_path)
                else:
                    logger.error(f"[{self.PLUGIN_NAME}] 无效的GIF源")
                    return

                await asyncio.to_thread(
                    _blocking_gif_to_mp4, str(local_gif_path), str(local_mp4_path)
                )
                logger.info(f"[{self.PLUGIN_NAME}] GIF转换成功: {local_mp4_path}")

                video_path = self._cache_video_file(gif_source, local_mp4_path)

            except Exception as e:
                logger.error(
                    f"[{self.PLUGIN_NAME}] 处理GIF失败 ({gif_source}): {e}",
                    exc_info=True,
                )
                return
            finally:
                self._cleanup_request_temp_files(
                    temp_dir, local_gif_path, local_mp4_path
                )

        # 4. 处理视频（发送或分析）
        if not video_path:
            return

        # 从消息对象中移除原始的GIF图片组件
        for i, comp in enumerate(event.message_obj.message):
            if isinstance(comp, Comp.Image) and (
                comp.file == gif_file or comp.url == gif_url
            ):
                event.message_obj.message.pop(i)
                break

        # 移除 "[图片]" 文本
        if hasattr(req, "prompt") and "[图片]" in req.prompt:
            req.prompt = req.prompt.replace("[图片]", "[视频(GIF已转换)]", 1)

        try:
            preview_frames = await asyncio.to_thread(
                self._ensure_preview_frames, cache_key, video_path
            )
        except Exception as frame_error:
            logger.error(
                f"[{self.PLUGIN_NAME}] 生成 GIF 预览帧异常: {frame_error}",
                exc_info=True,
            )
            preview_frames = []

        if not hasattr(req, "image_urls") or req.image_urls is None:
            req.image_urls = []

        if preview_frames:
            appended = 0
            for frame_path in preview_frames:
                path_str = str(frame_path)
                if path_str not in req.image_urls:
                    req.image_urls.append(path_str)
                    appended += 1
            current_prompt = getattr(req, "prompt", "")
            req.prompt = self._inject_preview_hint(current_prompt, appended)
            logger.info(
                f"[{self.PLUGIN_NAME}] 已注入 {appended} 帧 GIF 预览图片，帮助 LLM 理解动图。"
            )
        else:
            current_prompt = getattr(req, "prompt", "")
            req.prompt = self._inject_preview_hint(current_prompt, 0)
            logger.warning(
                f"[{self.PLUGIN_NAME}] 无法生成 GIF 预览帧，仅在 prompt 中记录已转换。"
            )
