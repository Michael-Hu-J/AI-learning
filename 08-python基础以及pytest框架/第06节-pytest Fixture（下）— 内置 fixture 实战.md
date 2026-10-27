# 06-pytest Fixture（下）— 内置 fixture 实战

> 对应代码：pytest 内置 fixture，补充测试场景示例
>
> 说明：pytest 内置了多个实用 fixture，不需要写一行代码就能用。本节结合真实测试场景演示它们的用法。

---

## 概念讲解

pytest 除了让你自定义 fixture，还内置了一组开箱即用的 fixture。

**这些内置 fixture 解决的是测试中的通用需求**：临时文件、日志捕获、环境变量模拟、输出捕获。你不需要自己实现，pytest 已经帮你写好了。

**很多测试工程师用 pytest 很久都不知道这些内置 fixture 的存在**，然后自己写了一堆重复的工具函数。本节把这四个最常用的内置 fixture讲清楚。

---

## 内置fixture实战用法

### 1. tmp_path — 临时目录，用完自动清理

`tmp_path` 返回一个 `pathlib.Path` 对象，指向一个唯一的临时目录。测试结束后自动删除。

**适用场景**：文件上传测试、配置文件生成测试、报告文件验证。

```python
def test_file_upload(tmp_path):
    """
    测试文件上传功能
    
    tmp_path 是一个唯一的临时目录，测试结束后自动删除
    """
    # 在临时目录中创建测试文件
    test_file = tmp_path / "test_document.pdf"
    test_file.write_text("这是测试文件内容")
    
    # 验证文件存在
    assert test_file.exists()
    assert test_file.read_text() == "这是测试文件内容"
    
    # 实际项目中：调用上传接口并验证返回结果
    # upload_file(str(test_file))
    # assert is_uploaded("test_document.pdf")
```

**tmp_path 的实用技巧**：

```python
def test_multiple_files(tmp_path):
    """在临时目录中创建多个文件和子目录"""
    # 创建子目录
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    
    # 创建多个文件
    (tmp_path / "file1.txt").write_text("内容1")
    (tmp_path / "file2.txt").write_text("内容2")
    (sub_dir / "file3.txt").write_text("内容3")
    
    # 列出所有文件
    all_files = list(tmp_path.rglob("*"))
    assert len(all_files) == 3
```

**真实测试场景**：测试报告生成器是否正确生成了 HTML 报告文件。

```python
def test_report_generation(tmp_path):
    """验证报告生成器能正确输出文件"""
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    
    # 实际项目中：调用报告生成器并验证输出文件
    # generate_html_report(output_dir=output_dir)
    
    # 验证报告文件存在和内容
    report_file = output_dir / "report.html"
    assert report_file.exists(), "报告文件应该被生成"
    
    # 验证报告内容
    content = report_file.read_text()
    assert "<html>" in content
    assert "测试报告" in content
```

### 2. caplog — 捕获日志输出

`caplog` 捕获测试过程中的日志输出，让你可以验证日志是否正确。

**适用场景**：验证日志级别、验证日志内容、验证错误是否被正确记录。

```python
def test_api_request_logging(caplog):
    """
    验证API请求是否正确记录了日志
    
    caplog 会捕获测试过程中的所有日志输出
    """
    # 设置日志级别（不设置的话可能捕获不到 DEBUG 日志）
    caplog.set_level("INFO")
    
    # 实际项目中：执行会记录日志的操作（如发送 API 请求）
    # api_client = BaseAPI(base_url="https://api.example.com")
    # response = api_client.get("/api/config/phone-area-list")
    
    # 验证日志内容
    # assert "发送GET请求" in caplog.text
    # assert "响应状态码: 200" in caplog.text
    
    # 或者逐条检查日志
    assert any("发送GET请求" in record.message for record in caplog.records)
    assert any("响应状态码" in record.message for record in caplog.records)
```

**caplog 的实用技巧**：

```python
def test_error_logging(caplog):
    """验证错误是否被正确记录"""
    caplog.set_level("ERROR")
    
    # 实际项目中：执行会触发错误日志的操作（如请求不存在的接口）
    # try:
    #     api_client.get("/api/nonexistent")
    # except:
    #     pass
    
    # 验证错误日志被正确记录
    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) > 0, "应该有错误日志"
    assert "连接错误" in caplog.text or "请求异常" in caplog.text
```

