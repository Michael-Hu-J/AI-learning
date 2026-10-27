# 第07节-API测试封装 — BaseAPI 的设计与实现

> 配套代码：[`api/base_api.py`](配套代码/test/api/base_api.py)（223行）
>
> 说明：本节所有代码示例来自真实移动端自动化测试项目，业务名和 API 路径已模糊化。

---

## 为什么移动端测试需要 API 封装

先交代背景。这个项目刚启动的时候，团队直接在 UI 测试里裸调 `requests.post()`，每个用例都自己造 headers、自己处理超时、自己 try-catch。跑了一周就炸了——登录 Token 过期没人管、测试环境切换要改几十个文件、某个接口超时了日志里只看得到一行 `ConnectionError` 连 URL 都没有。

移动端测试比纯后端测试多一层复杂度：你测的是 App，但 App 的行为 = UI 操作 + 网络请求。如果只测 UI，一个注册流程跑完要 20 秒，30 个用例就是 10 分钟，而且定位问题还得靠抓包。**更靠谱的策略是：核心业务逻辑走 API 测（注册、登录、修改手机号），页面展示用 UI 测（元素是否存在、布局是否正确）。**

这个 `BaseAPI` 就是这么来的——给整个项目提供一个统一的 HTTP 请求入口。所有接口测试要么继承它，要么直接实例化它。

## 核心设计：一个 Session 管所有请求

看 `api/base_api.py`，核心就一个思路：**用 `requests.Session()` 代替裸调**。

```python
def __init__(self, base_url: str = None, timeout: int = 30, verify_ssl: bool = True):
    self.base_url = base_url or ""
    self.timeout = timeout
    self.verify_ssl = verify_ssl
    self.session = requests.Session()
    self.headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
```

为什么用 Session？踩过坑的人都知道。如果每个请求方法里都 `requests.post()`，每次都会新建 TCP 连接——三次握手、TLS 握手全来一遍。Session 保持 HTTP Keep-Alive，同一个域名下的请求复用连接，实测在连续调 50 个接口的场景下，能省掉 60% 以上的建连时间。

另一个细节：`verify_ssl` 默认是 `True`。这个踩过一次坑——测试环境用自签名证书，一开始设了 `verify_ssl=False`，结果上线前忘了改回来，生产环境跑了半天 SSL 告警某安全组才抓出来。后来改成默认 `True`，测试环境通过 conftest 里显式覆盖。

## 统一请求入口：_request

`_request` 方法（下划线前缀，内部方法）是整个类的核心，所有公开方法都走它。

```python
def _request(
    self,
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict] = None,
    **kwargs
) -> requests.Response:
    url = self._build_url(endpoint)
    request_headers = self.headers.copy()
    if headers:
        request_headers.update(headers)
    
    logger.info(f"发送{method}请求: {url}")
    if params:
        logger.debug(f"请求参数: {params}")
    if json_data:
        logger.debug(f"请求体(JSON): {json_data}")
    if data:
        logger.debug(f"请求体(Form): {data}")
    
    try:
        response = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_data,
            data=data,
            headers=request_headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
            **kwargs
        )
        logger.info(f"响应状态码: {response.status_code}")
        logger.debug(f"响应头: {dict(response.headers)}")
        try:
            logger.debug(f"响应体: {response.json()}")
        except:
            logger.debug(f"响应体: {response.text[:500]}")
        return response
    except requests.exceptions.Timeout:
        logger.error(f"请求超时: {url}")
        raise
    except requests.exceptions.ConnectionError:
        logger.error(f"连接错误: {url}")
        raise
    except Exception as e:
        logger.error(f"请求异常: {str(e)}")
        raise
```

说几个设计上的考虑：

**日志分级。** info 层记录请求 URL 和状态码，debug 层才记录请求体和响应体。这么做的原因是——线上跑 CI 的时候，200 个测试用例全是 info 就够了，debug 会把日志撑爆。但 debug 又必须有，因为一旦某个接口返回 500，你需要知道当时传了什么参数。这个教训是从一次生产事故里来的：某个接口返回了 400，但 info 日志只看到 URL，查了半天才发现是某个字段传了空字符串。

**异常分类。** Timeout 和 ConnectionError 分开处理。看起来啰嗦，但实际排查问题的时候区别很大——超时通常是接口响应慢了或者网络抖动，连接错误八成是环境挂了或者配置错了。日志里搜 `请求超时` 和 `连接错误`，问题方向一目了然。

**响应体兜底。** `response.json()` 有可能抛异常（比如返回的不是 JSON），所以包了个 try-except，失败了就截取前 500 字符的 text。这个处理也是踩坑踩出来的——有一次某个接口返回了 502 页面（HTML 内容），`response.json()` 直接挂了，导致测试用例异常退出，连状态码都没打出来。

**`_build_url` 的小细节。** 注意它对 `base_url` 做了 `rstrip("/")`，对 `endpoint` 做了 `lstrip("/")`——这样不管配置里写 `https://api.example.com/v1` 还是 `https://api.example.com/v1/`，endpoint 传 `/user/login` 还是 `user/login`，都能拼出正确的完整 URL。虽然只是字符串操作，但这个细节在团队协作里帮了大忙，因为不同人的习惯写法不一样。

## 公开方法：薄薄的封装层

