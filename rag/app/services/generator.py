"""答案生成：调用 DeepSeek。

DeepSeek 提供 OpenAI 兼容接口，因此直接用 openai SDK，只把 base_url 指过去，
以后换 Moonshot / 本地 vLLM 也只改配置。

用 AsyncOpenAI 而不是 OpenAI：FastAPI 是异步框架，
同步客户端会阻塞事件循环，导致并发请求排队。
"""

from openai import AsyncOpenAI

from ..errors import GenerationError

# prompt 模板。相比旧脚本改了三处（都是"无法回答"的诱因）：
# 1. 上下文只放一份，不再在 system 和 user 里各塞一遍；
# 2. 明确"有相关信息就必须作答"，避免模型因措辞不同而拒答；
# 3. 把拒答条件收紧为"上下文与问题完全无关"。
# {context} 由 format 填入，注意模板里不要出现其他花括号。
SYSTEM_TEMPLATE = (
    "你是一个严谨的问答助手，请只依据下面提供的「上下文」回答问题。\n"
    "【回答要求】：\n"
    "1. 直接给出结论，最多分 3 点，不要输出与问题无关的内容。\n"
    "2. 只要上下文中出现了相关信息，就必须据此作答，不要因为表述不完全一致就拒答。\n"
    "3. 仅当上下文与问题完全无关时，才回答“根据已知信息无法回答”。\n\n"
    "=== 上下文开始 ===\n{context}\n=== 上下文结束 ==="
)


class Generator:
    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # 没有配置 key 时不创建客户端，让服务仍能启动（导入/检索可用），
        # 直到真正调用生成时才报明确的错，而不是启动就崩
        self._client = (
            AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout) if api_key else None
        )

    @property
    def ready(self) -> bool:
        """是否具备生成能力（仅表示配了 key，不代表网络一定通）。"""
        return self._client is not None

    async def answer(self, question: str, contexts: list[str]) -> str:
        """根据召回的片段回答问题。

        contexts 通常 1~3 条（top_n），片段之间用分隔线隔开，
        让模型能区分不同来源，避免把两段话读串。
        """
        if self._client is None:
            raise GenerationError("未配置 DEEPSEEK_API_KEY，无法生成答案")

        context = "\n\n---\n\n".join(contexts) if contexts else "（无可用资料）"
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    # 系统消息：角色设定 + 约束 + 上下文
                    {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
                    # 用户消息：只放问题，上下文不再重复
                    {"role": "user", "content": f"问题：{question}"},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:  # 网络、鉴权、限流等统一收敛
            # 包装成业务异常，由 main.py 转成 502，避免泄漏 SDK 堆栈给调用方
            raise GenerationError(f"调用 {self.model} 失败：{exc}") from exc

        # content 理论上非空，保守处理 None；strip 去掉首尾多余换行
        return (response.choices[0].message.content or "").strip()
