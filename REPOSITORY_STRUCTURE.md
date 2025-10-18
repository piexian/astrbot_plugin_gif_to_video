# 仓库结构

本文档描述了AstrBot GIF转视频插件的完整仓库结构。

## 目录结构

```
astrbot_plugin_gif_to_video/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md         # 错误报告模板
│   │   └── feature_request.md    # 功能请求模板
│   └── workflows/
│       └── lint.yml              # CI/CD工作流配置
├── tests/
│   ├── __init__.py               # 测试包初始化
│   ├── test_conversion.py        # 转换功能测试
│   └── test_plugin.py            # 插件功能测试
├── _conf_schema.json             # 插件配置模式
├── CHANGELOG.md                  # 更新日志
├── CONTRIBUTING.md               # 贡献指南
├── LICENSE                       # 许可证文件
├── README.md                     # 插件说明文档
├── main.py                       # 插件主代码
├── metadata.yaml                 # 插件元数据
├── pytest.ini                   # pytest配置
└── requirements.txt             # 依赖列表
```

## 文件说明

### 核心文件

- **main.py**: 插件的主要实现代码，包含GifToVideoPlugin类和转换函数
- **metadata.yaml**: 插件的元数据，包括名称、版本、作者等信息
- **requirements.txt**: 插件依赖的Python包列表
- **_conf_schema.json**: 插件配置的模式定义，用于WebUI配置界面

### 文档文件

- **README.md**: 详细的插件说明文档，包括安装、配置和使用方法
- **CHANGELOG.md**: 版本更新日志，记录每个版本的重要更改
- **CONTRIBUTING.md**: 贡献指南，说明如何为项目做贡献
- **LICENSE**: 许可证文件，本项目使用GNU AGPL v3许可证

### 测试文件

- **tests/**: 测试目录，包含所有测试代码
- **tests/test_conversion.py**: 测试GIF转换功能
- **tests/test_plugin.py**: 测试插件的主要功能
- **pytest.ini**: pytest配置文件，定义测试运行参数

### GitHub配置

- **.github/**: GitHub相关配置目录
- **.github/ISSUE_TEMPLATE/**: Issue模板，用于标准化错误报告和功能请求
- **.github/workflows/**: CI/CD工作流配置

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/piexian/astrbot_plugin_gif_to_video.git
cd astrbot_plugin_gif_to_video
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行测试

```bash
pytest
```

### 4. 安装到AstrBot

将整个插件目录复制到AstrBot的`data/plugins/`目录下，然后重启AstrBot。

## 发布流程

### 1. 更新版本号

在`metadata.yaml`中更新版本号。

### 2. 更新CHANGELOG.md

添加新版本的更改记录。

### 3. 创建Git标签

```bash
git tag -a v2.0.1 -m "Release version 2.0.1"
git push origin v2.0.1
```

### 4. 创建GitHub Release

在GitHub上创建新的Release，附上CHANGELOG中的更改说明。

## 代码规范

- 遵循PEP 8代码风格
- 使用类型提示
- 添加适当的文档字符串
- 保持函数和类的简洁

## 测试规范

- 为新功能编写相应的测试
- 确保测试覆盖边界情况
- 使用描述性的测试名称
- 保持测试的独立性

## 文档规范

- 使用Markdown格式
- 保持文档的及时更新
- 提供清晰的示例和说明
- 包含必要的故障排除信息

---

这个结构确保了插件的完整性、可维护性和可扩展性。所有必要的文件都已包含，使插件可以顺利地开发、测试、部署和维护。