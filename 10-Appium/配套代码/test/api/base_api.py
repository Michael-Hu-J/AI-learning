# base_api.py - API测试基类
"""
API测试基类
功能：封装接口请求的通用操作，所有API测试类都应继承此类
"""
import requests
from typing import Dict, Any, Optional
from utils.logger import Logger

logger = Logger().get_logger()


class BaseAPI:
    """
    API测试基类
    
    作用：
    1. 封装HTTP请求方法（GET、POST、PUT、DELETE等）
    2. 统一处理请求头、认证、超时等
    3. 统一处理响应和异常
    """
    
    def __init__(self, base_url: str = None, timeout: int = 30, verify_ssl: bool = True):
        """
        初始化API客户端
        
        参数：
        - base_url: API基础URL
        - timeout: 请求超时时间（秒）
        - verify_ssl: 是否验证SSL证书（默认True，测试环境可设置为False）
        """
        self.base_url = base_url or ""
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.debug(f"初始化API客户端，base_url: {self.base_url}, verify_ssl: {self.verify_ssl}")
    
    def set_headers(self, headers: Dict[str, str]):
        """
        设置请求头
        
        参数：
        - headers: 请求头字典
        """
        self.headers.update(headers)
        logger.debug(f"更新请求头: {headers}")
    
    def set_auth(self, auth_type: str = "bearer", token: str = None):
        """
        设置认证信息
        
        参数：
        - auth_type: 认证类型（bearer, basic等）
        - token: 认证令牌
        """
        if auth_type.lower() == "bearer" and token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif auth_type.lower() == "basic" and token:
            self.headers["Authorization"] = f"Basic {token}"
        logger.debug(f"设置认证: {auth_type}")
    
    def _build_url(self, endpoint: str) -> str:
        """
        构建完整URL
        
        参数：
        - endpoint: API端点
        
        返回：
        - 完整URL
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        base = self.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"
    
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
        """
        发送HTTP请求（内部方法）
        
        参数：
        - method: HTTP方法（GET, POST, PUT, DELETE等）
        - endpoint: API端点
        - params: URL参数
        - json_data: JSON数据
        - data: 表单数据
        - headers: 请求头（会合并到默认请求头）
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
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
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        发送GET请求
        
        参数：
        - endpoint: API端点
        - params: URL参数
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
        return self._request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, json_data: Optional[Dict] = None, data: Optional[Any] = None, **kwargs) -> requests.Response:
        """
        发送POST请求
        
        参数：
        - endpoint: API端点
        - json_data: JSON数据
        - data: 表单数据
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
        return self._request("POST", endpoint, json_data=json_data, data=data, **kwargs)
    
    def put(self, endpoint: str, json_data: Optional[Dict] = None, data: Optional[Any] = None, **kwargs) -> requests.Response:
        """
        发送PUT请求
        
        参数：
        - endpoint: API端点
        - json_data: JSON数据
        - data: 表单数据
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
        return self._request("PUT", endpoint, json_data=json_data, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送DELETE请求
        
        参数：
        - endpoint: API端点
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
        return self._request("DELETE", endpoint, **kwargs)
    
    def patch(self, endpoint: str, json_data: Optional[Dict] = None, data: Optional[Any] = None, **kwargs) -> requests.Response:
        """
        发送PATCH请求
        
        参数：
        - endpoint: API端点
        - json_data: JSON数据
        - data: 表单数据
        - **kwargs: 其他requests参数
        
        返回：
        - Response对象
        """
        return self._request("PATCH", endpoint, json_data=json_data, data=data, **kwargs)

