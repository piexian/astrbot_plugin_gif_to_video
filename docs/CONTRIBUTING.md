# 贡献指南

感谢您对AstrBot GIF转视频插件的关注！我们欢迎各种形式的贡献，包括但不限于报告错误、提出功能请求、改进文档和提交代码更改。

## 如何贡献

### 报告错误

如果您发现了错误，请：

1. 检查[Issues](https://github.com/piexian/astrbot_plugin_gif_to_video/issues)页面，确认错误尚未被报告
2. 创建一个新的Issue，使用"Bug Report"模板
3. 提供详细的信息，包括：
   - 错误的详细描述
   - 重现步骤
   - 预期行为和实际行为
   - 环境信息（AstrBot版本、操作系统、Python版本等）
   - 相关的日志输出

### 提出功能请求

如果您有新的功能想法，请：

1. 检查[Issues](https://github.com/piexian/astrbot_plugin_gif_to_video/issues)页面，确认功能尚未被请求
2. 创建一个新的Issue，使用"Feature Request"模板
3. 详细描述您希望添加的功能及其用例

### 提交代码更改

如果您想直接贡献代码，请遵循以下步骤：

#### 1. 准备环境

```bash
# 克隆仓库
git clone https://github.com/piexian/astrbot_plugin_gif_to_video.git
cd astrbot_plugin_gif_to_video

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-asyncio
```

#### 2. 创建分支

```bash
# 创建并切换到新分支
git checkout -b feature/your-feature-name
```

#### 3. 进行更改

- 确保您的代码遵循项目的代码风格
- 添加必要的测试
- 更新相关文档

#### 4. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_conversion.py
```

#### 5. 提交更改

```bash
# 添加更改
git add .

# 提交更改（使用清晰的提交信息）
git commit -m "feat: 添加新功能描述"

# 推送到您的分支
git push origin feature/your-feature-name
```

#### 6. 创建Pull Request

1. 访问GitHub仓库页面
2. 点击"New Pull Request"
3. 选择您的分支
4. 填写PR描述，详细说明您的更改
5. 等待代码审查

## 代码规范

### Python代码风格

- 遵循PEP 8代码风格
- 使用有意义的变量和函数名
- 添加适当的注释和文档字符串
- 保持函数和类的简洁

### 提交信息规范

使用[约定式提交](https://www.conventionalcommits.org/zh-hans/v1.0.0/)格式：

```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

类型包括：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更改
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

示例：
```
fix: 修复GIF检测逻辑中的大小写敏感问题

- 添加了URL大小写不敏感的检测
- 更新了相关测试用例
```

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_conversion.py

# 运行测试并显示覆盖率
pytest --cov=main tests/
```

### 编写测试

- 为新功能编写相应的测试
- 确保测试覆盖边界情况
- 使用描述性的测试名称

### 测试环境

插件测试需要：
- Python 3.8+
- FFmpeg（用于实际转换测试）
- 所有依赖项（见requirements.txt）

## 发布流程

### 版本号

项目遵循[语义化版本](https://semver.org/lang/zh-CN/)：
- `MAJOR.MINOR.PATCH`
- `MAJOR`: 不兼容的API更改
- `MINOR`: 向后兼容的功能新增
- `PATCH`: 向后兼容的错误修复

### 发布步骤

1. 更新版本号（metadata.yaml）
2. 更新CHANGELOG.md
3. 创建Git标签
4. 创建GitHub Release

## 社区准则

### 行为准则

- 尊重所有参与者
- 使用友好和包容的语言
- 接受建设性的反馈
- 专注于对社区最有利的事情

### 沟通渠道

- GitHub Issues: 报告错误和功能请求
- GitHub Discussions: 一般讨论和问题
- Pull Requests: 代码审查和讨论

## 获得帮助

如果您需要帮助：

1. 查看现有的Issues和Discussions
2. 阅读项目的文档
3. 创建一个新的Issue或Discussion

## 许可证

通过贡献代码，您同意您的贡献将在[GNU AGPL v3](LICENSE)许可证下授权。

---

感谢您的贡献！🎉