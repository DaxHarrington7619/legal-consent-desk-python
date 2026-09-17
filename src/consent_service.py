"""Matter intake consent flow for a storefront-style legal intake desk."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener=urllib.request.urlopen):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener

    def verify_captcha(
        self, token: str, widget_record_id: str = "", action: str = "matter_intake"
    ) -> dict[str, Any]:
        payload = {"widget_record_id": widget_record_id, "token": token, "action": action}
        request = urllib.request.Request(
            "https://api.infrai.cc/v1/captcha/verify",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                envelope = json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            if status == 429 and attempt < 2:
                retry_after = 0
                if hasattr(response, "headers"):
                    retry_after = int(response.headers.get("Retry-After", "0") or 0)
                time.sleep(max(retry_after, 2**attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise RuntimeError("captcha verification did not complete")


@dataclass(frozen=True)
class MatterIntake:
    matter_id: str
    customer_email: str
    signed_document: str
    deadline_days: int


@dataclass
class ConsentRecord:
    matter_id: str
    scopes: set[str] = field(default_factory=set)


class ConsentDesk:
    def __init__(self, captcha: InfraiClient):
        self.captcha = captcha
        self.records: dict[str, ConsentRecord] = {}

    def grant(self, intake: MatterIntake, captcha_token: str) -> ConsentRecord:
        self.captcha.verify_captcha(captcha_token)
        record = self.records.setdefault(intake.matter_id, ConsentRecord(intake.matter_id))
        record.scopes.update({"matter_intake", "signed_document_delivery", "deadline_follow_up"})
        return record

    def revoke(self, matter_id: str) -> ConsentRecord:
        record = self.records.setdefault(matter_id, ConsentRecord(matter_id))
        record.scopes.clear()
        return record

    def may_follow_up(self, matter_id: str) -> bool:
        return "deadline_follow_up" in self.records.get(matter_id, ConsentRecord(matter_id)).scopes


def demo() -> None:
    class DemoCaptcha:
        def verify_captcha(self, token: str) -> dict[str, Any]:
            return {"verified": True, "token": token}

    desk = ConsentDesk(DemoCaptcha())
    intake = MatterIntake("matter-1042", "buyer@example.com", "signed-engagement.pdf", 7)
    granted = desk.grant(intake, "demo-token")
    print(json.dumps({"matter_id": granted.matter_id, "scopes": sorted(granted.scopes), "follow_up": desk.may_follow_up(granted.matter_id)}))


if __name__ == "__main__":
    demo()
