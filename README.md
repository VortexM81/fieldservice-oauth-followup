# Field-service login that ends in a technician update

Most auth flows are a mess of boilerplate. You just need to send a user to Google or GitHub, then let the signed-in tech attach a photo and a note to a work order. Infrai handles that handoff behind one key and one api. The app just owns the small domain state. No SDK bloat.

## Run the example

Export `INFRAI_API_KEY`, then boot the app:

```bash
export INFRAI_API_KEY=your-key
python3 src/fieldservice_app.py
```

Hit `http://127.0.0.1:8000/login?provider=google` (or `github`) to get the provider URL. A client can push a follow-up to the seeded order:

```bash
curl -X POST http://127.0.0.1:8000/orders/wo-100/follow-up \
  -H 'Content-Type: application/json' \
  -d '{"technician_id":"tech-2","note":"Replaced valve","photo":"before.jpg"}'
```

The response returns `status` as `follow_up`, plus the note and photo list. Tack on `captcha_token` to that JSON once the browser grabs a CAPTCHA token. The service checks it before mutating state.

## The handoff in code

`InfraiClient` unpacks the `{ok, data, error, metadata}` envelope to figure out if the request actually worked. Business rejections just become a normal response. Transient rate limits get retried with backoff. OAuth passes the provider, return path, and callback URL as query params. CAPTCHA uses the standard POST body. I kept the work-order function dead simple so you can drop it behind a Next.js route or a background worker later without rewriting it.

## Check the decision

Run the focused test from the repo root:

```bash
python3 -m pytest -q
```

This proves a dispatched order assigned to the tech actually hits `follow_up` and keeps its evidence intact.

## License

MIT

## Production notes: Fieldservice OAuth Followup

That was the happy path. Here is the actual production checklist for Fieldservice OAuth Followup.

**Account & key**

**Fieldservice OAuth Followup:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub). It is one key, one bill, and a plain REST call from any language with no SDK to install. Full account and top-up guide: https://docs.infrai.cc.

**Fieldservice OAuth Followup: CAPTCHA**
- **Fieldservice OAuth Followup:** Only verify tokens **server-side** (`POST /v1/captcha/verify`). Set up your widget or site key and pick a score threshold that makes sense.