# 第17节-XMind用例转换 — 从思维导图到 YAML

> 对应代码：`配套代码/test/utils/xmind_parser.py`
>
> 说明：本节讲解如何解析 XMind 思维导图文件，将其转换为 YAML 格式的测试用例，供自动化脚本执行。

---

## 这节讲什么

测试用例通常有两种存在形式：
1. **思维导图**（XMind）：适合头脑风暴、梳理逻辑、团队评审
2. **YAML/JSON**：适合机器解析、自动化执行

问题：两种格式之间需要人工转换。测试工程师在 XMind 里写好用例，再手动翻译成 YAML，费时费力还容易出错。

**XMind 解析器**就是为了解决这个问题：自动把 XMind 文件转成 YAML，保持原有的层级结构，直接供自动化脚本使用。

---

## 核心思路

XMind 文件的结构是树形的：

```
测试套件（根节点）
  ├── 测试模块 1
  │   ├── 测试用例 1-1
  │   │   ├── 步骤 1
  │   │   └── 步骤 2
  │   └── 测试用例 1-2
  └── 测试模块 2
      └── 测试用例 2-1
```

转换后的 YAML 结构：

```yaml
name: 测试套件
test_modules:
  - name: 测试模块 1
    test_cases:
      - name: 测试用例 1-1
        steps:
          - action: "步骤 1"
          - action: "步骤 2"
      - name: 测试用例 1-2

### 层级识别

XMind 的层级通过**缩进**或**主题级别**来识别：
- 根主题 → 测试套件
- 一级子主题 → 测试模块
- 二级子主题 → 测试用例
- 三级子主题 → 测试步骤

**配套代码支持 3-6 层结构**，能处理大多数测试用例的层级需求。

---

## 实战案例

### 案例：登录功能 XMind 转 YAML

**原始 XMind 结构**：
```
登录功能测试
  ├── 正常场景
  │   ├── 有效用户登录成功
  │   │   ├── 输入用户名 admin
  │   │   ├── 输入密码 admin123
  │   │   └── 点击登录按钮
  │   └── 记住密码功能
  └── 异常场景
      ├── 密码错误
      └── 用户不存在
```

**转换后的 YAML**：
```yaml
name: 登录功能测试
test_modules:
  - name: 正常场景
    test_cases:
      - name: 有效用户登录成功
        steps:
          - action: "输入用户名 admin"
          - action: "输入密码 admin123"
          - action: "点击登录按钮"
      - name: 记住密码功能
        steps: []
  - name: 异常场景
    test_cases:
      - name: 密码错误
        steps: []
      - name: 用户不存在
        steps: []
```

---

## 代码实现

核心代码在 `utils/xmind_parser.py`：

```python
class XMindParser:
    def __init__(self):
        if not XMIND_AVAILABLE:
            raise ImportError("xmindparser 未安装")
    
    def parse(self, xmind_file: str) -> dict:
        """解析 XMind 文件"""
        # 1. 使用 xmindparser 解析文件
        content = xmindparser.xmind_to_dict(xmind_file)
        
        # 2. 转换格式
        test_suite = self._convert_to_test_suite(content[0])
        
        return test_suite
    
    def _convert_to_test_suite(self, root_topic: dict) -> dict:
        """将 XMind 主题转换为测试套件"""
        suite = {
            "name": root_topic.get("title", "测试套件"),
            "description": root_topic.get("note", ""),
            "test_modules": []
        }
        
        # 递归转换子主题
        for topic in root_topic.get("topics", []):
            module = self._convert_to_module(topic)
            suite["test_modules"].append(module)
        
        return suite

---

## 注意事项

### 1. XMind 版本兼容

xmindparser 支持 XMind 8 和 XMind Zen 格式，但不同版本的内部结构有差异。

**建议**：
- 团队统一使用同一版本 XMind
- 转换前先用小文件测试，确认格式正确
- 如果解析失败，检查 XMind 文件是否损坏

### 2. 层级深度的限制

配套代码支持 3-6 层结构。如果 XMind 超过 6 层，超出部分会被忽略。

**建议**：
- 测试用例层级控制在 4 层以内（套件→模块→用例→步骤）
- 超过 4 层说明用例设计太复杂，考虑拆分

### 3. 步骤内容的解析

XMind 中的步骤是纯文本，需要进一步解析才能供自动化脚本执行。

**建议**：
- 步骤格式统一为"动词 + 对象"（如"点击登录按钮"）
- 使用 `test_point_parser.py` 进一步解析步骤，提取动作和目标元素
- 复杂步骤（如"输入用户名"）需要额外参数（用户名值）

### 4. 数据丢失的风险

XMind 转 YAML 是**单向转换**，部分 XMind 特有信息会丢失：
- 备注（notes）可能丢失
- 标签（tags）可能丢失
- 超链接可能丢失

**建议**：
- 转换后人工 review 一遍 YAML，确认关键信息完整
- 重要用例保留 XMind 源文件作为备份

---

## XMind 转换的注意事项

XMind 转 YAML 听起来简单，实际用起来有几个容易踩坑的地方：

**XMind 文件结构不规范**

- 有些人习惯把步骤写在备注里而不是子主题里——解析器读不到
- 有些人用多级嵌套（超过 6 层）——超出部分会被忽略
- **建议**：转换前检查 XMind 结构，保证层级在 4 层以内（套件→模块→用例→步骤）

**步骤内容格式不统一**

- 同一个步骤，有人写"点击登录"，有人写"单击登录按钮"，有人写"Login Button Click"
- 解析后的 YAML 步骤是纯文本，后续自动化脚本需要统一格式才能执行
- **建议**：团队约定步骤格式为"动词 + 对象"（如"点击登录按钮"），用 `test_point_parser.py` 进一步解析

**信息丢失**

- XMind 的备注、标签、超链接、优先级标记——这些在转 YAML 时可能丢失
- 如果团队依赖 XMind 的备注功能记录测试要点，转换后需要人工补全
- **建议**：转换后人工 review 一遍 YAML，确认关键信息完整；重要用例保留 XMind 源文件

**版本兼容性**

- XMind 8 和 XMind Zen 的内部格式不同，同一个解析器可能只支持其中一个
- **建议**：团队统一 XMind 版本，转换前用小文件验证兼容性
