# AstrBot GIF转视频插件 (astrbot_plugin_gif_to_video)

一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的 GIF 格式转换插件。它会自动将用户发送的 GIF 动图转换为 MP4 视频格式，以便发送给不支持GIF格式的LLM服务商（如Gemini）。

## ✨ 核心功能

-   **🚀 自动转换**: 插件在后台运行，使用 `MoviePy` (FFmpeg) 快速将 GIF 转换为 MP4 视频。
-   **🔧 无缝配置**: 完全集成于 AstrBot 的 WebUI，提供简单直观的配置选项。
-   **🎯 智能检测**: 自动检测消息中的GIF内容，无需手动触发。
-   **📝 详细日志**: 提供详细的调试日志，方便排查问题。

## 🎯 使用场景

为什么需要将 GIF 转换为视频？

-   **平台兼容性**: 某些LLM服务商（如Gemini）不支持 GIF 格式的输入，转换为视频后可以确保能正常进行分析。
-   **减少错误**: 避免因GIF格式不兼容导致的LLM请求失败。

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
    ```bash
    # Windows (使用 Chocolatey)
    choco install ffmpeg
    ```
    ```bash
    # Windows (使用 Scoop)
    scoop install ffmpeg
    ```
安装 FFmpeg 后，请**重启 AstrBot** 以确保插件能够正确加载。

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

## 🔧 故障排除

### 插件不工作？

1.  **检查日志**: 查看 AstrBot 的日志输出，寻找 `[astrbot_plugin_gif_to_video]` 标记的日志信息。
2.  **确认FFmpeg安装**: 在终端中运行 `ffmpeg -version` 确认FFmpeg已正确安装。
3.  **检查配置**: 确认插件配置是否正确，特别是 `enabled_provider_id` 设置。
4.  **确认服务商**: 确认您使用的LLM服务商确实不支持GIF格式（如Gemini）。

### 常见问题

**Q: 为什么插件没有反应？**
A: 请检查日志中是否有 `[astrbot_plugin_gif_to_video] 收到LLM请求，检查是否包含GIF` 的信息。如果没有，说明插件可能没有正确加载。

**Q: 转换失败怎么办？**
A: 检查日志中的错误信息，可能是网络问题或GIF文件损坏。

**Q: 可以转换本地GIF文件吗？**
A: 是的，插件支持转换本地GIF文件和网络GIF链接。

## 🧪 测试

### 本地测试

如果你想在没有完整 AstrBot 环境下测试 GIF->MP4 转换，可以使用仓库内的测试：

```bash
# 安装依赖（建议在虚拟环境中）
pip install -r requirements.txt

# 运行测试
pytest -q
```

### 在AstrBot中测试

1.  确保插件已正确安装并启用
2.  发送一个GIF图片给机器人
3.  查看日志确认插件是否被触发
4.  确认LLM是否能够正确处理转换后的视频

---

## ⚠️ AI 生成声明

本插件的核心代码由 **GeminiAI** 在与 **氕氙** 的合作与指导下生成。

## 📝 更新日志

### v2.0.1
- 修复了插件不触发的问题
- 更新了事件处理器，使用 `@filter.on_llm_request` 替代 `@filter.event_message_type`
- 改进了GIF检测逻辑，支持更多消息格式
- 添加了详细的调试日志
- 优化了错误处理机制
