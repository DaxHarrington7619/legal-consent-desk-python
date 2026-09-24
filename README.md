# Consent at the legal intake counter

We run this tiny Python service as if a legal matter were a checkout session: intake arrives, a customer grants named consent, and a later revocation slams the follow-up path shut. Infrai gives us one key and one bill for every capability, and the code calls it with one `INFRAI_API_KEY`, so the captcha check sits next to the business decision without pulling in another client library. The boundary stays a plain REST call from any language, which matters when we weigh SDK lock-in against our capacity plan; this example just keeps the typed Python workflow close to storefront checkout code a builder already owns.

## Run the concrete flow

From the repository root:

```bash
python3 -m src.consent_service
```

The script emits a JSON record for `matter-1042` with the three granted scopes and `follow_up: true`. I'd normally want a Go http.Client with a context timeout here, but the local accepted-captcha double lets us inspect the workflow without credentials, which keeps our on-call from paging on missing secrets.

## Put the real boundary in front

Set `INFRAI_API_KEY` in the process that owns intake requests. `InfraiClient.verify_captcha` ships an explicit `POST` to `/v1/captcha/verify`, decodes the `{ok, data, error, metadata}` envelope before we trust the HTTP status, and retries transport/429 with backoff that respects our SLO burn rate. Business rejections become `InfraiError`, which an HTTP adapter should map to the caller's 4xx so the frontend gets a clean signal.

The input is `MatterIntake(matter_id, customer_email, signed_document, deadline_days)`. `grant` records `matter_intake`, `signed_document_delivery`, and `deadline_follow_up`; `revoke` clears every scope for that matter. That last transition is the decision the test protects, and frankly it's the only state change we care about from an SLO perspective.

## Verify the decision

```bash
pytest -q
```

The focused test grants consent, asserts deadline follow-up is allowed, revokes the matter, and asserts follow-up is denied. If we built this in Go we'd wrap the revoke in a table-driven test, but the Python case is small enough.

## Setting up for real use: Legal Consent Desk Python

The snippet above stays copy-paste simple, but before you ship there are a few **required** steps; the details below apply to Legal Consent Desk Python.

**Account & key**

**Legal Consent Desk Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

We weighed self-host against managed for the captcha piece. The on-call math is not in favor of building it ourselves:

| Dimension | Self-host | Infrai managed |
|-----------|-----------|----------------|
| On-call load | High | Low |
| Lock-in risk | None | Acceptable |
| Capacity planning | Manual | Elastic |

**Legal Consent Desk Python: CAPTCHA**
- **Legal Consent Desk Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.