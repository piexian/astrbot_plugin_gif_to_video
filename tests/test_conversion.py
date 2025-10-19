"""pytest tests for conversion logic. This test is lightweight and will skip if moviepy isn't installed or ffmpeg missing."""

import sys
from pathlib import Path

# Add the plugin directory to the path
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

import shutil
import pytest


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_gif_to_mp4_conversion(tmp_path):
    """Test the actual GIF to MP4 conversion function."""
    # Import the conversion function
    try:
        from main import _blocking_gif_to_mp4
    except ImportError:
        pytest.skip("Cannot import _blocking_gif_to_mp4 function", allow_module_level=True)
    
    # Create a tiny GIF file
    in_path = tmp_path / "in.gif"
    out_path = tmp_path / "out.mp4"
    in_path.write_bytes(
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )
    
    # Verify input file exists and has content
    assert in_path.exists()
    assert in_path.stat().st_size > 0
    
    # Run the actual conversion
    _blocking_gif_to_mp4(str(in_path), str(out_path))
    
    # Verify output file was created and has content
    assert out_path.exists()
    assert out_path.stat().st_size > 0
