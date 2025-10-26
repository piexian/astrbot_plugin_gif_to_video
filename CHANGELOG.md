# 更新日志

所有重要的项目更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.3.0] - 2025-02-16

### 改动
- **功能聚焦**：移除已失效的 Gemini 视频分析与 FFmpeg 拆轨逻辑，插件专注于 GIF → MP4 转换 + 多帧预览注入。
- **配置简化**：删除全部 Gemini 相关配置项，仅保留 `enabled_provider_id` 与 `preview_frame_count`。
- **依赖声明**：恢复 `requirements.txt`，确保自动安装 MoviePy/aiohttp/Pillow 等依赖。
- **文档同步**：更新 README 与 metadata 描述，突出“多帧预览”能力。

### 修复
- 解决删除 `gemini_content.py`、`videos_cliper.py` 后 `main.py` 仍引用导致的 `ModuleNotFoundError`。

## [2.2.0] - 2025-02-16

### 新增
- **GIF 预览帧注入**：为非 Gemini 服务商自动抽取多帧 PNG，并随请求发送，帮助 LLM 理解整段动图。
- **配置项**：新增 `preview_frame_count`，可自定义预览帧数量。

### 改进
- **请求流程**：在 on_llm_request 中使用 `event.send + plain_result`，进度提示和异常通知不再报错。
- **缓存体系**：统一管理视频与帧缓存，自动过期清理，复用转换结果。
- **Provider 识别**：重写 provider 映射与检测逻辑，兼容 `inst_map` / `get_all_providers` 等多种路径，Gemini 检测更可靠。
- **自动模式**：当无法直接获取 provider id 时，回退到实例比对，确保默认服务商能够识别。

### 修复
- **Gemini 检测**：修正 `_is_gemini_provider` 中对不存在的 `context.get_provider` 的调用，避免永远判定为非 Gemini。
- **提示词损坏**：替换错误的 `event.make_result().plain_result(...)` 调用，修复在分析阶段无法发送提示的问题。
- **版本字段**：同步 metadata/register 版本号至 `2.2.0`，与实际功能保持一致。

## [2.1.2] - 2025-10-19

### 修复
- **Provider ID 匹配逻辑**: 改进 `_get_provider_id_by_instance` 方法，修复无法正确匹配 provider 实例的问题
- **调试信息增强**: 添加详细的调试日志，包括 provider 类型、属性和可用 provider 列表
- **实例匹配优化**: 使用 `is` 比较和类型匹配来正确识别 provider ID
- **回退机制**: 当直接获取 ID 失败时，通过遍历所有 providers 进行匹配

### 改进
- **调试能力**: 大幅增强问题排查能力，提供完整的 provider 信息
- **兼容性**: 改进对不同类型 provider 的兼容性
- **错误恢复**: 增强在 provider 获取失败时的恢复能力

## [2.1.1] - 2025-10-19

### 修复
- **Provider ID 获取**: 修复无法正确获取 provider_id 导致插件跳过处理的问题
- **API 兼容性**: 适配 AstrBot 框架的最新 API，使用 `get_using_provider(umo=event.unified_msg_origin)`
- **属性检测**: 改进 provider 对象属性检测，支持 `provider_id` 和 `id` 两种属性名
- **调试日志**: 增强调试日志输出，便于问题排查

### 改进
- **错误处理**: 改进 provider 获取失败时的错误处理逻辑
- **代码健壮性**: 提升代码在不同 AstrBot 版本下的兼容性
- **日志详细度**: 增加更详细的调试信息

## [2.1.0] - 2025-10-19

### 新增
- 添加智能模型选择和自动回退机制
- 新增模型能力验证系统
- 支持自定义Gemini模型配置
- 添加模型描述和代数信息

### 改进
- 根据模型类型自动优化超时时间设置
- 增强错误处理，添加ModelValidationError异常类型
- 改进日志记录，包含模型选择和回退信息
- 优化文档注释，修正不一致的默认值描述
- 更新视频处理方式，使用base64 inline_data上传（兼容Gemini 2.5）
- 添加文件大小验证，防止超过API限制

### 性能优化
- 根据模型能力动态调整请求参数
- 减少不必要的模型验证调用
- 优化视频文件处理流程，直接使用base64编码

### 修复
- 修正文档注释中模型默认值的不一致问题
- 修复硬编码模型名称导致的可维护性问题
- 修复配置文件兼容性问题（boolean→bool, integer→int）
- 修复视频上传方式，改为Gemini 2.5兼容的base64 inline_data方式

## [2.0.8] - 2025-10-19

### 修复
- 修复获取provider_id的问题，移除get_using_provider()方法中不正确的umo参数
- 添加异常处理，避免获取provider失败时插件崩溃
- 将警告日志改为调试日志，减少日志噪音

### 改进
- 使用框架提供的正确API获取当前使用的provider
- 提高插件在获取provider信息失败时的健壮性

## [2.0.7] - 2025-10-19

