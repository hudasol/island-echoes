import json

import httpx
import pytest
import respx

from app.chat import grounding
from app.chat.prompts import build_user
from app.config import Settings
from app.llm import LLMError, build_llm, parse_answer_json
from app.llm.extractive import ExtractiveAnswerLLM, first_sentence
from app.llm.ollama import OllamaAnswerLLM
from app.llm.openai_compat import OpenAICompatAnswerLLM

GOOD = {"answered": True, "sentences": [{"text": "It is 1,503 m.", "kind": "fact", "cites": ["SOC-011"]}], "missing": ""}


def test_parse_plain_fenced_and_wrapped_json():
    raw = json.dumps(GOOD)
    assert parse_answer_json(raw)["sentences"][0]["cites"] == ["SOC-011"]
    assert parse_answer_json(f"```json\n{raw}\n```")["answered"] is True
    assert parse_answer_json(f"Sure! Here you go: {raw} Hope that helps")["answered"] is True


def test_parse_normalises_bad_shapes():
    out = parse_answer_json(json.dumps({"answered": 1, "sentences": [{"text": "x", "kind": "weird", "cites": "SOC-011"}, "junk", {"nope": 1}]}))
    assert out["sentences"] == [{"text": "x", "kind": "fact", "cites": ["SOC-011"]}] and out["answered"] is True and out["missing"] == ""


def test_parse_cleans_citation_wrappers_but_not_ids():
    raw = json.dumps({"answered": True, "missing": "", "sentences": [{"text": "x", "kind": "fact", "cites": ["[SOC-011]", ".SOC-012", " SOC-013 ", "`SOC-014`", "", "..."]}]})
    assert parse_answer_json(raw)["sentences"][0]["cites"] == ["SOC-011", "SOC-012", "SOC-013", "SOC-014"]


@pytest.mark.parametrize("bad", ["", "no json here", "{broken", "[1,2]", '{"sentences": "x"}'])
def test_parse_rejects_garbage(bad):
    with pytest.raises(LLMError):
        parse_answer_json(bad)


@respx.mock
def test_ollama_sends_schema_and_reads_usage():
    route = respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": json.dumps(GOOD)}, "prompt_eval_count": 120, "eval_count": 30})
    )
    llm = OllamaAnswerLLM("qwen2.5:3b-instruct")
    assert llm.answer("sys", "user")["answered"] is True
    body = json.loads(route.calls[0].request.content)
    assert body["format"]["type"] == "object" and body["options"]["temperature"] == 0 and body["stream"] is False
    assert (llm.last_usage.input_tokens, llm.last_usage.output_tokens) == (120, 30)


@respx.mock
def test_ollama_errors_are_readable():
    respx.post("http://localhost:11434/api/chat").mock(return_value=httpx.Response(404))
    with pytest.raises(LLMError, match="ollama pull"):
        OllamaAnswerLLM("nope").answer("s", "u")
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("x"))
    with pytest.raises(LLMError, match="not reachable"):
        OllamaAnswerLLM("nope").answer("s", "u")


@respx.mock
def test_openai_compat_falls_back_to_json_mode_and_maps_errors():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["response_format"]["type"])
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": "unsupported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}], "usage": {"prompt_tokens": 9, "completion_tokens": 4}})

    respx.post("https://example.test/v1/chat/completions").mock(side_effect=handler)
    llm = OpenAICompatAnswerLLM("https://example.test/v1", "m", "tok", provider="huggingface")
    assert llm.answer("s", "u")["answered"] is True
    assert calls == ["json_schema", "json_object"] and llm.last_usage.output_tokens == 4
    respx.post("https://example.test/v1/chat/completions").mock(return_value=httpx.Response(429))
    with pytest.raises(LLMError, match="rate limit"):
        llm.answer("s", "u")
    respx.post("https://example.test/v1/chat/completions").mock(return_value=httpx.Response(401))
    with pytest.raises(LLMError, match="token"):
        llm.answer("s", "u")


def test_extractive_answers_pass_the_grounding_checks(retriever, store):
    res = retriever.search("socotra", "What is the highest mountain on Socotra?")
    llm = ExtractiveAnswerLLM(max_sentences=2)
    out = llm.answer("sys", build_user("What is the highest mountain on Socotra?", res.evidence))
    assert out["answered"] and out["sentences"] and all(s["cites"] for s in out["sentences"])
    isl = store.get("socotra")
    names = grounding.allowed_names(isl.name, isl.alt_names, [isl.creatures[0].common_name, isl.creatures[0].scientific_name])
    checked = grounding.check_sentences(out["sentences"], {e.id: e for e in res.evidence}, "What is the highest mountain on Socotra?", names)
    assert all(c.ok for c in checked), [c.issues for c in checked if not c.ok]


def test_extractive_with_no_evidence_declines():
    out = ExtractiveAnswerLLM().answer("s", build_user("q", []))
    assert out["answered"] is False and out["sentences"] == []


def test_first_sentence_keeps_abbreviations_and_limits_length():
    assert first_sentence("Mashanig is at about 1,503 m. It is in the Hajhir Mountains.") == "Mashanig is at about 1,503 m."
    assert len(first_sentence("word " * 200)) <= 322


def test_factory_selects_providers_and_validates_config():
    assert build_llm(Settings(telemetry=False)) is None
    assert build_llm(Settings(llm_provider="off", anthropic_api_key="x")) is None
    assert build_llm(Settings(llm_provider="extractive")).provider == "extractive"
    o = build_llm(Settings(llm_provider="ollama", llm_model="llama3.2:3b"))
    assert (o.provider, o.model) == ("ollama", "llama3.2:3b")
    with pytest.raises(LLMError, match="HF_TOKEN"):
        build_llm(Settings(llm_provider="huggingface"))
    h = build_llm(Settings(llm_provider="huggingface", hf_token="t"))
    assert h.provider == "huggingface" and "Qwen" in h.model
    with pytest.raises(LLMError, match="unknown"):
        build_llm(Settings(llm_provider="bogus"))
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        build_llm(Settings(llm_provider="anthropic"))
