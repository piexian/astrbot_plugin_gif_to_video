# AstrBot GIF转视频插件 v2.0.4 发布公告

## 🎉 版本更新

我们很高兴地宣布 AstrBot GIF转视频插件 v2.0.4 已发布！

## 🐛 问题修复

### MoviePy 2.2.1+ 版本兼容性问题
- **修复了** `TypeError: got an unexpected keyword argument 'verbose'` 错误
- **实现了** 自适应版本兼容机制，确保插件在不同 MoviePy 版本间稳定运行
- **支持** MoviePy 1.0.3 到 2.2.1+ 的所有版本

### 错误处理改进
- **增强了** 错误处理机制，提供更详细的版本兼容性日志
- **优化了** GIF 转换流程，提高稳定性
- **确保了** 插件在各种环境下的可靠性

## 🔧 技术细节

本次更新主要解决了 MoviePy 库版本升级导致的兼容性问题。新版本的 MoviePy (2.2.1+) 移除了 `verbose` 和 `logger` 参数，导致插件在处理 GIF 转换时出现错误。

我们的解决方案：
1. 优先尝试使用新版本 MoviePy 的参数（不包含 `verbose` 和 `logger`）
2. 如果检测到参数错误，自动回退到旧版本参数
3. 记录详细的兼容性日志，便于问题排查

## 📦 更新建议

如果您遇到了以下错误，请立即更新到此版本：
```
TypeError: got an unexpected keyword argument 'verbose'
```

## 🚀 如何更新

1. 通过 AstrBot 插件市场搜索 `gif转视频插件` 并更新到最新版本
2. 或者手动拉取最新代码：
   ```bash
   cd /AstrBot/data/plugins/astrbot_plugin_gif_to_video
   git pull origin main
   ```

## 🙏 致谢

感谢用户反馈的兼容性问题，这帮助我们快速定位并修复了问题。

## 📞 支持

如果您在使用过程中遇到任何问题，请通过以下方式联系我们：
- 提交 Issue: https://github.com/piexian/astrbot_plugin_gif_to_video/issues
- 查看 README.md 中的故障排除指南

---

**发布日期**: 2025-10-19  
**版本**: v2.0.4  
**兼容性**: AstrBot v4.3.5+, MoviePy 1.0.3-2.2.1+