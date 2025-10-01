# 🤖  AstrBot gif转视频插件（astrbot_plugin_gif_to_video）


> ⚠️ **重要提示**
>
> <font color="red">本插件目前仅在 **NapCat (aiocqhttp)** 平台上，针对 **Google Gemini** 模型进行了完整测试。在其他平台或与其他模型一同使用时，可能存在未知问题。</font>

一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的gif适配插件。它通过 `MoviePy` (FFmpeg)将gif转换为视频，为您的Google Gemini大语言模型启用gif完整读取功能（主要是防止报错）。

## ✨ 核心特性

-   **✨ 智能双模**: 无需配置即可为您的默认模型工作，同时为高级用户提供强大的自定义能力。
-   **🚀 高效转换**: 在后台使用 `MoviePy` (FFmpeg) 将 gif 快速转换为视频，解锁模型的动态视觉。
-   **🔧 WebUI 原生配置**: 完全集成于 AstrBot 的 WebUI，提供无缝、友好的配置体验。
-   **🌐 提示词策略**: 默认使用高效的英文提示词，同时提供可选的自动翻译功能，方便使用中文编写复杂指令。
-   **💰 成本优化**: 您可以指定一个独立的、更经济的模型专门用于执行翻译任务，节约成本。

## 📦 安装

-   可以直接在 AstrBot 的插件市场搜索 `gif转视频分析插件`或者 `astrbot_plugin_gif_to_video`，点击安装即可。

-   或者可以直接克隆源码到插件文件夹：
    
    ```bash
    
    cd /AstrBot/data/plugins
    git clone https://github.com/piexian/astrbot_plugin_gif_to_video.git
    
    ```
    控制台重启 AstrBot
    
### ⚠️ 前置依赖：FFmpeg

**本插件的正常运行依赖于FFmpeg程序。** 
AstrBot 默认项目和Docker镜像中**不包含**此依赖，您很可能需要手动安装。

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
安装FFmpeg后，请**重启AstrBot** 以确保插件能够正常工作。
其他依赖详见 requirements.txt

## 📁 文件结构

```
📂 /astrbot_plugin_gif_to_video
├── main.py           (核心逻辑)
├── _conf_schema.json (WebUI 配置)
├── requirements.txt  (依赖)
├── README.md         (说明文档)
└── metadata.yaml     (插件市场元说明文档)
```

## 🚀 工作模式

本插件拥有两种智能工作模式，旨在提供最佳的用户体验。

### 1. 自动模式 (默认)

-   **触发条件**: 您没有在本插件的配置页面中添加任何服务商 ID（即 `enabled_providers` 列表为空）。
-   **行为**: 插件会自动检测 AstrBot 的**全局默认服务商**。当用户发送 gif，并且需要由这个默认服务商处理时，插件会自动进行转换和分析。
-   **优势**: **安装即用！** 对于大多数只使用一个核心模型的用户来说，无需任何额外配置。

### 2. 手动模式 (自定义)

-   **触发条件**: 您在本插件的配置页面中，向 `enabled_providers` 列表里添加了**至少一个**服务商 ID。
-   **行为**: 插件将切换到严格的白名单模式，**仅为**您列表中指定的服务商启用gif转换分析功能。
-   **优势**: 提供了最大快捷的自定义。

## 🛠️ 配置指南

> ⚠️ **重要配置提示**
>
> 如果您的默认聊天模型**不是**可以进行识图模型（例如，您使用DeepSeek聊天，但使用Gemini进行识图），**自动模式将无法正常工作**。
>
> 在这种情况下，您**必须**在插件配置的 `enabled_providers` 列表中，明确填入您的Gemini的服务商ID（仅适配Gemini）。

### 提示词策略

-   **默认行为**: 插件默认使用一个内置的、优化过的**英文提示词**进行分析，以获得最佳效果。
-   **如何使用中文提示词**:
    1.  在插件配置中，将 `custom_prompt` 的内容修改为您自己的**中文提示词**。
    2.  勾选 `auto_translate_prompt` 选项，插件会自动将您的中文提示词翻译为英文后再发送给模型。

### ⚙️ 配置选项

| 配置项                      | 说明                                                         | 默认值                                                       |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `auto_translate_prompt`     | 是否将您的自定义提示词翻译为英语。默认关闭。 | `false`                                                      |
| `custom_prompt`             | 自定义分析指令。默认使用英文。若需使用中文，请填写并开启翻译。 | `Please describe the dynamic content... Please reply in Chinese.` |
| `translation_provider_id`   | 用于翻译提示词的专用服务商。留空则使用主模型。 | `""` (空)                                                    |
| `translation_model_name`    |  翻译服务商使用的具体模型名称。              | `""` (空)                                                    |
| `fallback_to_main_provider` | 翻译失败时是否回退到主模型再次尝试。                         | `true`                                                       |
| `enabled_providers`         | 【手动模式】启用 gif 分析的 LLM 服务商 ID 列表。留空则进入【自动模式】。 | `[]` (自动模式)                                              |

## 📦 依赖管理

为确保插件的稳定运行你需要

-   `moviepy>=1.0.3`
-   `aiohttp>=3.9.5`

默认无需配置

---

## ⚠️ AI 生成声明

本插件的核心代码由 **GeminiAI** 在与 **piexian** 的深度合作与指导下生成。代码经过了多次迭代和优化，以确保其遵循 AstrBot 插件开发的最佳实践。尽管如此，仍建议在部署前进行代码审查。
