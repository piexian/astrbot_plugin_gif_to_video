# 更新日志

所有重要的项目更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

[2.0.2]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/piexian/astrbot_plugin_gif_to_video/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/piexian/astrbot_plugin_gif_to_video/releases/tag/v2.0.0