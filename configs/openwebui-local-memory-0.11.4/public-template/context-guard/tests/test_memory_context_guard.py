"""Synthetic route and short-circuit tests; no Open WebUI app, DB, or network."""

from __future__ import annotations

import asyncio
import importlib.util
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "memory_context_guard.py"
spec = importlib.util.spec_from_file_location("memory_context_guard", MODULE)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(guard)


MODEL_ID = guard.ALLOWED_MODEL_ID
LOOPBACK_URLS = [{"url": "http://127.0.0.1:11434"}]


class FakeState:
    def __init__(self):
        self.MODELS = {MODEL_ID: {"id": MODEL_ID}}
        self.OLLAMA_MODELS = {MODEL_ID: {"urls": [0]}}
        self.OPENAI_MODELS = {}


def request(state=None):
    return types.SimpleNamespace(app=types.SimpleNamespace(state=state or FakeState()))


def model(model_id=MODEL_ID, caps=None):
    meta = {"capabilities": caps or {"memory": True}}
    return {"id": model_id, "info": {"meta": meta}}


class RouteGuardTests(unittest.TestCase):
    def test_exact_local_qwen_route_is_allowed(self):
        self.assertTrue(guard.is_allowed_memory_context_route(request(), model(), LOOPBACK_URLS))
        self.assertTrue(
            guard.is_allowed_memory_context_route(
                request(), model(), [{"url": "http://localhost:11434"}]
            )
        )

    def test_unknown_or_new_model_is_denied_even_if_memory_capability_missing(self):
        state = FakeState()
        new_id = "new-provider/model-added-later"
        state.MODELS[new_id] = {"id": new_id}
        state.OPENAI_MODELS[new_id] = {"id": new_id}
        self.assertFalse(
            guard.is_allowed_memory_context_route(request(state), model(new_id, {}), LOOPBACK_URLS)
        )

    def test_denies_missing_or_conflicting_server_route_state(self):
        cases = []
        cases.append((types.SimpleNamespace(), LOOPBACK_URLS))
        state = FakeState()
        state.OPENAI_MODELS[MODEL_ID] = {"id": MODEL_ID}
        cases.append((state, LOOPBACK_URLS))
        state = FakeState()
        state.OLLAMA_MODELS = {}
        cases.append((state, LOOPBACK_URLS))
        state = FakeState()
        state.MODELS = {}
        cases.append((state, LOOPBACK_URLS))
        for state, urls in cases:
            with self.subTest(state=state):
                self.assertFalse(guard.is_allowed_memory_context_route(request(state), model(), urls))

    def test_denies_non_loopback_malformed_and_invalid_index(self):
        cases = [
            ([{"url": "https://external.example"}], [0]),
            ([{"url": "http://10.20.30.40:11434"}], [0]),
            ([{"url": "http://user@127.0.0.1:11434"}], [0]),
            ([{"url": "http://127.0.0.1:11434/path"}], [0]),
            ([{"url": "http://127.0.0.1:99999"}], [0]),
            ([{"url": "http://127.0.0.1:11434"}], [1]),
            ([{"url": "http://127.0.0.1:11434"}], [True]),
            (None, [0]),
        ]
        for urls, indices in cases:
            with self.subTest(urls=urls, indices=indices):
                state = FakeState()
                state.OLLAMA_MODELS[MODEL_ID] = {"urls": indices}
                self.assertFalse(guard.is_allowed_memory_context_route(request(state), model(), urls))

class NoReadBeforeGuardTests(unittest.TestCase):
    def test_external_and_unset_new_models_short_circuit_before_memory_read(self):
        class FakeMemoryDB:
            def __init__(self):
                self.reads = 0

            async def search(self):
                self.reads += 1
                return ["SYNTHETIC_MEMORY_CANARY"]

        async def synthetic_add_memory_context(req, payload, active_model, base_urls, db):
            # Mirrors the proposed 0.11.4 patch lines placed at function entry.
            if (
                not isinstance(active_model, dict)
                or active_model.get("id") != MODEL_ID
                or not guard.is_allowed_memory_context_route(req, active_model, base_urls)
            ):
                return payload
            if not (
                active_model.get("info", {}).get("meta", {}).get("capabilities") or {}
            ).get("memory", True):
                return payload
            rows = await db.search()
            payload["messages"].append({"role": "system", "content": repr(rows)})
            return payload

        async def run_case(model_id, caps):
            db = FakeMemoryDB()
            payload = {"messages": [{"role": "user", "content": "Synthetic prompt"}]}
            state = FakeState()
            if model_id != MODEL_ID:
                state.MODELS[model_id] = {"id": model_id}
                state.OPENAI_MODELS[model_id] = {"id": model_id}
            result = await synthetic_add_memory_context(
                request(state), payload, model(model_id, caps), LOOPBACK_URLS, db
            )
            return result, db.reads

        for external_id in ("external/provider-model", "external/new-model-added-later"):
            with self.subTest(external_id=external_id):
                result, reads = asyncio.run(run_case(external_id, {}))
                self.assertEqual(reads, 0)
                self.assertNotIn("SYNTHETIC_MEMORY_CANARY", repr(result))

    def test_verified_qwen_preserves_existing_context_read_flow(self):
        result, reads = asyncio.run(
            self._verified_qwen_case()
        )
        self.assertEqual(reads, 1)
        self.assertIn("SYNTHETIC_MEMORY_CANARY", repr(result))

    async def _verified_qwen_case(self):
        class FakeMemoryDB:
            reads = 0

            async def search(self):
                self.reads += 1
                return ["SYNTHETIC_MEMORY_CANARY"]

        async def synthetic_add_memory_context(req, payload, active_model, base_urls, db):
            if (
                not isinstance(active_model, dict)
                or active_model.get("id") != MODEL_ID
                or not guard.is_allowed_memory_context_route(req, active_model, base_urls)
            ):
                return payload
            if not (
                active_model.get("info", {}).get("meta", {}).get("capabilities") or {}
            ).get("memory", True):
                return payload
            rows = await db.search()
            payload["messages"].append({"role": "system", "content": repr(rows)})
            return payload

        db = FakeMemoryDB()
        payload = {"messages": [{"role": "user", "content": "Synthetic prompt"}]}
        result = await synthetic_add_memory_context(request(), payload, model(), LOOPBACK_URLS, db)
        return result, db.reads

    def test_existing_qwen_capability_false_remains_respected(self):
        async def check():
            class FakeMemoryDB:
                reads = 0

                async def search(self):
                    self.reads += 1
                    return ["SYNTHETIC_MEMORY_CANARY"]

            db = FakeMemoryDB()
            payload = {"messages": [{"role": "user", "content": "Synthetic prompt"}]}
            active_model = model(caps={"memory": False})
            if not guard.is_allowed_memory_context_route(request(), active_model, LOOPBACK_URLS):
                return payload, db.reads
            if not active_model["info"]["meta"]["capabilities"].get("memory", True):
                return payload, db.reads
            await db.search()
            return payload, db.reads

        result, reads = asyncio.run(check())
        self.assertEqual(reads, 0)
        self.assertNotIn("SYNTHETIC_MEMORY_CANARY", repr(result))


if __name__ == "__main__":
    unittest.main()
