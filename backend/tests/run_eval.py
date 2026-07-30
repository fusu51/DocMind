"""DocMind 管线评估 — split_merged.json + 外域拒答 + 多维度评分"""
import json, asyncio, sys, time
sys.path.insert(0, "D:\\Code\\Agent\\ResumeProject_05\\DocMind\\backend")

from dotenv import load_dotenv; load_dotenv()

from openai import OpenAI
from app.rag.hybrid_search import hybrid_search
from app.rag.generator import stream_generate
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_CHAT_MODEL

# ===== 裁判 =====
kwargs = {"api_key": LLM_API_KEY}
if LLM_BASE_URL:
    kwargs["base_url"] = LLM_BASE_URL
judge = OpenAI(**kwargs)

SAMPLE_SIZE = 50

# 外域拒答题（不在知识库中，验证双阶拒答）
REJECT_QUESTIONS = [
    ("铁皮石斛的DNA序列是什么", "文档中未提及"),
    ("2026年世界杯冠军是谁", "文档中未提及"),
    ("Python装饰器的实现原理", "文档中未提及"),
    ("新冠病毒起源于哪个城市", "文档中未提及"),
    ("马斯克收购推特的金额是多少", "文档中未提及"),
]

# ===== 加载 =====
with open("split_merged.json", "r", encoding="utf-8") as f:
    data = json.load(f)
items = data["event_summary"]
import random; random.seed(42); random.shuffle(items)
items = items[:SAMPLE_SIZE]

# 外域题追加
reject_items = [{"event": q, "summary": gt} for q, gt in REJECT_QUESTIONS]
all_items = reject_items + items
print(f"知识库内 {SAMPLE_SIZE} 题 + 外域拒答 {len(REJECT_QUESTIONS)} 题，裁判: {LLM_CHAT_MODEL}\n")


# ===== CRUD 分类 =====
def classify(question, default_type=None):
    """如果传入 default_type（如 reject），直接返回"""
    if default_type:
        return default_type
    kw_map = {
        "为什么": "infer", "原因": "infer", "如何": "infer", "是否": "infer",
        "影响": "infer", "意义": "infer", "导致": "infer",
        "比较": "compare", "差异": "compare", "相比": "compare",
        "不同": "compare", "分别": "compare", "对比": "compare",
    }
    for kw, t in kw_map.items():
        if kw in question:
            return t
    return "read"


# ===== 评分 =====
def score(question, answer, contexts, ground_truth):
    if not answer:
        return {"faithfulness": 0, "context_precision": 0, "context_recall": 0, "answer_correctness": 0}

    # 拒答检测
    abstain_kw = ["未提及", "没有", "不包含", "无法", "未提供", "没有找到", "文档中未"]
    is_abstain = any(kw in answer for kw in abstain_kw) and len(answer) < 50
    if is_abstain:
        return {"faithfulness": 10, "context_precision": 0, "context_recall": 0, "answer_correctness": 0, "abstained": True}

    ctx = "\n\n".join(f"[{i+1}] {c[:300]}" for i, c in enumerate(contexts[:6]))

    prompt = f"""评估 RAG 回答质量。1~10 分，只输出 JSON 对象。

问题：{question}

检索片段（最多 6 条）：
{ctx}

模型回答：{answer[:600]}

参考摘要：{ground_truth[:300]}

{{
    "faithfulness": "回答是否 100% 基于检索片段，而不是模型自己编的？10=完全基于片段",
    "context_precision": "检索到的片段中，有多少条和问题相关？10=全部相关",
    "context_recall": "参考摘要中的关键信息，检索片段覆盖了多少？10=完全覆盖",
    "answer_correctness": "回答和参考摘要相比，核心事实是否准确？10=完全准确"
}}

只输出 JSON："""

    resp = judge.chat.completions.create(
        model=LLM_CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4096,
    )
    raw = resp.choices[0].message.content.strip()
    return _parse(raw)


