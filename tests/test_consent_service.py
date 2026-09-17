import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from consent_service import ConsentDesk, MatterIntake


class CaptchaAccepted:
    def verify_captcha(self, token):
        return {"verified": True}


def test_revoke_removes_deadline_follow_up_consent():
    desk = ConsentDesk(CaptchaAccepted())
    intake = MatterIntake("matter-7", "shopper@example.com", "engagement.pdf", 3)
    desk.grant(intake, "captcha-token")
    assert desk.may_follow_up("matter-7") is True
    desk.revoke("matter-7")
    assert desk.may_follow_up("matter-7") is False
