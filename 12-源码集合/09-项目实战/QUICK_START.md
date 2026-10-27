# 快速开始指南

## 项目结构

```
09-项目实战/
├── 70-智能客服系统/           # 智能客服测试
├── 71-企业知识库问答/         # 企业知识库测试  
├── 72-文档自动摘要/           # 文档摘要测试
├── 73-代码生成助手/           # 代码生成测试
├── 74-数据分析Agent/          # 数据分析测试
├── 75-营销文案生成/           # 营销文案测试
├── 76-智能问答机器人/         # 问答机器人测试
├── 77-多模态应用/             # 多模态测试
├── 78-langgraph实战/          # LangGraph框架测试
├── 79-langchain实战/          # LangChain框架测试
├── 80-crewAI实战/             # CrewAI框架测试
└── 81-autogen实战/            # AutoGen框架测试
```

## 环境要求

- Python 3.8+
- pip 包管理器
- 网络连接（用于下载依赖）

## 快速安装与运行

### 1. 选择任一项目进行测试

```bash
# 例如，运行LangGraph项目
cd 78-langgraph实战
pip install -r requirements.txt
python run_tests.py --demo
```

### 2. 一次性安装所有依赖（可选）

```bash
# 安装所有项目依赖（可能包含重复包）
pip install -r 78-langgraph实战/requirements.txt
pip install -r 79-langchain实战/requirements.txt  
pip install -r 80-crewAI实战/requirements.txt
pip install -r 81-autogen实战/requirements.txt
```

### 3. 各项目运行命令

| 项目 | 命令 | 用途 |
|------|------|------|
| LangGraph | `python run_tests.py --demo` | AI Agent测试框架演示 |
| LangChain | `python run_rag_tests.py --demo` | RAG系统测试演示 |
| CrewAI | `python run_crewai_tests.py --demo` | 多智能体协作测试演示 |
| AutoGen | `python run_autogen_tests.py --demo` | 多智能体对话测试演示 |

## 配置说明

### API密钥配置
大多数项目需要API密钥，创建 `.env` 文件：

```bash
# 在项目根目录创建
cp .env.example .env
# 编辑 .env 文件，添加你的API密钥
```

### 环境变量
常见的环境变量包括：
- `OPENAI_API_KEY` - OpenAI API密钥
- `LANGCHAIN_API_KEY` - LangChain API密钥
- `SERPAPI_API_KEY` - 搜索API密钥

## 实用脚本

### 1. 框架演示脚本
项目根目录提供了便捷的演示脚本：

```bash
# 运行特定框架演示
./run_framework_demos.sh langgraph  # LangGraph演示
./run_framework_demos.sh langchain  # LangChain演示  
./run_framework_demos.sh crewai     # CrewAI演示
./run_framework_demos.sh autogen    # AutoGen演示
./run_framework_demos.sh all        # 运行所有演示
```

### 2. 验证脚本
验证所有文件语法：

```bash
python syntax_validator.py
```

## 学习建议

### 初学者路径
1. 先运行 `71-企业知识库问答` 理解基础概念
2. 再运行 `78-langgraph实战` 学习状态管理
3. 接着运行 `79-langchain实战` 掌握RAG测试
4. 然后运行 `80-crewAI实战` 体验协作测试
5. 最后运行 `81-autogen实战` 探索对话测试

### 进阶应用
- 修改测试场景以适应自己的AI系统
- 扩展现有框架以满足特定需求
- 结合多个框架构建复合测试方案

## 故障排除

### 常见问题
1. **依赖安装失败**: 确保pip和setuptools是最新版本
2. **API密钥错误**: 检查`.env`文件配置
3. **网络连接超时**: 检查网络连接和API服务状态

### 性能建议
- 在有GPU的环境中运行，提高处理速度
- 合理设置并发数，避免API限制
- 使用缓存机制减少重复计算

---

*祝您学习愉快！有问题请参考各项目详细文档。*