```python
def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
    return self._request("GET", endpoint, params=params, **kwargs)

def post(self, endpoint: str, json_data: Optional[Dict] = None,
         data: Optional[Any] = None, **kwargs) -> requests.Response:
    return self._request("POST", endpoint, json_data=json_data, data=data, **kwargs)

def put(self, endpoint: str, json_data: Optional[Dict] = None,
        data: Optional[Any] = None, **kwargs) -> requests.Response:
    return self._request("PUT", endpoint, json_data=json_data, data=data, **kwargs)

def delete(self, endpoint: str, **kwargs) -> requests.Response:
    return self._request("DELETE", endpoint, **kwargs)

def patch(self, endpoint: str, json_data: Optional[Dict] = None,
          data: Optional[Any] = None, **kwargs) -> requests.Response:
    return self._request("PATCH", endpoint, json_data=json_data, data=data, **kwargs)
```

为什么要单独 `get`、`post`、`put` 而不是直接暴露一个 `request(method, endpoint, ...)`？两个原因：

1. **IDE 自动补全友好。** 别人用这个类的时候，输入 `api_client.` 就能看到所有可用的 HTTP 方法，不需要去记方法名。
2. **参数签名差异化。** GET 不需要 `json_data`，POST 需要区分 `json_data` 和 `data`，单独封装可以在参数列表里明确区分。

GET 请求传参数用 `params`（URL 查询参数），POST/PUT 请求体用 `json_data`（自动设置 `Content-Type: application/json` 并序列化）或 `data`（表单编码）。这个区分是 requests 库的设计，BaseAPI 没有做什么额外包装，保持原样——少一层抽象就少一层坑。

## set_auth 和 set_headers

```python
def set_headers(self, headers: Dict[str, str]):
    self.headers.update(headers)

def set_auth(self, auth_type: str = "bearer", token: str = None):
    if auth_type.lower() == "bearer" and token:
        self.headers["Authorization"] = f"Bearer {token}"
    elif auth_type.lower() == "basic" and token:
        self.headers["Authorization"] = f"Basic {token}"
```

为什么 `set_auth` 只处理 header 级别的 token？不处理更复杂的 OAuth2 流程？因为项目里大多数接口都是 Bearer Token 认证，token 从登录接口拿。这层不处理刷新逻辑——token 过期了，调用方负责重新拿。这是刻意做薄的决策：BaseAPI 只做请求发送的基础设施，业务逻辑（包括 token 管理）由上层处理。

## 在测试框架里怎么用

实际项目里一般在 conftest.py 里把这个配成 fixture：

```python
@pytest.fixture(scope="session")
def api_client():
    base_url = os.getenv("API_BASE_URL", "")
    timeout = int(os.getenv("API_TIMEOUT", "30"))
    
    client = BaseAPI(base_url=base_url, timeout=timeout)
    
    api_token = os.getenv("API_TOKEN", "")
    if api_token:
        client.set_auth("bearer", api_token)
    
    yield client

`scope="session"` 意味着整个测试会话只创建一个客户端实例，Session 复用。注意 fixture 返回的是 `client` 实例，而不是 session 级别的函数调用——因为中间可能需要更新 headers（比如 token 刷新后调 `set_auth`）。

一个常见的坑：fixture 里设了 `verify_ssl=False`，但上线前忘了改。建议在 conftest 里加一个环境检查：

```python
if os.getenv("ENV") == "production" and not os.getenv("ALLOW_INSECURE"):
    client.verify_ssl = True

## 踩坑总结

按踩坑频率排个序：

1. **Token 过期无感知。** 测试跑着跑着，某几个接口返回 401，但用例断言的是 200，全部标红。排查半天才发现是 fixture 里 set 的 token 过期了。解决方案：在 fixture 里加 token 过期时间的日志打印，并在 CI 里定期更新 token。

2. **超时时间一刀切。** 默认 30 秒，大部分接口没问题。但文件上传接口和导出接口（生成 PDF/Excel 的那类）慢得多，需要在用例级别单独指定 timeout。所以 `_request` 的 `**kwargs` 支持透传 `timeout` 参数覆盖默认值。

3. **SSL 证书切换。** 测试环境用 `verify_ssl=False` 图省事，结果自签名证书更新了也没人管。上线前打开 `verify_ssl=True`，一堆接口炸了——因为测试环境的证书配置跟生产不一样。后来每次上线前都要跑一遍 SSL 验证的冒烟测试。

4. **JSON 响应不是 JSON。** 服务端返回 500 的时候，响应体是 HTML 错误页面。`response.json()` 抛 ValueError，用例崩溃。后来在 `_request` 里加了兜底处理（上面提到的那段 try-except），至少能输出状态码和部分响应体。

5. **日志量太大。** 一开始所有请求体和响应体都用 `info` 级别打日志，跑 100 个用例就几十 MB 日志。改成分级后好了很多。

## BaseAPI 到底有多大价值

223 行代码，功能就这么点：封装 HTTP 方法、统一异常处理、分级日志。但它解决的是"**30 个接口测试用例、6 个团队成员的协作问题**"——没有人需要关心怎么拼 URL、怎么设 headers、怎么 catch 异常。出了问题，日志里搜 `发送POST请求` 或者 `响应状态码`，定位路径是统一的。

这层封装的核心理念：**不要重复造轮子，但要把轮子磨平整，让所有人都能轻松推到同一个方向上。**
