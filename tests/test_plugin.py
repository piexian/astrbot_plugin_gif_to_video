"""Tests for the GIF to Video plugin functionality."""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add the plugin directory to the path
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))


# Setup module mocks using pytest fixtures for cleaner code
@pytest.fixture(autouse=True)
def setup_module_mocks(mocker):
    """Setup all necessary module mocks for testing."""
    # Mock astrbot modules
    mock_astrbot = Mock()
    mock_astrbot.api = Mock()
    mock_astrbot.api.AstrBotConfig = dict
    mock_astrbot.api.logger = Mock()
    mock_astrbot.api.event = Mock()
    mock_astrbot.api.event.filter = Mock()
    mock_astrbot.api.event.AstrMessageEvent = object
    mock_astrbot.api.star = Mock()
    mock_astrbot.api.star.Context = object
    mock_astrbot.api.star.Star = object
    mock_astrbot.api.star.register = lambda *args: lambda cls: cls
    mock_astrbot.api.message_components = Mock()

    mocker.patch.dict(
        sys.modules,
        {
            "astrbot": mock_astrbot,
            "astrbot.api": mock_astrbot.api,
            "astrbot.api.event": mock_astrbot.api.event,
            "astrbot.api.event.filter": mock_astrbot.api.event.filter,
            "astrbot.api.star": mock_astrbot.api.star,
            "astrbot.api.message_components": mock_astrbot.api.message_components,
        },
    )

    # Mock moviepy to avoid heavy dependencies
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

    mock_moviepy = Mock()
    mock_moviepy.editor = Mock()
    mock_moviepy.editor.VideoFileClip = MockVideoFileClip

    mocker.patch.dict(
        sys.modules,
        {
            "moviepy": mock_moviepy,
            "moviepy.editor": mock_moviepy.editor,
        },
    )

    # Mock aiohttp
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

    mock_aiohttp = Mock()
    mock_aiohttp.ClientSession = MockClientSession

    mocker.patch.dict(
        sys.modules,
        {
            "aiohttp": mock_aiohttp,
        },
    )

    # Now import the plugin after all mocks are in place
    try:
        from main import GifToVideoPlugin, _blocking_gif_to_mp4

        return GifToVideoPlugin, _blocking_gif_to_mp4
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
    def plugin(self, mock_context, mock_config, setup_module_mocks):
        """Create a plugin instance."""
        GifToVideoPlugin, _ = setup_module_mocks
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            return GifToVideoPlugin(mock_context, mock_config)

    def test_plugin_initialization_auto_mode(self, mock_context, setup_module_mocks):
        """Test plugin initialization in auto mode."""
        GifToVideoPlugin, _ = setup_module_mocks
        config = {"enabled_provider_id": ""}
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            plugin = GifToVideoPlugin(mock_context, config)

        assert plugin.ffmpeg_available is True
        assert plugin.default_provider_id == "openai"

    def test_plugin_initialization_manual_mode(self, mock_context, setup_module_mocks):
        """Test plugin initialization in manual mode."""
        GifToVideoPlugin, _ = setup_module_mocks
        config = {"enabled_provider_id": "test_provider"}
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            plugin = GifToVideoPlugin(mock_context, config)

        assert plugin.ffmpeg_available is True
        assert plugin.config.get("enabled_provider_id") == "test_provider"

    def test_plugin_initialization_no_ffmpeg(
        self, mock_context, mock_config, setup_module_mocks
    ):
        """Test plugin initialization when FFmpeg is not available."""
        GifToVideoPlugin, _ = setup_module_mocks
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
    async def test_handle_gif_message_with_gif_file(self, plugin, tmp_path):
        """Test handling message with GIF file."""
        # Create a real temporary GIF file
        gif_file_path = tmp_path / "test.gif"
        gif_file_path.write_bytes(b"dummy_gif_content")

        # Mock message components with GIF
        mock_image = Mock()
        mock_image.file = str(gif_file_path)
        mock_image.url = "https://example.com/test.gif"

        mock_event = Mock()
        mock_event.message_obj.message = [mock_image]
        mock_event.unified_msg_origin = "test:group:test"

        mock_request = Mock()
        mock_request.provider_id = "openai"
        mock_request.prompt = "测试消息 [图片]"

        with patch.object(plugin, "default_provider_id", "openai"):
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
        # 注意：terminate方法现在是同步的
        result = plugin.terminate()
        assert result is None
