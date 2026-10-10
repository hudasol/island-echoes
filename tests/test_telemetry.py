import sqlite3
import time

from fastapi.testclient import TestClient

from app.chat.service import ChatService
from app.config import Settings
from app.main import create_app
from app.telemetry import Telemetry, percentile
from tests.fakes import ScriptedLLM, fact, reply


def test_percentile():
    assert percentile([], 0.5) is None
    assert percentile([10], 0.95) == 10
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert percentile(list(range(1, 101)), 0.95) == 95.0


def test_disabled_telemetry_is_a_noop(tmp_path):
    t = Telemetry(None, enabled=False)
    t.record("chat", "hello", island="socotra")
    assert t.summary()["events"] == 0 and t.summary()["enabled"] is False


def test_question_text_is_not_stored_by_default(tmp_path):
    p = tmp_path / "t.db"
    t = Telemetry(p)
    t.record("chat", "How tall is the volcano?", island="tristan-da-cunha", answered=True, total_ms=10)
    row = sqlite3.connect(p).execute("SELECT question, qhash, qlen FROM events").fetchone()
    assert row[0] is None and len(row[1]) == 12 and row[2] == len("How tall is the volcano?")
    t2 = Telemetry(tmp_path / "q.db", log_questions=True)
    t2.record("chat", "How tall is the volcano?", island="x")
    assert sqlite3.connect(tmp_path / "q.db").execute("SELECT question FROM events").fetchone()[0].startswith("How tall")


def test_same_question_gets_same_hash_regardless_of_case_and_spacing(tmp_path):
    t = Telemetry(tmp_path / "t.db")
    t.record("library", "Hello  World", island="a")
    t.record("library", "hello world", island="a")
    assert t.summary()["repeat_questions"] == 1


def test_summary_aggregates(tmp_path):
    t = Telemetry(tmp_path / "t.db", log_questions=True)
    t.record("library", "tallest peak", island="socotra", quality="strong", answered=True, total_ms=5)
    t.record("library", "pizza", island="socotra", quality="none", answered=False, total_ms=7)
    t.record("library", "", island="socotra", quality="browse", total_ms=3)
    t.record("chat", "q1", island="galapagos", answered=True, provider="ollama", model="m", llm_ms=900, retrieval_ms=4,
             total_ms=910, fact_kept=3, fact_dropped=1, repaired=True, tokens_in=100, tokens_out=40)
    t.record("chat", "q2", island="galapagos", answered=False, provider="ollama", model="m", llm_ms=700, retrieval_ms=6,
             total_ms=710, fact_kept=0, fact_dropped=0, repaired=False)
    t.record("chat", "q3", island="galapagos", status="error", error="down")
    t.record("chat", "q4", island="bouvet", status="refused_no_evidence", answered=False, total_ms=2)
    s = t.summary(1)
    assert s["events"] == 7
    assert s["library"]["quality"] == {"strong": 1, "partial": 0, "none": 1, "browse": 1}
    assert s["library"]["no_answer_rate"] == 0.5
    c = s["chat"]
    assert (c["turns"], c["errors"], c["refused_no_evidence"], c["answered"]) == (4, 1, 1, 1)
    assert c["grounded_sentence_rate"] == 0.75 and c["repair_rate"] == 0.5
    assert c["tokens_in"] == 100 and c["by_model"] == {"ollama:m": 2}
    assert s["by_island"]["galapagos"] == 3
    assert {"island": "socotra", "question": "pizza"} in s["unanswered_questions"]


def test_window_excludes_old_events(tmp_path):
    t = Telemetry(tmp_path / "t.db")
    t.record("library", "a", island="x", quality="strong", answered=True)
    t._conn.execute("UPDATE events SET ts = ?", (time.time() - 10 * 86400,))
    t._conn.commit()
    assert t.summary(7)["events"] == 0 and t.summary(30)["events"] == 1


def test_api_records_and_serves_stats(tmp_path, store, retriever):
    s = Settings(telemetry_path=tmp_path / "t.db", telemetry=True, anthropic_api_key=None, read_rate_per_min=1000)
    llm = ScriptedLLM(reply(fact("Socotra's highest point is Mashanig at about 1,503 m.", "SOC-011")))
    c = TestClient(create_app(s, ChatService(store, retriever, llm)))
    c.get("/api/library/search", params={"island": "socotra", "q": "tallest mountain"})
    c.get("/api/library/search", params={"island": "socotra", "q": "pizza recipe"})
    c.post("/api/chat", json={"island": "socotra", "message": "What is the highest mountain on Socotra?"})
    stats = c.get("/api/stats", params={"days": 1}).json()
    assert stats["events"] == 3 and stats["chat"]["turns"] == 1 and stats["chat"]["answered"] == 1
    assert stats["library"]["quality"]["none"] == 1
    assert "pizza" not in str(stats) and "highest mountain" not in str(stats) and "unanswered_questions" not in stats
    h = c.get("/api/health").json()
    assert h["chat_enabled"] is True and h["llm"] == "scripted:test" and h["retrieval_mode"] == "bm25"
