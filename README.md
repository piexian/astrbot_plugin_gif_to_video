# AstrBot GIF转视频插件 (astrbot_plugin_gif_to_video)

一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的 GIF 格式转换插件。它会自动将用户发送的 GIF 动图转换为 MP4 视频格式并发送llm。


## ✨ 核心功能

-   **🚀 自动转换**: 插件在后台运行，使用 `MoviePy` (FFmpeg) 快速将 GIF 转换为 MP4 视频。
-   **🔧 无缝配置**: 完全集成于 AstrBot 的 WebUI，提供简单直观的配置选项。

## 🎯 使用场景

为什么需要将 GIF 转换为视频？

-   **平台兼容性**: Gemini不支持 GIF 的接受，转换为视频后可以确保能正常进行。


## 📦 安装

-   可以直接在 AstrBot 的插件市场搜索 `gif转视频插件` 或 `astrbot_plugin_gif_to_video`，点击安装即可。
-   或者可以克隆源码到插件文件夹：
    
    ```bash
    cd /AstrBot/data/plugins
    git clone https://github.com/piexian/astrbot_plugin_gif_to_video.git
    ```
    安装后，请重启 AstrBot。

### ⚠️ 前置依赖：FFmpeg

**本插件的正常运行依赖于 FFmpeg 程序。** AstrBot 默认环境和 Docker 镜像中**不包含**此依赖，您需要手动安装。

-   **对于 Docker 用户：**
    请在您的 Docker环境内手动输入指令安装
    或者自行build带ffmpeg的镜像  

-   **对于直接部署的用户：**
    请使用您服务器的包管理器进行安装：
    ```bash
    # Debian / Ubuntu
    sudo apt-get install ffmpeg
    ```
    ```bash
    # CentOS / RHEL
    sudo yum install ffmpeg
    ```
安装 FFmpeg 后，请**重启 AstrBot** 以确保插件能够正确加载。

## 本地测试

如果你想在没有完整 AstrBot 环境下测试 GIF->MP4 转换，可以使用仓库内的脚本：

```powershell
# 安装依赖（建议在虚拟环境中）
pip install -r requirements.txt

# 使用样例：
python scripts/test_convert.py sample.gif sample.mp4
```

或者运行 pytest 的轻量测试（不会真正调用 moviepy 转换大文件）：

```powershell
pytest -q
```

## 🛠️ 配置指南

插件的配置非常简单，旨在控制它何时触发转换。

| 配置项                | 说明                                                                                                                            | 默认值      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `enabled_provider_id` | 指定一个服务商 ID。插件将**仅**在该服务商被调用时触发转换。如果留空，插件将在**默认服务商**被调用时触发。 | `""` (空)   |

### 工作模式说明

-   **自动模式 (默认)**:
    -   **条件**: `enabled_provider_id` 配置项留空。
    -   **行为**: 当用户发送 GIF，并且该消息的目标是 AstrBot 的**全局默认服务商**时，插件会自动进行转换。
    -   **场景**: 适用于大多数简单场景，让插件响应默认模型的调用。

-   **手动模式 (指定服务商)**:
    -   **条件**: 在 `enabled_provider_id` 中选择了一个具体服务商。
    -   **行为**: 插件将只在用户请求**您所指定的服务商**时，才会对 GIF 进行转换。
    -   **场景**: 如果您希望仅在特定模型（例如一个专门的识图模型）被调用时才转换 GIF，可以使用此模式进行精确控制。

---

## ⚠️ AI 生成声明

本插件的核心代码由 **GeminiAI** 在与 **氕氙** 的合作与指导下生成。
