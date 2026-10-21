#!/usr/bin/env python3
# ABOUTME: Verify native Codex subagent model routing with ephemeral read-only chats.
"""Opt-in live test; uses authenticated Codex and sends two repository instructions.

Requires an app-server exposing subAgentActivity.model and ephemeral threads.
This is not part of the offline test suite. Evidence stays in a temporary directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import queue
import re
import subprocess
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (ROOT / "docs/runtime.md", ROOT / "plugins/feature-spec/agents/fact-finder.md")
FIXTURE = "feature_enabled = true\nretry_limit = 3\n"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Server:
    def __init__(self, executable, directory, default_model):
        self.events = []
        self.sequence = 0
        self.queue = queue.Queue()
        self.log = (directory / "server.log").open("w")
        self.record = (directory / "events.jsonl").open("w")
        command = [executable]
        overrides = {
            "sqlite_home": str(directory / "state"),
            "log_dir": str(directory / "logs"),
            "agents.enabled": True,
            "agents.max_concurrent_threads_per_session": 2,
        }
        if default_model is not None:
            overrides["agents.default_subagent_model"] = default_model
        for key, value in overrides.items():
            command.extend(["-c", f"{key}={json.dumps(value)}"])
        command.extend(["app-server", "--stdio"])
        try:
            self.process = subprocess.Popen(
                command, cwd=directory, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, text=True, bufsize=1,
            )
        except Exception:
            self.log.close()
            self.record.close()
            raise
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.record.write(line)
                self.record.flush()
                self.queue.put(json.loads(line))
        except Exception as error:
            self.queue.put(error)
        finally:
            self.queue.put(None)

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def receive(self, deadline):
        try:
            message = self.queue.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty as error:
            raise TimeoutError("Codex did not complete before the timeout") from error
        require(message is not None, "Codex exited; inspect server.log")
        if isinstance(message, Exception):
            raise message
        self.events.append(message)
        require(not ("method" in message and "id" in message),
                f"Unexpected server request: {message.get('method')}; no approvals are granted")
        return message

    def request(self, method, params):
        self.sequence += 1
        self.send({"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params})
        deadline = time.monotonic() + 60
        while True:
            message = self.receive(deadline)
            if message.get("id") == self.sequence:
                require("error" not in message, f"{method}: {message.get('error')}")
                return message["result"]

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.reader.join(timeout=5)
        self.record.close()
        self.log.close()
        self.process.stdin.close()
        self.process.stdout.close()


def completed_items(events, thread_id=None, turn_id=None):
    return [event["params"]["item"] for event in events
            if event.get("method") == "item/completed"
            and (thread_id is None or event["params"]["threadId"] == thread_id)
            and (turn_id is None or event["params"]["turnId"] == turn_id)]


def verify(events, parent_id, child, expected):
    """Use host activity and completed turns, never an assistant's model claim."""
    parent_items = completed_items(events, parent_id)
    starts = [item for item in parent_items
              if item["type"] == "subAgentActivity" and item["kind"] == "started"]
    require(len(starts) == 1, "Expected exactly one spawned worker")
    require(sum(item["type"] == "subAgentActivity" and item.get("kind") == "started"
                for item in completed_items(events)) == 1, "Unexpected additional worker")
    require(starts[0]["model"] == expected, "Host resolved an unexpected spawn model")
    require(starts[0]["agentThreadId"] == child["id"], "Wrong child inspected")
    require(child["parentThreadId"] == parent_id, "Child has a different parent")
    require(child["model"] == expected, "Child model changed during continuation")
    require(child["ephemeral"] and child["path"] is None, "Child is not ephemeral")
    require(child["forkedFromId"] is None, "Child is a fork of an existing chat")
    interactions = [item for item in parent_items
                    if item["type"] == "subAgentActivity" and item["kind"] == "interacted"]
    require(len(interactions) == 1 and interactions[0]["agentThreadId"] == child["id"],
            "Expected one continuation of the same child")
    turns = [event["params"]["turn"] for event in events
             if event.get("method") == "turn/completed"
             and event["params"]["threadId"] == child["id"]]
    require(len(turns) == 2, "Worker did not complete exactly two turns")
    replies = []
    observed_output = ""
    for index, turn in enumerate(turns, 1):
        require(turn["status"] == "completed" and not turn.get("error"), "Worker turn failed")
        items = completed_items(events, child["id"], turn["id"])
        reads = [item for item in items if item["type"] == "commandExecution"]
        # A continuation can cite an unchanged line opened on an earlier turn.
        observed_output += "\n".join(item.get("aggregatedOutput") or "" for item in reads
                                     if item.get("exitCode") == 0 and "settings.txt" in item["command"])
        finals = [item["text"] for item in items
                  if item["type"] == "agentMessage" and item.get("phase") == "final_answer"]
        require(len(finals) == 1, "Worker did not return one final report")
        reply = finals[0]
        fields = re.findall(r"^(Q|FACT|EVIDENCE|CONFIDENCE|NOT_FOUND): (.+)$", reply, re.M)
        require([key for key, _ in fields] == ["Q", "FACT", "EVIDENCE", "CONFIDENCE", "NOT_FOUND"],
                "Fact-finder report does not match its schema")
        require(len(reply.strip().splitlines()) == 5, "Extra prose outside fact-finder schema")
        values = dict(fields)
        key, value = ("feature_enabled", "true") if index == 1 else ("retry_limit", "3")
        require(re.search(rf"(?m)^\s*(?:\d+\s+)?{key} = {value}\s*$", observed_output),
                "Worker did not successfully read the cited fixture line before answering")
        require(values["Q"] == f"What is the value of {key} in settings.txt?", "Wrong question")
        require(re.search(rf"\b{value}\b", values["FACT"]), "Wrong fact")
        require(values["EVIDENCE"] == f"settings.txt:{index}", "Wrong evidence line")
        require(values["CONFIDENCE"] == "high" and values["NOT_FOUND"] == "none", "Unexpected evidence status")
        replies.append(reply)
    require(not any(item["type"] == "fileChange" for item in completed_items(events)), "Unexpected file edit")
    return {"resolved_spawn_model": starts[0]["model"], "model_after_continuation": child["model"],
            "child_id": child["id"], "completed_child_turns": len(turns), "replies": replies}


