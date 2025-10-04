"""本地测试脚本：手动把 gif 转换为 mp4，不依赖 AstrBot 环境。
用法:
    python scripts/test_convert.py input.gif output.mp4
"""
import sys
from pathlib import Path
from moviepy.editor import VideoFileClip


def gif_to_mp4(input_path: str, output_path: str):
    with VideoFileClip(input_path) as clip:
        fps = clip.fps if clip.fps is not None else 15
        clip.write_videofile(output_path, codec="libx264", audio=False, fps=fps)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_convert.py input.gif output.mp4")
        raise SystemExit(2)
    inp = sys.argv[1]
    out = sys.argv[2]
    if not Path(inp).exists():
        print(f"Input not found: {inp}")
        raise SystemExit(1)
    gif_to_mp4(inp, out)
    print(f"Converted {inp} -> {out}")
