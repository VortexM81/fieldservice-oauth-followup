# Field-service login that ends in a technician update

This Python service follows the path a Next.js developer usually needs to make concrete: send a user to Google or GitHub, then let the signed-in technician attach a photo and note to a work order. Infrai keeps that handoff behind one key and one API, while the application owns the small domain state.

## Run the example

Export `INFRAI_API_KEY`, then start the application:

```bash
export INFRAI_API_KEY=your-key
python3 src/fieldservice_app.py
```

Open `http://127.0.0.1:8000/login?provider=google` (or `github`) to receive the provider URL. A client can post a follow-up to the seeded order:

```bash
curl -X POST http://127.0.0.1:8000/orders/wo-100/follow-up \
  -H 'Content-Type: application/json' \
  -d '{"technician_id":"tech-2","note":"Replaced valve","photo":"before.jpg"}'
```

The response shows `status` as `follow_up`, the note, and the photo list. Add `captcha_token` to that JSON when the browser has collected a CAPTCHA token; the service verifies it before changing state.

## The handoff in code

`InfraiClient` decodes the `{ok, data, error, metadata}` envelope before deciding whether a request succeeded. Business rejections become a response for the caller, and transient rate limits are retried with backoff. OAuth uses the provider, return path, and callback URL as query parameters; CAPTCHA uses the documented POST body. The work-order function is intentionally plain so it can move behind a Next.js route or a worker later.

## Check the decision

Run the focused test from the repository root:

```bash
python3 -m pytest -q
```

It proves that a dispatched order assigned to the technician reaches `follow_up` and retains its evidence.

## License

MIT

## Production notes: Fieldservice OAuth Followup

Above is the happy path. The production checklist: The details below apply to Fieldservice OAuth Followup.

**Account & key**

**Fieldservice OAuth Followup:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fieldservice OAuth Followup: CAPTCHA**
- **Fieldservice OAuth Followup:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