### 修复
- 修复terminate方法兼容性问题，将方法从同步改回异步以满足框架期望
- 解决'object NoneType can't be used in 'await' expression'错误
- 更新测试文件以匹配异步方法调用

### 改进
- 保持方法内部执行同步操作，不包含任何await调用
- 确保插件能够正常终止，避免插件运行不正常

## [2.0.6] - 2025-10-19

### 修复
- 修复数据持久化问题，使用框架提供的StarTools.get_data_dir()替代硬编码的临时目录
- 改进资源管理，在handle_gif_message中使用try...finally确保临时文件清理
- 修复代码质量问题，将terminate方法改为同步方法
- 优化可维护性，减少与provider_manager内部实现的耦合
- 移除重复的测试代码，整合测试用例到test_conversion.py

### 改进
- 使用框架提供的稳定API获取provider信息，提高代码健壮性
- 增强临时文件清理机制，确保每次请求后立即清理资源
- 改进错误处理和日志记录，提供更好的调试信息
- 优化测试结构，消除重复测试代码

## [2.0.5] - 2025-10-19

### 修复
- 修复了临时文件生命周期管理问题，解决了 `FileNotFoundError` 错误
- 实现了智能缓存机制，转换后的视频文件会缓存24小时
- 修复了因临时目录过早删除导致的文件访问失败问题

### 新增
- 添加了基于MD5哈希的缓存系统，相同GIF文件只需转换一次
- 实现了自动过期缓存清理机制，避免磁盘空间浪费
- 缓存文件保存24小时，提高重复请求的响应速度

### 改进
- 优化了临时文件管理，使用持久化临时目录
- 改进了缓存命中时的处理逻辑，提高效率
- 增强了文件生命周期管理，确保文件在需要时始终可用

## [2.0.4] - 2025-10-19

### 修复
- 修复了 MoviePy 2.2.1+ 版本兼容性问题
- 解决了 `TypeError: got an unexpected keyword argument 'verbose'` 错误
- 实现了自适应版本兼容机制，优先使用新版本参数，失败时回退到旧版本参数
- 增强了插件对不同 MoviePy 版本的兼容性

### 改进
- 改进了错误处理机制，提供更详细的版本兼容性日志
- 优化了 GIF 转换流程，提高稳定性
- 确保插件在 MoviePy 1.0.3 到 2.2.1+ 版本范围内都能正常工作

## [2.0.3] - 2025-10-19

### 修复
- 修复了获取服务商ID的重复代码问题，创建了`_get_provider_id_by_instance()`辅助方法
- 修复了转换后的视频被添加到请求但原始GIF图片组件未被移除的问题
- 修复了tests/test_conversion.py中的测试逻辑错误，现在真正执行GIF到MP4转换
- 优化了tests/test_plugin.py中的模块模拟代码，使用pytest-mock简化模拟设置
- 修复了部分测试用例的模拟不完整问题，使用真实临时文件进行测试

### 改进
- 提高了代码的可维护性和可读性
- 增强了测试的健壮性和可靠性
- 消除了代码重复，遵循DRY原则
- 改进了请求处理逻辑，确保消息纯净性

## [2.0.2] - 2024-10-18

### 修复
- 修复了moviepy 2.x版本兼容性问题
- 添加了多版本moviepy导入支持，兼容1.0.3到2.1.2+版本
- 解决了`ModuleNotFoundError: No module named 'moviepy.editor'`错误
- 改进了导入错误处理机制，提高了插件的健壮性

### 改进
- 采用渐进式导入策略，优先尝试兼容的导入方式
- 增强了版本兼容性，支持更广泛的moviepy版本范围

## [2.0.1] - 2024-10-18

### 修复
- 修复了插件不触发的问题
- 更新了事件处理器，使用 `@filter.on_llm_request` 替代 `@filter.event_message_type`
- 改进了GIF检测逻辑，支持更多消息格式
- 添加了详细的调试日志
- 优化了错误处理机制
- 修复了代码中的重复导入问题

### 改进
- 增强了配置系统的兼容性
- 优化了GIF转换性能
- 改进了日志输出的可读性
- 增强了临时文件管理

### 文档
- 更新了README.md
- 添加了详细的调试指南
- 完善了故障排除部分

## [2.0.0] - 2024-XX-XX

### 新增
- 初始版本发布
- 支持GIF到MP4的转换
- 支持自动和手动配置模式
- 支持本地文件和网络URL
- 完整的错误处理机制

### 特性
- 使用MoviePy进行视频转换
- 异步处理避免阻塞
- 临时文件自动清理
- 详细的日志记录

[2.1.0]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.8...v2.1.0
[2.0.8]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.7...v2.0.8
[2.0.7]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.6...v2.0.7
[2.0.6]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.5...v2.0.6
[2.0.5]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.4...v2.0.5
[2.0.4]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/piexian/astrbot_plugin_gif_to_video/releases/tag/v2.0.0
