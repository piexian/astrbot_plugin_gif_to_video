"""Tests for the GIF to Video plugin functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the plugin directory to the path
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

# Mock astrbot modules
import types

astrbot = types.ModuleType("astrbot")
astrbot.api = types.ModuleType("astrbot.api")
astrbot.api.AstrBotConfig = dict
astrbot.api.logger = Mock()
astrbot.api.event = types.ModuleType("astrbot.api.event")
astrbot.api.event.filter = types.ModuleType("astrbot.api.event.filter")
astrbot.api.event.AstrMessageEvent = object
astrbot.api.star = types.ModuleType("astrbot.api.star")
astrbot.api.star.Context = object
astrbot.api.star.Star = object
astrbot.api.star.register = lambda *args: lambda cls: cls
astrbot.api.message_components = types.ModuleType("astrbot.api.message_components")

sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = astrbot.api
sys.modules["astrbot.api.event"] = astrbot.api.event
sys.modules["astrbot.api.event.filter"] = astrbot.api.event.filter
sys.modules["astrbot.api.star"] = astrbot.api.star
sys.modules["astrbot.api.message_components"] = astrbot.api.message_components

# Mock moviepy to avoid heavy dependencies
moviepy = types.ModuleType("moviepy")
moviepy.editor = types.ModuleType("moviepy.editor")


class MockVideoFileClip:
    def __init__(self, path):
        self.path = path
        self.fps = 15

    def write_videofile(self, output_path, **kwargs):
        # Create a dummy file
        Path(output_path).write_bytes(b"dummy video content")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


moviepy.editor.VideoFileClip = MockVideoFileClip
sys.modules["moviepy"] = moviepy
sys.modules["moviepy.editor"] = moviepy.editor

# Mock aiohttp
aiohttp = types.ModuleType("aiohttp")


class MockClientSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def get(self, url):
        mock_response = Mock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.read = AsyncMock(return_value=b"dummy gif content")
        return mock_response


aiohttp.ClientSession = MockClientSession
sys.modules["aiohttp"] = aiohttp

# Now import the plugin
try:
    from main import GifToVideoPlugin, _blocking_gif_to_mp4
except ImportError as e:
    pytest.skip(f"Cannot import plugin: {e}", allow_module_level=True)


class TestGifToVideoPlugin:
    """Test cases for the GIF to Video plugin."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = Mock()
        context.provider_manager = Mock()
        context.provider_manager.curr_provider_inst = Mock()
        context.provider_manager.get_all_providers.return_value = {
            "openai": context.provider_manager.curr_provider_inst
        }
        context.get_using_provider = Mock(
            return_value=context.provider_manager.curr_provider_inst
        )
        return context

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        return {"enabled_provider_id": ""}

    @pytest.fixture
    def plugin(self, mock_context, mock_config):
        """Create a plugin instance."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            return GifToVideoPlugin(mock_context, mock_config)

    def test_plugin_initialization_auto_mode(self, mock_context):
        """Test plugin initialization in auto mode."""
        config = {"enabled_provider_id": ""}
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            plugin = GifToVideoPlugin(mock_context, config)

        assert plugin.ffmpeg_available is True
        assert plugin.default_provider_id == "openai"

    def test_plugin_initialization_manual_mode(self, mock_context):
        """Test plugin initialization in manual mode."""
        config = {"enabled_provider_id": "test_provider"}
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            plugin = GifToVideoPlugin(mock_context, config)

        assert plugin.ffmpeg_available is True
        assert plugin.config.get("enabled_provider_id") == "test_provider"

    def test_plugin_initialization_no_ffmpeg(self, mock_context, mock_config):
        """Test plugin initialization when FFmpeg is not available."""
        with patch("shutil.which", return_value=None):
            plugin = GifToVideoPlugin(mock_context, mock_config)

        assert plugin.ffmpeg_available is False

    def test_get_default_provider_id(self, plugin):
        """Test getting the default provider ID."""
        provider_id = plugin._get_default_provider_id()
        assert provider_id == "openai"

    def test_get_default_provider_id_no_provider(self, plugin):
        """Test getting the default provider ID when no provider is available."""
        plugin.context.provider_manager.curr_provider_inst = None
        provider_id = plugin._get_default_provider_id()
        assert provider_id is None

    @pytest.mark.asyncio
    async def test_handle_gif_message_no_ffmpeg(self, plugin):
        """Test handling GIF message when FFmpeg is not available."""
        plugin.ffmpeg_available = False

        mock_event = Mock()
        mock_request = Mock()

        # Should return early without processing
        result = await plugin.handle_gif_message(mock_event, mock_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_gif_message_no_gif(self, plugin):
        """Test handling message without GIF."""
        # Mock message components with no GIF
        mock_image = Mock()
        mock_image.file = "test.jpg"
        mock_image.url = "https://example.com/test.jpg"

        mock_event = Mock()
        mock_event.message_obj.message = [mock_image]
        mock_event.unified_msg_origin = "test:group:test"

        mock_request = Mock()
        mock_request.provider_id = "openai"

        with patch.object(plugin, "default_provider_id", "openai"):
            result = await plugin.handle_gif_message(mock_event, mock_request)

        # Should return early without processing
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_gif_message_with_gif_file(self, plugin):
        """Test handling message with GIF file."""
        # Mock message components with GIF
        mock_image = Mock()
        mock_image.file = "test.gif"
        mock_image.url = "https://example.com/test.gif"

        mock_event = Mock()
        mock_event.message_obj.message = [mock_image]
        mock_event.unified_msg_origin = "test:group:test"

        mock_request = Mock()
        mock_request.provider_id = "openai"
        mock_request.prompt = "测试消息 [图片]"

        with patch.object(plugin, "default_provider_id", "openai"):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("shutil.copy2"):
                    with patch.object(
                        plugin, "_get_default_provider_id", return_value="openai"
                    ):
                        result = await plugin.handle_gif_message(
                            mock_event, mock_request
                        )

        # Should process the GIF
        assert result is None
        assert hasattr(mock_request, "image_urls")
        assert len(mock_request.image_urls) > 0
        assert "[视频(GIF已转换)]" in mock_request.prompt

    @pytest.mark.asyncio
    async def test_handle_gif_message_with_gif_url(self, plugin):
        """Test handling message with GIF URL."""
        # Mock message components with GIF URL
        mock_image = Mock()
        mock_image.file = None
        mock_image.url = "https://example.com/test.gif"

        mock_event = Mock()
        mock_event.message_obj.message = [mock_image]
        mock_event.unified_msg_origin = "test:group:test"

        mock_request = Mock()
        mock_request.provider_id = "openai"
        mock_request.prompt = "测试消息 [图片]"

        with patch.object(plugin, "default_provider_id", "openai"):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = Mock()
                mock_response = Mock()
                mock_response.raise_for_status = AsyncMock()
                mock_response.read = AsyncMock(return_value=b"dummy gif content")
                mock_session.get.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session
                mock_session_class.return_value.__aexit__.return_value = None

                with patch.object(
                    plugin, "_get_default_provider_id", return_value="openai"
                ):
                    result = await plugin.handle_gif_message(mock_event, mock_request)

        # Should process the GIF
        assert result is None
        assert hasattr(mock_request, "image_urls")
        assert len(mock_request.image_urls) > 0
        assert "[视频(GIF已转换)]" in mock_request.prompt

    @pytest.mark.asyncio
    async def test_handle_gif_message_provider_not_enabled(self, plugin):
        """Test handling GIF message when provider is not enabled."""
        # Mock message components with GIF
        mock_image = Mock()
        mock_image.file = "test.gif"
        mock_image.url = "https://example.com/test.gif"

        mock_event = Mock()
        mock_event.message_obj.message = [mock_image]
        mock_event.unified_msg_origin = "test:group:test"

        mock_request = Mock()
        mock_request.provider_id = "different_provider"

        # Configure plugin for specific provider
        plugin.config = {"enabled_provider_id": "specific_provider"}

        with patch.object(plugin, "default_provider_id", "openai"):
            result = await plugin.handle_gif_message(mock_event, mock_request)

        # Should return early without processing
        assert result is None
        assert not hasattr(mock_request, "image_urls")

    @pytest.mark.asyncio
    async def test_terminate(self, plugin):
        """Test plugin termination."""
        result = await plugin.terminate()
        assert result is None


class TestGifConversion:
    """Test cases for the GIF conversion function."""

    @pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
    def test_blocking_gif_to_mp4(self):
        """Test the blocking GIF to MP4 conversion function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a minimal GIF file
            gif_path = Path(temp_dir) / "test.gif"
            gif_path.write_bytes(
                b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
                b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
                b"\x00\x02\x02D\x01\x00;"
            )

            mp4_path = Path(temp_dir) / "test.mp4"

            # This should not raise an exception
            _blocking_gif_to_mp4(str(gif_path), str(mp4_path))

            # Check that the output file was created
            assert mp4_path.exists()
            assert mp4_path.stat().st_size > 0
