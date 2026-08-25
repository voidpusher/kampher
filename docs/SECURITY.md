# Kampher security model

## Current data boundary

Kampher is a public research product. Its API exposes only public-source conversations,
derived opportunities, trends, polls, and aggregate corpus health. It does not currently
store accounts, sessions, emails, payment information, or private user records.

Saved searches remain in the browser under `kampher.saved-searches.v1`. They are not sent
to Kampher's database, cannot be read by another Kampher visitor, and disappear when the
browser storage is cleared. The client validates and bounds this data before using it.

Production secrets exist only in Render, GitHub Actions, Neon, Qdrant, and local ignored
environment files. No secret may use the `NEXT_PUBLIC_` prefix or enter a browser bundle.

## Enforced controls

- Production API documentation and schema endpoints are disabled.
- CORS is restricted to `https://kampher.vercel.app`; wildcard production CORS is rejected.
- Chat and search are rate-limited using the validated final proxy address.
- Request bodies are capped and chat responses are non-cacheable.
- Browser and API responses set CSP, HSTS, anti-framing, MIME-sniffing, referrer, and
  permissions policies.
- Retrieved conversations are treated as untrusted LLM data and JSON-encoded before
  synthesis. Model-generated links are not made clickable.
- React escapes displayed source content and raw HTML is not enabled in Markdown.

## Authentication gate

Do not add a login screen until Kampher introduces server-side user-owned data. When it
does, authentication and isolation must ship together:

1. Use a managed OIDC provider with secure, HTTP-only, same-site cookies.
2. Derive the user identity from the verified server session, never from a request body.
3. Add an immutable `owner_id` foreign key to every user-owned table.
4. Scope every read, update, and delete query by that verified owner.
5. Add cross-user isolation tests before deployment.
6. Provide account export and deletion before collecting personal information.

A cosmetic login without these controls is not considered authentication.
