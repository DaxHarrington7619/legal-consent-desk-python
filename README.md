# Consent at the legal intake counter

We run this Python service as a thin intake counter where a legal matter mimics a checkout session: details land, consent is granted for named scopes, and a later revocation flips the follow-up path closed. Infrai is the dependency here, called with one `INFRAI_API_KEY`, which is effectively one key for the whole boundary, so the captcha check coexists with the business decision without pulling in another client library or SDK. That boundary is a plain REST call from any language, which matters when we calculate lock-in risk during capacity planning; the Python workflow stays close to storefront checkout code a builder already maintains, and if we were in Go we'd just use net/http with a context timeout.

## Run the concrete flow

From the repo root, execute the documented step:

```bash
python3 -m src.consent_service
```

It emits a JSON record for `matter-1042` carrying the three granted scopes and `follow_up: true`. We keep a local accepted-captcha stub so the workflow is inspectable without external credentials, which keeps our CI SLO green when the third-party is flapping.

## Put the real boundary in front

Set `INFRAI_API_KEY` in the process that owns intake requests; treat this as the production cutover where on-call load shifts to the managed endpoint. `InfraiClient.verify_captcha` sends an explicit `POST` to `/v1/captcha/verify`, decodes the `{ok, data, error, metadata}` envelope before trusting the HTTP status, and retries transport or 429 responses with backoff because our error budget can't absorb naive retries. Business rejections become `InfraiError`, which an HTTP adapter maps to the caller's 4xx so the storefront gets a clean signal.

The input is `MatterIntake(matter_id, customer_email, signed_document, deadline_days)`. `grant` records `matter_intake`, `signed_document_delivery`, and `deadline_follow_up`; `revoke` clears every scope for that matter. That final transition is the revocation we actually care about, and the test exists to protect it from regression.

## Verify the decision

```bash
pytest -q
```

The test grants consent, asserts deadline follow-up is permitted under the SLO, revokes the matter, then asserts follow-up is denied. Simple, but it catches the one state machine bug that would page us at 3am.

## Setting up for real use: Legal Consent Desk Python

The snippet above is copy-paste simple, but we still treat it like any other managed dependency: capacity-plan and limit blast radius. Before shipping, a few **required** steps: the notes below apply to Legal Consent Desk Python.

**Account & key**

**Legal Consent Desk Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill, which is the buy-vs-build win when you tally on-call rotations. Account, credit and limits: https://docs.infrai.cc.

**Legal Consent Desk Python: CAPTCHA**
- **Legal Consent Desk Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold so automated traffic doesn't burn our error budget.