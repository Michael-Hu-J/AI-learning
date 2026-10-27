#!/usr/bin/env python3
"""
OpenAPI 文档解析器 v2
从 OpenAPI 3.0 YAML/JSON 文档中提取接口信息，包含字段约束、枚举、类型等完整 Schema 信息。
"""

import yaml
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FieldConstraint:
    """字段约束信息"""
    name: str
    field_type: str  # string/integer/number/boolean/array/object
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    enum: Optional[List] = None
    pattern: Optional[str] = None
    format: Optional[str] = None  # email/date-time/uuid
    description: str = ""
    example: Any = None


@dataclass
class APIEndpoint:
    """单个 API 接口"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]
    operation_id: str
    parameters: List[Dict]
    request_body: Optional[Dict]
    request_fields: List[FieldConstraint] = field(default_factory=list)
    responses: Dict[str, Dict] = field(default_factory=dict)
    requires_auth: bool = False
    response_fields: List[FieldConstraint] = field(default_factory=list)


@dataclass
class APISchema:
    """Schema 定义"""
    name: str
    properties: Dict[str, Dict]
    required: List[str]
    fields: List[FieldConstraint] = field(default_factory=list)


class OpenAPIParser:
    """OpenAPI 文档解析器 v2"""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec = self._load_spec()
        self.endpoints: List[APIEndpoint] = []
        self.schemas: Dict[str, APISchema] = {}
        self._parse()

    def _load_spec(self) -> Dict:
        with open(self.spec_path, 'r', encoding='utf-8') as f:
            if self.spec_path.endswith('.json'):
                return json.load(f)
            return yaml.safe_load(f)

    def _resolve_ref(self, ref: str) -> Dict:
        if not ref.startswith('#/'):
            return {}
        parts = ref[2:].split('/')
        result = self.spec
        for part in parts:
            result = result.get(part, {})
        return result

    def _extract_fields(self, schema: Dict, required_list: List[str] = None) -> List[FieldConstraint]:
        """从 Schema 提取字段约束"""
        if required_list is None:
            required_list = schema.get('required', [])
        fields = []
        properties = schema.get('properties', {})
        for name, prop in properties.items():
            fc = FieldConstraint(
                name=name,
                field_type=prop.get('type', 'string'),
                required=name in required_list,
                min_length=prop.get('minLength'),
                max_length=prop.get('maxLength'),
                minimum=prop.get('minimum'),
                maximum=prop.get('maximum'),
                enum=prop.get('enum'),
                pattern=prop.get('pattern'),
                format=prop.get('format'),
                description=prop.get('description', ''),
                example=prop.get('example'),
            )
            # 递归处理嵌套对象
            if prop.get('type') == 'object' and 'properties' in prop:
                fc.field_type = 'object'
            fields.append(fc)
        return fields

    def _check_auth(self, operation: Dict) -> bool:
        security = operation.get('security', [])
        if security:
            for sec in security:
                if isinstance(sec, dict) and ('BearerAuth' in sec or 'bearerAuth' in sec):
                    return True
        global_security = self.spec.get('security', [])
        if global_security:
            return True
        return False

    def _parse(self):
        # 解析 Schema
        components = self.spec.get('components', {})
        schemas = components.get('schemas', {})
        for name, schema_def in schemas.items():
            required = schema_def.get('required', [])
            fields = self._extract_fields(schema_def, required)
            self.schemas[name] = APISchema(
                name=name,
                properties=schema_def.get('properties', {}),
                required=required,
                fields=fields,
            )

        # 解析接口
        paths = self.spec.get('paths', {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method not in ('get', 'post', 'put', 'delete', 'patch'):
                    continue

                # 解析请求体
                request_body = None
                request_fields = []
                if 'requestBody' in operation:
                    content = operation['requestBody'].get('content', {})
                    json_content = content.get('application/json', {})
                    schema = json_content.get('schema', {})
                    if '$ref' in schema:
                        schema = self._resolve_ref(schema['$ref'])
                    required = schema.get('required', [])
                    request_fields = self._extract_fields(schema, required)
                    request_body = {
                        'required': operation['requestBody'].get('required', False),
                        'schema': schema,
                        'example': json_content.get('example', {}),
                    }

                # 解析参数
                parameters = []
                for param in operation.get('parameters', []):
                    param_schema = param.get('schema', {})
                    parameters.append({
                        'name': param.get('name'),
                        'in': param.get('in'),
                        'required': param.get('required', False),
                        'type': param_schema.get('type', 'string'),
                        'enum': param_schema.get('enum'),
                        'description': param.get('description', ''),
                    })

                # 解析响应
                responses = {}
                response_fields = []
                for status_code, resp_def in operation.get('responses', {}).items():
                    content = resp_def.get('content', {})
                    json_content = content.get('application/json', {})
                    schema = json_content.get('schema', {})
                    if '$ref' in schema:
                        schema = self._resolve_ref(schema['$ref'])
                    responses[status_code] = {
                        'description': resp_def.get('description', ''),
                        'schema': schema,
                    }
                    if status_code.startswith('2') and 'properties' in schema:
                        response_fields = self._extract_fields(schema)

                endpoint = APIEndpoint(
                    path=path,
                    method=method.upper(),
                    summary=operation.get('summary', ''),
                    description=operation.get('description', ''),
                    tags=operation.get('tags', []),
                    operation_id=operation.get('operationId', f"{method}_{path.replace('/', '_')}"),
                    parameters=parameters,
                    request_body=request_body,
                    request_fields=request_fields,
                    responses=responses,
                    requires_auth=self._check_auth(operation),
                    response_fields=response_fields,
                )
                self.endpoints.append(endpoint)

    def get_endpoints_by_tag(self, tag: str) -> List[APIEndpoint]:
        return [ep for ep in self.endpoints if tag in ep.tags]

    def get_auth_endpoints(self) -> List[APIEndpoint]:
        return [ep for ep in self.endpoints if ep.requires_auth]

    def get_public_endpoints(self) -> List[APIEndpoint]:
        return [ep for ep in self.endpoints if not ep.requires_auth]

    def get_schema(self, name: str) -> Optional[APISchema]:
        return self.schemas.get(name)

    def get_all_tags(self) -> List[str]:
        tags = set()
        for ep in self.endpoints:
            tags.update(ep.tags)
        return sorted(tags)

    def get_example_body(self, endpoint: APIEndpoint) -> Optional[Dict]:
        if endpoint.request_body and endpoint.request_body.get('example'):
            return endpoint.request_body['example']
        if endpoint.request_body and endpoint.request_fields:
            example = {}
            for fc in endpoint.request_fields:
                if fc.example is not None:
                    example[fc.name] = fc.example
                elif fc.enum:
                    example[fc.name] = fc.enum[0]
                elif fc.field_type == 'string':
                    example[fc.name] = f"test_{fc.name}"
                elif fc.field_type == 'integer':
                    example[fc.name] = 1
                elif fc.field_type == 'number':
                    example[fc.name] = 1.0
                elif fc.field_type == 'boolean':
                    example[fc.name] = True
                elif fc.field_type == 'array':
                    example[fc.name] = []
                elif fc.field_type == 'object':
                    example[fc.name] = {}
            return example if example else None
        return None

    def get_boundary_values(self, field: FieldConstraint) -> Dict[str, Any]:
        """生成字段的边界值测试数据"""
        values = {}
        if field.field_type == 'string':
            if field.max_length:
                values['max_length'] = 'a' * field.max_length
                values['over_max'] = 'a' * (field.max_length + 1)
            if field.min_length:
                values['min_length'] = 'a' * field.min_length if field.min_length > 0 else ''
                values['under_min'] = 'a' * max(0, field.min_length - 1) if field.min_length > 1 else 'a'
            values['empty'] = ''
            values['special_chars'] = '<script>alert(1)</script>'
            values['unicode'] = '测试中文'
            values['whitespace'] = '   '
            if field.format == 'email':
                values['invalid_email'] = 'not-an-email'
                values['valid_email'] = 'test@example.com'
        elif field.field_type in ('integer', 'number'):
            if field.minimum is not None:
                values['at_min'] = field.minimum
                values['below_min'] = field.minimum - 1
            if field.maximum is not None:
                values['at_max'] = field.maximum
                values['above_max'] = field.maximum + 1
            values['zero'] = 0
            values['negative'] = -1
            values['large'] = 999999999
        elif field.field_type == 'boolean':
            values['true'] = True
            values['false'] = False
        if field.enum:
            values['valid_enum'] = field.enum[0]
            values['invalid_enum'] = 'INVALID_VALUE_NOT_IN_ENUM'
        return values

    def get_path_params(self, endpoint: APIEndpoint) -> List[Dict]:
        """获取路径参数"""
        return [p for p in endpoint.parameters if p.get('in') == 'path']

    def get_query_params(self, endpoint: APIEndpoint) -> List[Dict]:
        """获取查询参数"""
        return [p for p in endpoint.parameters if p.get('in') == 'query']
