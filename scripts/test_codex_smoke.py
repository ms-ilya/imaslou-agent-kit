#!/usr/bin/env python3
# ABOUTME: Ensure live model smoke checks reject misleading or incomplete host evidence.
import copy
import unittest

from smoke_codex_models import verify


def evidence():
    events = []

    def item(thread, turn, value):
        events.append({"method": "item/completed", "params": {
            "threadId": thread, "turnId": turn, "item": value,
        }})

    item("parent", "p1", {"type": "subAgentActivity", "kind": "started",
                           "agentThreadId": "child", "model": "selected"})
    item("parent", "p1", {"type": "subAgentActivity", "kind": "interacted", "agentThreadId": "child"})
    # An assistant's claim is deliberately different from host evidence.
    item("parent", "p1", {"type": "agentMessage", "text": "I used another-model."})
    for index, (key, value) in enumerate((("feature_enabled", "true"), ("retry_limit", "3")), 1):
        turn = str(index)
        item("child", turn, {"type": "commandExecution", "command": "nl -ba settings.txt", "exitCode": 0,
                             "aggregatedOutput": "1\tfeature_enabled = true\n2\tretry_limit = 3\n"})
        item("child", turn, {"type": "agentMessage", "phase": "final_answer", "text":
                             f"Q: What is the value of {key} in settings.txt?\n"
                             f"FACT: {key} is {value}.\nEVIDENCE: settings.txt:{index}\n"
                             "CONFIDENCE: high\nNOT_FOUND: none"})
        events.append({"method": "turn/completed", "params": {"threadId": "child", "turn": {
            "id": turn, "status": "completed", "error": None,
        }}})
    child = {"id": "child", "parentThreadId": "parent", "model": "selected",
             "ephemeral": True, "path": None, "forkedFromId": None}
    return events, child


class HostEvidence(unittest.TestCase):
    def test_uses_host_records_instead_of_model_self_report(self):
        events, child = evidence()
        result = verify(events, "parent", child, "selected")
        self.assertEqual(result["completed_child_turns"], 2)
        self.assertEqual(result["resolved_spawn_model"], "selected")

    def test_rejects_wrong_spawn_model(self):
        events, child = evidence()
        events[0]["params"]["item"]["model"] = "wrong"
        with self.assertRaisesRegex(RuntimeError, "spawn model"):
            verify(events, "parent", child, "selected")

    def test_rejects_changed_model_on_continuation(self):
        events, child = evidence()
        child["model"] = "wrong"
        with self.assertRaisesRegex(RuntimeError, "changed during continuation"):
            verify(events, "parent", child, "selected")

    def test_rejects_failed_or_missing_turn(self):
        events, child = evidence()
        for status in ("failed", "interrupted"):
            with self.subTest(status=status):
                modified = copy.deepcopy(events)
                modified[-1]["params"]["turn"]["status"] = status
                with self.assertRaisesRegex(RuntimeError, "turn failed"):
                    verify(modified, "parent", child, "selected")
        with self.assertRaisesRegex(RuntimeError, "exactly two turns"):
            verify(events[:-1], "parent", child, "selected")

    def test_requires_successful_read(self):
        events, child = evidence()
        for event in events:
            item = event["params"].get("item", {})
            if item.get("type") == "commandExecution":
                item["exitCode"] = 1
        with self.assertRaisesRegex(RuntimeError, "successfully read"):
            verify(events, "parent", child, "selected")

    def test_accepts_evidence_read_on_previous_turn(self):
        events, child = evidence()
        events = [event for event in events if not (
            event["params"].get("turnId") == "2"
            and event["params"].get("item", {}).get("type") == "commandExecution")]
        verify(events, "parent", child, "selected")

    def test_rejects_line_not_observed_before_answer(self):
        events, child = evidence()
        # A later read cannot justify the first answer's earlier citation.
        events[3]["params"]["item"]["aggregatedOutput"] = "2\tretry_limit = 3\n"
        with self.assertRaisesRegex(RuntimeError, "cited fixture line before answering"):
            verify(events, "parent", child, "selected")

    def test_rejects_replacement_worker(self):
        events, child = evidence()
        events[1]["params"]["item"]["agentThreadId"] = "replacement"
        with self.assertRaisesRegex(RuntimeError, "same child"):
            verify(events, "parent", child, "selected")

    def test_rejects_wrong_citation_and_extra_prose(self):
        events, child = evidence()
        for text in ("EVIDENCE: settings.txt:99", "EVIDENCE: settings.txt:1\nExtra prose"):
            with self.subTest(text=text):
                modified = copy.deepcopy(events)
                modified[4]["params"]["item"]["text"] = modified[4]["params"]["item"]["text"].replace(
                    "EVIDENCE: settings.txt:1", text)
                with self.assertRaises(RuntimeError):
                    verify(modified, "parent", child, "selected")

    def test_rejects_nested_delegation(self):
        events, child = evidence()
        extra = copy.deepcopy(events[0])
        extra["params"]["threadId"] = "child"
        events.append(extra)
        with self.assertRaisesRegex(RuntimeError, "additional worker"):
            verify(events, "parent", child, "selected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
