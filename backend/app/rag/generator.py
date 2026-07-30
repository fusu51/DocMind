"""生成 — 上下文压缩 + Prompt 构建 → 调用 LLM → 流式输出"""
import re
from typing import List, Dict, Any, AsyncGenerator

from ..config import (
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_CHAT_MODEL,
    LLM_BASE_URL,
    MAX_CONTEXT_TOKENS,
)

SYSTEM_PROMPT = """你是一个文档问答助手。请根据提供的文档片段回答用户问题。

规则：
1. 仅基于文档片段内容回答，不要编造信息
2. 如果片段不足以回答问题，请明确说明"文档中未提及"
3. 回答时标注引用的片段编号，例如 [1]、[2]
4. 用中文回答
"""

REFUSAL_PROMPT = """【重要指令】
以下文档片段与用户问题的相关性较弱（仅有弱相关或部分相关）。
请严格遵循以下规则：
1. 如果片段内容不足以支撑准确回答，请直接说"文档中未提及此信息"，绝对不要推测或补充
2. 如果仅有部分相关，明确说明哪些内容是文档中有的，哪些是你无法确认的
3. 宁可拒答，不可编造"""


# ============================================================
#  L4: 上下文压缩
# ============================================================

def compress_chunks(
        chunks: List[Dict[str, Any]],
        max_tokens: int = MAX_CONTEXT_TOKENS,
) -> List[Dict[str, Any]]:
    """
    压缩检索片段，确保不超 token 预算。
    策略:
        1. 去重 — 大段重叠的片段只保留分数最高的
        2. 按分数截断 — 超出预算时从末尾裁剪
        3. 文本截断 — 每条片段最多保留 800 字符
    """
    if not chunks:
        return chunks

    # 1. 去重：检测文本 Jaccard 重叠 > 70% 的片段，只保留分数高的
    deduped = _deduplicate_chunks(chunks)

    # 2. 按 score 降序排列，逐条累加直到超过 token 预算
    sorted_chunks = sorted(deduped, key=lambda c: c.get("score", 0), reverse=True)

    result = []
    total_tokens = 0

    for c in sorted_chunks:
        # 截断过长文本
        text = c["text"][:800]
        tokens = _estimate_tokens(text)

        if total_tokens + tokens > max_tokens and result:
            break  # 超出预算，停止添加

        c["text"] = text
        result.append(c)
        total_tokens += tokens

    return result


def _deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Jaccard 字词重叠去重。
    如果两个片段的 4-gram 重叠 > 70%，保留 score 高的。
    """
    if len(chunks) <= 1:
        return chunks

    # 按分数降序排列，分数高的优先保留
    sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)
    kept = []
    kept_ngrams = []

    for c in sorted_chunks:
        ngrams = _char_ngrams(c["text"], n=4)
        is_dup = False

        for existing in kept_ngrams:
            overlap = len(ngrams & existing) / len(ngrams) if ngrams else 0
            if overlap > 0.7:
                is_dup = True
                break

        if not is_dup:
            kept.append(c)
            kept_ngrams.append(ngrams)

    return kept


def _char_ngrams(text: str, n: int = 4) -> set:
    """字符级 n-gram 集合"""
    text = text.replace(" ", "").replace("\n", "")
    if len(text) <= n:
        return {text}
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    return int(chinese_chars * 1.5 + english_words * 1.3 + len(text) * 0.3)


# ============================================================
#  流式生成
# ============================================================

async def stream_generate(
        question: str,
        chunks: List[Dict[str, Any]],
        refusal_hint: bool = False,
        history: List[Dict] = None,
) -> AsyncGenerator[dict, None]:
    """
    流式生成回答。
    流程: 压缩 chunks → 构建 prompt → 调 LLM → yield {type, content}
    """
    # L4: 上下文压缩
    compressed = compress_chunks(chunks)

    system_prompt = SYSTEM_PROMPT
    if refusal_hint:
        system_prompt = REFUSAL_PROMPT + "\n\n" + SYSTEM_PROMPT

    user_prompt = _build_user_prompt(question, compressed, history)

    print(f"[Generator] provider={LLM_PROVIDER}, model={LLM_CHAT_MODEL}, "
          f"chunks={len(chunks)}→{len(compressed)}, tokens≈{_estimate_tokens(user_prompt)}")

    if LLM_PROVIDER == "claude":
        async for token in _stream_claude(user_prompt, system_prompt):
            yield {"type": "token", "content": token}
    else:
        async for event in _stream_openai(user_prompt, system_prompt):
            yield event


async def _stream_openai(user_prompt: str, system_prompt: str = SYSTEM_PROMPT) -> AsyncGenerator[dict, None]:
    """OpenAI 流式 — 兼容 DeepSeek V4 推理模型"""
    from openai import AsyncOpenAI

    kwargs = {
        "api_key": LLM_API_KEY,
        "timeout": 120.0,
        "max_retries": 1,
    }
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL

    client = AsyncOpenAI(**kwargs)

    stream = await client.chat.completions.create(
        model=LLM_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        temperature=0.3,
        timeout=60.0,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.reasoning_content:
            yield {"type": "reasoning", "content": delta.reasoning_content}
        elif delta.content:
            yield {"type": "token", "content": delta.content}


async def _stream_claude(user_prompt: str, system_prompt: str = SYSTEM_PROMPT) -> AsyncGenerator[str, None]:
    """Claude 流式"""
    from anthropic import AsyncAnthropic

    kwargs = {"api_key": LLM_API_KEY}
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL

    client = AsyncAnthropic(**kwargs)

    async with client.messages.stream(
            model=LLM_CHAT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


def _build_user_prompt(question: str, chunks: List[Dict[str, Any]], history: List[Dict] = None) -> str:
    parts = []

    # 对话历史（最近几轮）
    if history:
        history_parts = []
        for h in history[-6:]:  # 最多 3 轮
            role = "用户" if h["role"] == "user" else "助手"
            history_parts.append(f"**{role}**：{h['content']}")
        if history_parts:
            parts.append("## 历史对话\n\n" + "\n\n".join(history_parts))

    # 文档片段
    chunk_parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = f"[{i}] 📄 {chunk.get('doc_name', '未知')} · 第{chunk.get('page_number', 1)}页"
        text = chunk.get("parent_text") or chunk["text"]
        chunk_parts.append(f"{source}\n{text}")

    parts.append("## 文档片段\n\n" + "\n\n---\n\n".join(chunk_parts))
    parts.append(f"## 用户问题\n\n{question}\n\n请根据以上片段回答。")

    return "\n\n".join(parts)

