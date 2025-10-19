# 更新日志

所有重要的项目更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

[2.0.4]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/piexian/astrbot_plugin_gif_to_video/releases/tag/v2.0.0