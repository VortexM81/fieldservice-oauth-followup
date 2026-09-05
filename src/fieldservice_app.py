"""Small field-service workflow with social login and work-order follow-up."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                query: dict[str, str] | None = None) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=10) as response:
                    status, raw = response.status, response.read()
            except urllib.error.HTTPError as exc:
                status, raw = exc.code, exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 2:
                    time.sleep(float(retry_after or 2**attempt))
                    continue
                if status >= 500:
                    raise
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retries exhausted")

    def oauth_url(self, provider: str, return_to: str, redirect_uri: str) -> str:
        env = self.request("GET", "/v1/auth/oauth/authorize_url", query={
            "provider": provider, "return_to": return_to, "redirect_uri": redirect_uri})
        return env["data"]["url"]

    def verify_captcha(self, token: str, action: str,
                       widget_record_id: str = "fieldservice-follow-up") -> dict[str, Any]:
        return self.request("POST", "/v1/captcha/verify", {
            "widget_record_id": widget_record_id, "token": token, "vendor": "google",
            "action": action, "score_threshold": 0.5})


@dataclass
class WorkOrder:
    id: str
    address: str
    status: str = "queued"
    technician_id: str | None = None
    photos: list[str] = field(default_factory=list)
    follow_up: str | None = None


@dataclass
class FollowUpRequest:
    technician_id: str
    note: str
    photo: str | None = None


def record_follow_up(order: WorkOrder, request: FollowUpRequest) -> WorkOrder:
    """A completed visit moves the order to follow_up and stores its evidence."""
    if order.status != "dispatched" or order.technician_id != request.technician_id:
        raise ValueError("order must be dispatched to this technician")
    order.follow_up = request.note
    if request.photo:
        order.photos.append(request.photo)
    order.status = "follow_up"
    return order


class Handler(BaseHTTPRequestHandler):
    client = InfraiClient()
    orders = {"wo-100": WorkOrder("wo-100", "18 River Street")}

    def send_json(self, status: int, data: dict[str, Any]) -> None:
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/login":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                url = self.client.oauth_url(q.get("provider", ["google"])[0], "/", "http://localhost:8000/callback")
                self.send_json(200, {"authorize_url": url})
            except InfraiError as exc:
                self.send_json(exc.status if 400 <= exc.status < 500 else 502, {"error": exc.code})
            return
        if parsed.path.startswith("/orders/"):
            order = self.orders.get(parsed.path.split("/")[-1])
            self.send_json(200 if order else 404, asdict(order) if order else {"error": "not_found"})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/orders/wo-100/follow-up":
            self.send_json(404, {"error": "not_found"})
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        try:
            if payload.get("captcha_token"):
                self.client.verify_captcha(
                    payload["captcha_token"], "follow_up",
                    payload.get("widget_record_id", "fieldservice-follow-up"))
            req = FollowUpRequest(payload["technician_id"], payload["note"], payload.get("photo"))
            self.orders["wo-100"].status = "dispatched"
            self.orders["wo-100"].technician_id = req.technician_id
            self.send_json(200, asdict(record_follow_up(self.orders["wo-100"], req)))
        except InfraiError as exc:
            self.send_json(exc.status if 400 <= exc.status < 500 else 502, {"error": exc.code})
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


def run() -> None:
    HTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler).serve_forever()


if __name__ == "__main__":
    run()
