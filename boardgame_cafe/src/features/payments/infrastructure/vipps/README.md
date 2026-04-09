Vipps integration notes
======================

Environment variables (example):

- `VIPPS_API_BASE` (default: `https://api.vipps.no`)
- `VIPPS_SUBSCRIPTION_KEY` (Ocp-Apim-Subscription-Key)
- `VIPPS_CLIENT_ID`
- `VIPPS_CLIENT_SECRET`
- `VIPPS_MERCHANT_SERIAL_NUMBER` (optional)
- `VIPPS_CALLBACK_PREFIX` (merchant callback base URL)
- `VIPPS_FALLBACK_URL` (optional fallback URL shown to users)
 - `VIPPS_CALLBACK_AUTH_TOKEN` (optional token that Vipps will send in `Authorization` header for callbacks; set this to validate callbacks)

Idempotency
-----------

Use the `X-Request-Id` header when calling capture/cancel endpoints. The adapter will forward this as `X-Request-Id` to Vipps so requests are idempotent.

This package exposes `VippsAdapter` which implements the payment provider
interface. In development, if credentials are not present the adapter will
simulate provider references so the app and tests can run without external
access.