def run_case(args, case, directory):
    directory.mkdir()
    project = directory / "fixture project"
    project.mkdir()
    (project / "settings.txt").write_text(FIXTURE)
    default = None if case == "inherit" else args.default_model
    server = Server(args.codex, directory, default)
    try:
        initialization = server.request("initialize", {
            "clientInfo": {"name": "agent_kit_model_smoke", "version": "1.0"},
            "capabilities": {"experimentalApi": True},
        })
        server.send({"jsonrpc": "2.0", "method": "initialized"})
        config = server.request("config/read", {"includeLayers": False})["config"]
        actual_default = (config.get("agents") or {}).get("default_subagent_model")
        require(actual_default == default,
                "Inheritance test requires a profile without agents.default_subagent_model; no settings were changed")
        start = server.request("thread/start", {
            "ephemeral": True, "cwd": str(project), "model": args.parent_model,
            "config": {"model_reasoning_effort": "low"},
            "approvalPolicy": "never", "sandbox": "read-only",
        })
        parent = start["thread"]
        parent_model = start["model"]
        require(parent["ephemeral"] and parent["path"] is None, "Parent is not ephemeral")
        require(start["sandbox"]["type"] == "readOnly", "Parent is not read-only")
        require(parent_model != args.default_model, "Choose a default different from the parent")
        require(args.explicit_model not in (parent_model, args.default_model),
                "Choose an explicit model different from the parent and configured default")
        expected = {"inherit": parent_model, "configured": default, "explicit": args.explicit_model}[case]
        print(f"START {case}: parent={parent_model}, default={default}, expected={expected}", flush=True)
        selection = (f"The user explicitly requests {args.explicit_model} for this worker. Pass that "
                     "model on spawn and preserve it during continuation." if case == "explicit" else
                     "Do not pass a model override on spawn or continuation. Leave routing to the host.")
        prompt = f"""Run this user-authorized, bounded live subagent test. No edits, installation, commits, network or apps.
Read {INPUTS[0]} and {INPUTS[1]}. Use the runtime conventions and the full fact-finder role body.
Spawn exactly one fresh-context general-purpose child (fork_turns=none if supported), passing the full role body, runtime conventions and only this task input:
Scope is {project}. Q: What is the value of feature_enabled in settings.txt? Read the file and return the exact Q/FACT/EVIDENCE/CONFIDENCE/NOT_FOUND schema. Do not delegate.
Do not solve the child's question yourself. {selection}
Wait for completion. Continue the SAME child with: Q: What is the value of retry_limit in settings.txt? Read the file and return the same schema. Do not delegate.
Use a continuation operation that actually starts a turn and wait for completion. Do not change its model, replace or close it. End with the two replies. The harness inspects host records; do not claim which model ran."""
        turn = server.request("turn/start", {"threadId": parent["id"], "effort": "low",
                                             "input": [{"type": "text", "text": prompt}]})["turn"]
        deadline = time.monotonic() + args.timeout
        while True:
            event = server.receive(deadline)
            params = event.get("params", {})
            if (event.get("method") == "turn/completed" and params.get("threadId") == parent["id"]
                    and params["turn"]["id"] == turn["id"]):
                require(params["turn"]["status"] == "completed", "Parent turn did not complete")
                break
        starts = [item for item in completed_items(server.events, parent["id"])
                  if item["type"] == "subAgentActivity" and item["kind"] == "started"]
        require(len(starts) == 1, "Expected exactly one worker")
        # Ephemeral threads reject includeTurns; completed item events are the transcript.
        child = server.request("thread/read", {"threadId": starts[0]["agentThreadId"],
                                               "includeTurns": False})["thread"]
        result = verify(server.events, parent["id"], child, expected)
        require((project / "settings.txt").read_text() == FIXTURE, "Fixture changed")
        require(sorted(path.name for path in project.iterdir()) == ["settings.txt"], "Extra fixture files")
        result.update(case=case, runtime=initialization["userAgent"], parent_model=parent_model,
                      configured_default=default, explicit_override=args.explicit_model if case == "explicit" else None,
                      source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in INPUTS})
        (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"PASS {case}: {expected}, two completed turns, correct facts and citations", flush=True)
        return result
    finally:
        server.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex", help="installed Codex executable")
    parser.add_argument("--parent-model", help="omit to use the current Codex configuration")
    parser.add_argument("--default-model", required=True, help="supported worker default, different from parent")
    parser.add_argument("--explicit-model", required=True, help="third supported model for explicit override")
    parser.add_argument("--case", choices=("inherit", "configured", "explicit", "all"), default="all")
    parser.add_argument("--timeout", type=int, default=360, help="maximum seconds per model-driven case")
    args = parser.parse_args()
    require(args.timeout > 0, "Timeout must be positive")
    output = Path(tempfile.mkdtemp(prefix="agent-kit-codex-models-"))
    print(f"Evidence directory: {output}", flush=True)
    cases = ("inherit", "configured", "explicit") if args.case == "all" else (args.case,)
    for case in cases:
        run_case(args, case, output / case)


if __name__ == "__main__":
    main()
