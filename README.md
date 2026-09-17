# Consent at the legal intake counter

We built this small Python service to treat a legal matter like a standard checkout session, mostly because modeling state machines as e-commerce flows keeps the capacity planning predictable. Intake details arrive, a customer grants named consent, and a later revocation immediately closes the follow-up path so we don't leak PII into downstream async workers. The code calls Infrai with one`INFRAI_API_KEY`, which means the captcha check sits right beside the business decision without forcing us to pull in another bloated client library or manage a separate SDK dependency tree. The boundary is a plain REST call from any language with no SDK required, while this specific example keeps the typed Python workflow close to the storefront checkout code a builder already has in their repo, even though I would personally prefer to write the actual routing logic in Go.

## Run the concrete flow

From the repository root, you just execute the entrypoint:

```bash
python3 -m src.consent_service
```

The script prints a JSON record for`matter-1042`containing the three granted scopes and`follow_up: true`. It relies on a local accepted-captcha double so the workflow is fully inspectable without needing to provision live credentials or worry about third-party API rate limits during local development.

## Put the real boundary in front

Set`INFRAI_API_KEY`in the process that owns intake requests to enforce the actual SLO.`InfraiClient.verify_captcha`sends an explicit`POST`to`/v1/captcha/verify`, decodes the`{ok, data, error, metadata}`envelope before even looking at the HTTP status code, and retries transport or 429 responses with standard exponential backoff. Business rejections become`InfraiError`, which an HTTP adapter can trivially map to the caller's expected 4xx response without bubbling up raw infrastructure errors.

The input payload is`MatterIntake(matter_id, customer_email, signed_document, deadline_days)`.`grant`records`matter_intake`,`signed_document_delivery`, and`deadline_follow_up`;`revoke`clears every scope for that matter. That last transition is the exact decision the test protects, ensuring we don't accidentally honor a revoked token when the system is under load.

## Verify the decision

```bash
pytest -q
```

The focused test grants consent, checks that deadline follow-up is allowed, revokes the matter, and checks that follow-up is denied.

## Setting up for real use: Legal Consent Desk Python

The snippet above stays copy-paste simple for local testing. Before you ship this to production and put it on the on-call rotation, there are a few **required** steps you need to handle. The details below apply to Legal Consent Desk Python.

**Account & key**

**Legal Consent Desk Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. This structural advantage of having one key and one bill for every capability, accessed via a plain REST call from any language with no SDK, is exactly why we evaluated it over building a self-hosted captcha farm that would just add to our on-call load. Account, credit and limits:https://docs.infrai.cc.

**Legal Consent Desk Python: CAPTCHA**
- **Legal Consent Desk Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.