def _parse(raw):
    import re
    # 1. 直接解析
    try: return json.loads(raw)
    except: pass
    # 2. 去 markdown 包裹
    for prefix in ["```json", "```"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
            if raw.endswith("```"): raw = raw[:-3].strip()
            try: return json.loads(raw)
            except: pass
    # 3. 正则提取数字
    nums = re.findall(r'\d+', raw)
    if len(nums) >= 4:
        return {"faithfulness": int(nums[0]), "context_precision": int(nums[1]),
                "context_recall": int(nums[2]), "answer_correctness": int(nums[3])}
    return {"faithfulness": 0, "context_precision": 0, "context_recall": 0, "answer_correctness": 0}


# ===== 主流程 =====
async def evaluate():
    rows = []
    groups = {"read": [], "infer": [], "compare": [], "reject": []}
    failed_parse = 0
    abstain_count = 0
    start = time.time()

    for i, item in enumerate(all_items):
        question = item.get("event", "").strip()
        ground_truth = item.get("summary", "").strip()
        if not question:
            continue

        # 外域题固定 type=reject，知识库内题自动分类
        is_reject = i < len(REJECT_QUESTIONS)
        crud_type = "reject" if is_reject else classify(question)

        chunks, pipeline = hybrid_search(question)
        contexts = [c.get("text", "") for c in chunks]

        answer = ""
        async for event in stream_generate(question, chunks):
            if event["type"] == "token":
                answer += event["content"]

        s = score(question, answer, contexts, ground_truth)

        if s.get("abstained"): abstain_count += 1
        if sum(v for k, v in s.items() if k != "abstained") == 0 and not s.get("abstained"):
            failed_parse += 1

        row = {
            "question": question[:80],
            "answer": answer[:200],
            "ground_truth": ground_truth[:200],
            "type": crud_type,
            "top1_score": pipeline.get("top1_score", 0),
            "abstain_level": pipeline.get("abstain_level", "none"),
            **{k: v for k, v in s.items() if k != "abstained"},
            "abstained": s.get("abstained", False),
        }
        groups.setdefault(crud_type, []).append(s)
        rows.append(row)

        elapsed = time.time() - start
        eta = (elapsed / (i + 1)) * (len(all_items) - i - 1)
        r = s.get('context_recall', 0)
        print(f"[{i+1:02d}/{len(all_items)}] [{crud_type:7s}] "
              f"f={s.get('faithfulness',0):2d} p={s.get('context_precision',0):2d} "
              f"r={r:2d} c={s.get('answer_correctness',0):2d}"
              f"{' 🛡️' if s.get('abstained') else '  '}"
              f" | {question[:45]}  ETA:{eta:.0f}s")

    # ===== 汇总 =====
    elapsed = time.time() - start
    print(f"\n{'='*65}")
    print(f"DocMind CRUD-RAG 评估 — {len(all_items)} 题 — 耗时 {elapsed:.0f}s")
    print(f"裁判: {LLM_CHAT_MODEL}  |  拒答: {abstain_count}  |  解析失败: {failed_parse}")
    print(f"{'='*65}")

    labels = {
        "read":    "Read    (直接查找)",
        "compare": "Compare (多片段对比)",
        "infer":   "Infer   (推理判断)",
        "reject":  "Reject  (外域拒答)",
    }

    for t, label in labels.items():
        items_in_group = [r for r in rows if r["type"] == t]
        if not items_in_group: continue
        n = len(items_in_group)

        if t == "reject":
            abstained = [r for r in items_in_group if r.get("abstained")]
            print(f"\n{label} ({n} 题): 拒答率 {len(abstained)}/{n} ({len(abstained)/n*100:.0f}%)")
            continue

        valid = [r for r in items_in_group if not r.get("abstained") and r.get("faithfulness", 0) > 0]
        if not valid:
            print(f"\n{label} ({n} 题): 全部拒答")
            continue

        avg = lambda k: sum(r[k] for r in valid) / len(valid)
        print(f"\n{label} ({n} 题, {len(valid)} 有效):")
        print(f"  Faithfulness:       {avg('faithfulness'):.1f}")
        print(f"  Context Precision:  {avg('context_precision'):.1f}")
        print(f"  Context Recall:     {avg('context_recall'):.1f}")
        print(f"  Answer Correctness:  {avg('answer_correctness'):.1f}")

    # 整体（不含外域拒答）
    valid = [r for r in rows if r["type"] != "reject" and not r.get("abstained") and r.get("faithfulness", 0) > 0]
    if valid:
        n = len(valid)
        print(f"\n{'─'*65}")
        print(f"整体 ({n} 有效题):")
        print(f"  Faithfulness:       {sum(r['faithfulness'] for r in valid)/n:.1f}")
        print(f"  Context Precision:  {sum(r['context_precision'] for r in valid)/n:.1f}")
        print(f"  Context Recall:     {sum(r['context_recall'] for r in valid)/n:.1f}")
        print(f"  Answer Correctness:  {sum(r['answer_correctness'] for r in valid)/n:.1f}")

    # 管线统计
    top1s = [r["top1_score"] for r in rows if r.get("top1_score", 0) > 0]
    if top1s:
        print(f"\n{'─'*65}")
        print(f"管线统计:")
        print(f"  Avg Top1 Reranker Score: {sum(top1s)/len(top1s):.3f}")
        print(f"  Abstain Rate:            {abstain_count}/{len(rows)} ({abstain_count/len(rows)*100:.0f}%)")

    with open("eval_result.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n→ eval_result.json")


if __name__ == "__main__":
    asyncio.run(evaluate())
