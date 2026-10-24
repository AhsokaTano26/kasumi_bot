"""Kuma 上报必须反映 Webhook 与 QQ 身份接口的实际状态。"""

from __future__ import annotations

import asyncio
import importlib
import json
import unittest
from typing import Any
from unittest.mock import patch

import httpx
import nonebot
from nonebot.adapters.qq import Adapter
from nonebot.drivers import Driver, Request, Response


class KumaHealthTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        nonebot.init(
            driver="~fastapi+~httpx",
            host="0.0.0.0",
            port=8080,
            log_level="WARNING",
            kuma_push_url="",
            qq_bots=[
                {
                    "id": "test-app",
                    "token": "test-token",
                    "secret": "test-secret",
                    "use_websocket": False,
                }
            ],
        )
        cls.driver = nonebot.get_driver()
        adapters = patch.dict(Driver._adapters, {}, clear=True)
        adapters.start()
        cls.addClassCleanup(adapters.stop)
        cls.driver.register_adapter(Adapter)
        cls.adapter = nonebot.get_adapter(Adapter)
        asyncio.run(cls.adapter.startup())
        plugin = nonebot.load_plugin("src.plugins.kuma_health")
        if plugin is None:
            message = "kuma_health plugin failed to load"
            raise AssertionError(message)
        cls.entry = plugin.module
        cls.health = importlib.import_module("src.plugins.kuma_health.health")

    async def asyncSetUp(self) -> None:
        self.reporter = self.health.HealthReporter(
            self.driver,
            "https://kuma.example/api/push/test-token"
            "?status=up&msg=OK&ping=999&custom=keep",
        )
        self.pushes: list[httpx.Request] = []
        self.qq_requests: list[Request] = []
        self.identity: dict[str, Any] = {
            "id": "test-bot",
            "username": "Kasumi",
            "bot": True,
        }
        self.identity_status = 200
        self.webhook_status: int | None = None
        self.push_error: Exception | None = None
        self.push_event = asyncio.Event()
        self.asgi = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=nonebot.get_asgi())
        )
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.route))
        self.addAsyncCleanup(self.asgi.aclose)
        self.addAsyncCleanup(self.client.aclose)
        self.addAsyncCleanup(self.entry.stop)
        requests = patch.object(self.adapter, "request", self.qq_request)
        requests.start()
        self.addCleanup(requests.stop)

    async def route(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "kuma.example":
            self.pushes.append(request)
            self.push_event.set()
            if self.push_error:
                raise self.push_error
            return httpx.Response(200, json={"ok": True})
        self.assertEqual(request.url.host, "127.0.0.1")
        self.assertEqual(request.url.port, 8080)
        self.assertEqual(request.url.path, "/qq/webhook")
        if self.webhook_status is not None:
            return httpx.Response(self.webhook_status, json={})
        return await self.asgi.send(request)

    async def qq_request(self, request: Request) -> Response:
        self.qq_requests.append(request)
        if request.url.path.endswith("getAppAccessToken"):
            return Response(
                200,
                content=json.dumps({"access_token": "test-access", "expires_in": 7200}),
            )
        self.assertEqual(request.url.path, "/users/@me")
        self.assertEqual(request.headers["Authorization"], "QQBot test-access")
        return Response(self.identity_status, content=json.dumps(self.identity))

    async def test_healthy_webhook_without_events_reports_up(self) -> None:
        self.assertEqual(nonebot.get_bots(), {})
        await self.reporter.report_once(self.client)
        self.assertEqual(len(self.pushes), 1)
        params = self.pushes[0].url.params
        self.assertEqual(params.get_list("status"), ["up"])
        self.assertEqual(params["custom"], "keep")
        self.assertNotEqual(params["ping"], "999")
        self.assertTrue(any(req.url.path == "/users/@me" for req in self.qq_requests))
        self.assertEqual(nonebot.get_bots(), {})

    async def test_each_cycle_rechecks_identity_and_reuses_token(self) -> None:
        await self.reporter.report_once(self.client)
        await self.reporter.report_once(self.client)
        self.identity_status = 500
        self.identity = {"code": 500, "message": "identity unavailable"}
        await self.reporter.report_once(self.client)
        self.assertEqual(
            [req.url.params["status"] for req in self.pushes], ["up", "up", "down"]
        )
        paths = [req.url.path for req in self.qq_requests]
        self.assertEqual(paths.count("/users/@me"), 3)
        self.assertEqual(sum(path.endswith("getAppAccessToken") for path in paths), 1)

    async def test_missing_or_malformed_identity_reports_down(self) -> None:
        for identity in ({"id": ""}, {"unexpected": "response"}):
            with self.subTest(identity=identity):
                self.identity = identity
                await self.reporter.report_once(self.client)
                self.assertEqual(
                    self.pushes[-1].url.params.get_list("status"), ["down"]
                )

    async def test_webhook_failure_reports_down(self) -> None:
        for status in (404, 500, 200):
            with self.subTest(status=status):
                self.webhook_status = status
                await self.reporter.report_once(self.client)
                self.assertEqual(self.pushes[-1].url.params["status"], "down")
        self.assertEqual(self.qq_requests, [])

    async def test_webhook_connection_failure_reports_down(self) -> None:
        async def unavailable(request: httpx.Request) -> httpx.Response:
            if request.url.host != "kuma.example":
                message = "not listening"
                raise httpx.ConnectError(message, request=request)
            return await self.route(request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(unavailable)
        ) as client:
            await self.reporter.report_once(client)
        self.assertEqual(self.pushes[-1].url.params["status"], "down")

    async def test_missing_accounts_report_down(self) -> None:
        with patch.object(self.adapter.qq_config, "qq_bots", []):
            await self.reporter.report_once(self.client)
        self.assertEqual(self.pushes[-1].url.params["status"], "down")

    async def test_one_failing_account_makes_all_accounts_down(self) -> None:
        second = self.adapter.qq_config.qq_bots[0].model_copy(
            update={"id": "other-app"}
        )
        original = self.qq_request

        async def request(setup: Request) -> Response:
            if setup.headers.get("X-Union-Appid") == "other-app":
                return Response(401, content='{"code":11244,"message":"invalid"}')
            return await original(setup)

        with (
            patch.object(
                self.adapter.qq_config,
                "qq_bots",
                [*self.adapter.qq_config.qq_bots, second],
            ),
            patch.object(self.adapter, "request", request),
        ):
            await self.reporter.report_once(self.client)
        self.assertEqual(self.pushes[-1].url.params["status"], "down")

    async def test_identity_timeout_reports_down(self) -> None:
        async def stalled(_request: Request) -> Response:
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

        with (
            patch.object(self.adapter, "request", stalled),
            patch.object(self.health, "REQUEST_TIMEOUT", 0.01),
        ):
            await self.reporter.report_once(self.client)
        self.assertEqual(self.pushes[-1].url.params["status"], "down")

    async def test_failed_account_leaves_no_identity_requests_running(self) -> None:
        second = self.adapter.qq_config.qq_bots[0].model_copy(
            update={"id": "other-app"}
        )
        cancelled = asyncio.Event()

        async def request(setup: Request) -> Response:
            if setup.headers.get("X-Union-Appid") == "test-app":
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
            if setup.headers.get("X-Union-Appid") == "other-app":
                return Response(500, content='{"code":500,"message":"failed"}')
            return await self.qq_request(setup)

        with (
            patch.object(
                self.adapter.qq_config,
                "qq_bots",
                [*self.adapter.qq_config.qq_bots, second],
            ),
            patch.object(self.adapter, "request", request),
            patch.object(self.health, "REQUEST_TIMEOUT", 0.01),
        ):
            await self.reporter.report_once(self.client)
            self.assertTrue(cancelled.is_set())
        self.assertEqual(self.pushes[-1].url.params["status"], "down")

    async def test_push_failure_allows_next_report(self) -> None:
        self.push_error = httpx.ConnectError("contains private push URL")
        await self.reporter.report_once(self.client)
        self.push_error = None
        await self.reporter.report_once(self.client)
        self.assertEqual(
            [req.url.params["status"] for req in self.pushes], ["up", "up"]
        )

    async def test_push_url_is_hidden_from_httpx_info_logs(self) -> None:
        with self.assertLogs("httpx", level="INFO") as captured:
            await self.reporter.report_once(self.client)
        logs = "\n".join(captured.output)
        self.assertNotIn("/api/push/", logs)
        # 非敏感的 HTTPX 请求日志仍然可见。
        self.assertIn("127.0.0.1", logs)

    async def test_empty_configuration_does_not_start_task(self) -> None:
        for value in ("", "   "):
            with (
                self.subTest(value=value),
                patch.object(self.entry.config, "kuma_push_url", value),
            ):
                await self.entry.start()
                self.assertIsNone(self.entry._task)

    async def test_background_task_waits_60_seconds_and_stops_cleanly(self) -> None:
        delays: list[float] = []
        first_tick = asyncio.Event()
        real_sleep = asyncio.sleep

        async def sleep(delay: float) -> None:
            delays.append(delay)
            if len(delays) == 1:
                await first_tick.wait()
            else:
                await asyncio.Event().wait()

        with (
            patch.object(self.entry.config, "kuma_push_url", self.reporter.push_url),
            patch.object(self.health.httpx, "AsyncClient", return_value=self.client),
            patch.object(self.health.asyncio, "sleep", sleep),
        ):
            await self.entry.start()
            task = self.entry._task
            await self.entry.start()
            self.assertIs(self.entry._task, task)
            await real_sleep(0)
            self.assertEqual(delays, [60])
            self.assertEqual(self.pushes, [])
            first_tick.set()
            await asyncio.wait_for(self.push_event.wait(), timeout=2)
            await real_sleep(0)
            self.assertGreater(delays[-1], 59)
            self.assertLessEqual(delays[-1], 60)
            await self.entry.stop()
        self.assertTrue(task.done())
        self.assertIsNone(self.entry._task)
        self.assertTrue(self.client.is_closed)


if __name__ == "__main__":
    unittest.main()