**为什么要验证日志**：日志是线上排查问题的第一手段。如果日志没按预期输出，线上出了问题你就找不到根因。用 `caplog` 验证日志，等于给日志本身写了测试。

### 3. monkeypatch — 模拟环境变量和属性

`monkeypatch` 允许你在测试中临时修改环境变量、对象属性、字典值。测试结束后自动恢复。

**适用场景**：测试不同配置下的行为、模拟环境变量、mock 第三方库的返回值。

```python
def test_config_from_env(monkeypatch):
    """
    验证配置从环境变量读取
    
    monkeypatch 可以临时设置环境变量，测试结束后自动恢复
    """
    # 设置环境变量
    monkeypatch.setenv("API_BASE_URL", "https://staging.example.com")
    monkeypatch.setenv("API_TIMEOUT", "60")
    
    # 读取配置（从环境变量）
    base_url = os.getenv("API_BASE_URL")
    timeout = int(os.getenv("API_TIMEOUT", "30"))
    
    # 验证读取到了正确的值
    assert base_url == "https://staging.example.com"
    assert timeout == 60
    
    # 测试结束后，环境变量自动恢复为原始值
```

**monkeypatch 的实用技巧**：

```python
def test_platform_detection(monkeypatch):
    """验证不同平台配置下的行为"""
    # 模拟 Android 平台
    monkeypatch.setenv("PLATFORM", "android")
    # 实际项目中：验证平台检测函数返回值
    # assert detect_platform() == "android"
    
    # 模拟 iOS 平台
    monkeypatch.setenv("PLATFORM", "ios")
    # assert detect_platform() == "ios"


def test_mock_third_party(monkeypatch):
    """mock 第三方库的返回值"""
    # mock requests.get 的返回值
    def mock_get(url, **kwargs):
        class FakeResponse:
            status_code = 200
            def json(self):
                return {"code": "SUCCESS", "data": {"mocked": True}}
        return FakeResponse()
    
    monkeypatch.setattr("requests.get", mock_get)
    
    # 实际项目中：调用被测函数并验证使用了 mock 的返回值
    # response = requests.get("https://any-url.com")
    # assert response.json()["data"]["mocked"] == True
```

**monkeypatch vs mock 库**：`monkeypatch` 适合简单的属性/环境变量修改。复杂的 mock 场景（如验证调用次数、参数匹配）建议用 `unittest.mock`。

### 4. capsys — 捕获 print 输出

`capsys` 捕获测试过程中的 `print()` 输出和 `sys.stdout/sys.stderr`。

**适用场景**：验证命令行工具的输出、验证打印的日志格式。

```python
def test_cli_output(capsys):
    """
    验证命令行工具的打印输出
    
    capsys 会捕获测试过程中的 print() 输出
    """
    # 实际项目中：执行会打印输出的操作（如运行 CLI 命令）
    # print_test_summary()  # 假设这个函数打印测试结果概览
    
    # 捕获输出
    captured = capsys.readouterr()
    
    # 验证输出内容
    # assert "测试通过" in captured.out
    # assert "失败" not in captured.out
```

**capsys 的正确用法**：

```python
def test_print_output(capsys):
    """验证 print 输出"""
    print("Hello, World!")
    print("Test Summary: 10 passed, 0 failed")
    
    captured = capsys.readouterr()
    
    assert "Hello, World!" in captured.out
    assert "10 passed" in captured.out
    assert "0 failed" in captured.out
```

---

## 实战案例

以"测试环境配置切换"为场景，综合运用多个内置 fixture。

**场景描述**：测试系统需要支持多个环境（开发、测试、生产），通过环境变量切换。需要验证：
1. 环境变量正确读取
2. 日志正确输出
3. 配置文件正确生成

