"""LLM judge: does each answer sentence follow from the evidence it cites?

The judge sees only the question, the cited evidence text and the numbered answer sentences. It does
not see which answer is "expected". Using the same model family as the answerer can flatter the
score; set JUDGE_MODEL to a different model to reduce that bias (the README states this limit).
"""

from __future__ import annotations

import json

JUDGE_SYSTEM = """You are a strict fact-checker for a grounded question-answering system.

You receive a QUESTION, an ANSWER split into numbered sentences (each lists the evidence IDs it cites), and the \
text of the cited EVIDENCE. The cited evidence is the only ground truth. Never use outside knowledge, even if \
you know the claim is true.

For every sentence give one verdict:
- supported: every claim in the sentence is stated in, or directly entailed by, the evidence that sentence cites.
- partially_supported: part of the sentence is supported but some detail (a number, name, date, cause or \
qualifier) is not in the cited evidence.
- unsupported: the cited evidence does not state the main claim, or the sentence cites nothing and states a fact.
- contradicted: the cited evidence says something different (wrong number, date, status, direction).
- no_claim: a greeting, stage business or an in-character remark that asserts no fact about the world.

Judge wording fairly: paraphrase, first-person framing of facts about the speaker's own species or island, and \
attribution ("according to Wikipedia") are fine. A sentence that states a fact must be judged against its OWN \
cited evidence, not against other evidence in the answer.

Also answer:
- answers_question: does the answer, as a whole, actually address what was asked using the evidence?
- states_conflict: if the cited evidence contains disagreeing values for the thing asked, does the answer report \
the different values and indicate that sources differ? Use "yes", "no", or "not_applicable" when the evidence \
does not disagree."""

JUDGE_TOOL = {
    "name": "grade",
    "description": "Return the verdicts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "verdict": {
                            "type": "string",
                            "enum": ["supported", "partially_supported", "unsupported", "contradicted", "no_claim"],
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["index", "verdict", "reason"],
                },
            },
            "answers_question": {"type": "boolean"},
            "states_conflict": {"type": "string", "enum": ["yes", "no", "not_applicable"]},
        },
        "required": ["verdicts", "answers_question", "states_conflict"],
    },
}


def build_user(question: str, sentences: list[dict], evidence: dict[str, str]) -> str:
    lines = []
    for i, s in enumerate(sentences):
        cites = ", ".join(s["cites"]) or "(none)"
        lines.append(f'{i}. [{s["kind"]}] cites: {cites}\n   "{s["text"]}"')
    ev = "\n\n".join(f"[{k}]\n{v}" for k, v in evidence.items()) or "(no evidence cited)"
    return f"<question>\n{question}\n</question>\n\n<answer>\n" + "\n".join(lines) + f"\n</answer>\n\n<evidence>\n{ev}\n</evidence>"


class AnthropicJudge:
    def __init__(self, api_key: str, model: str):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=3)
        self.model = model

    def grade(self, question: str, sentences: list[dict], evidence: dict[str, str]) -> dict:
        kwargs = dict(
            model=self.model,
            max_tokens=1500,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": build_user(question, sentences, evidence)}],
            tools=[JUDGE_TOOL],
            tool_choice={"type": "tool", "name": "grade"},
        )
        resp = self.client.messages.create(**kwargs)
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                data = dict(block.input)
                data["verdicts"] = {str(v["index"]): v["verdict"] for v in data.get("verdicts", [])}
                data["reasons"] = {str(v["index"]): v["reason"] for v in block.input.get("verdicts", [])}
                return data
        raise RuntimeError("judge returned no verdicts")


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)