```python
import os
import pytest


class TestEnvironmentConfig:
    """环境配置测试"""
    
    def test_dev_environment(self, monkeypatch, caplog, tmp_path):
        """验证开发环境配置"""
        caplog.set_level("INFO")
        
        # 设置开发环境的环境变量
        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("API_BASE_URL", "https://dev-api.example.com")
        monkeypatch.setenv("API_TIMEOUT", "10")
        
        # 读取配置
        env = os.getenv("ENV")
        base_url = os.getenv("API_BASE_URL")
        timeout = int(os.getenv("API_TIMEOUT", "30"))
        
        # 验证配置值
        assert env == "dev"
        assert base_url == "https://dev-api.example.com"
        assert timeout == 10
        
        # 实际项目中：验证配置加载日志是否正确输出
        # assert "加载开发环境配置" in caplog.text
        
        # 在临时目录生成配置文件
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"env: {env}\nbase_url: {base_url}\ntimeout: {timeout}")
        
        # 验证配置文件内容
        content = config_file.read_text()
        assert "env: dev" in content
        assert "base_url: https://dev-api.example.com" in content
    
    def test_staging_environment(self, monkeypatch, caplog, tmp_path):
        """验证测试环境配置"""
        caplog.set_level("INFO")
        
        monkeypatch.setenv("ENV", "staging")
        monkeypatch.setenv("API_BASE_URL", "https://staging-api.example.com")
        monkeypatch.setenv("API_TIMEOUT", "30")
        
        env = os.getenv("ENV")
        base_url = os.getenv("API_BASE_URL")
        timeout = int(os.getenv("API_TIMEOUT", "30"))
        
        assert env == "staging"
        assert base_url == "https://staging-api.example.com"
        assert timeout == 30
        
        # 生成配置文件
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"env: {env}\nbase_url: {base_url}\ntimeout: {timeout}")
        
        content = config_file.read_text()
        assert "env: staging" in content
```

**这个案例展示了什么**：
- `monkeypatch` 模拟不同环境的环境变量
- `caplog` 验证日志输出
- `tmp_path` 生成和验证配置文件
- 三个内置 fixture 组合使用，覆盖了配置测试的完整流程

---

## 注意事项和常见坑

- **`caplog.set_level()` 必须在日志产生之前调用**。如果你在设置级别之前就执行了被测代码，日志已经产生了，`caplog` 捕获不到。
- **`monkeypatch.setenv()` 只影响当前测试**。测试结束后自动恢复原始值，不会影响其他测试。这是它比直接 `os.environ[key] = value` 更好的地方。
- **`tmp_path` 是 `pathlib.Path` 对象，不是字符串**。需要用 `str(tmp_path)` 转换后才能传给不接受 Path 的库。
- **`capsys.readouterr()` 返回的是 namedtuple**，有 `out` 和 `err` 两个属性。不要直接 `assert "xxx" in capsys`，要 `assert "xxx" in captured.out`。
- **内置 fixture 不需要导入**。pytest 自动注册了它们，直接在测试函数参数中声明即可。

---

## 总结与思考

> pytest 内置的这四个 fixture（tmp_path、caplog、monkeypatch、capsys）覆盖了测试中80%的通用需求。先看看 pytest 有没有内置的，再决定要不要自己写——省下的时间够你多喝一杯咖啡。

**思考题**：你有没有自己写过"临时文件清理"或"环境变量模拟"的工具函数？看完这节后，有没有发现可以用内置 fixture 替换的地方？


---

## 面试题模块

### 1. tmp_path

**Q1：`tmp_path` 和 `tmpdir` 的区别是什么？应该用哪个？**

A：`tmp_path` 返回 `pathlib.Path` 对象（现代 Python 推荐），`tmpdir` 返回 py.path.local 对象（旧版兼容）。pytest 官方推荐用 `tmp_path`，因为 `pathlib` 是 Python 3 的标准路径操作方式。两者功能相同——都是唯一的临时目录，测试结束后自动删除。

### 2. capsys

**Q2：怎么测试一个函数是否正确输出了 print 内容？**

A：用 `capsys` fixture：
```python
def test_print_output(capsys):
    print("Hello, World!")
    captured = capsys.readouterr()
    assert "Hello, World!" in captured.out
```
`capsys.readouterr()` 返回 `CaptureResult(out=..., err=...)`，可以分别检查 stdout 和 stderr。

### 3. monkeypatch

**Q3：`monkeypatch` 能做什么？举一个测试环境变量的例子。**

A：`monkeypatch` 可以在测试期间临时修改环境变量、模块属性、字典值等。测试结束后自动恢复。
```python
def test_with_env_var(monkeypatch):
    monkeypatch.setenv("API_URL", "http://test.example.com")
    import os
    assert os.getenv("API_URL") == "http://test.example.com"
# 测试结束后，环境变量自动恢复
```

---

