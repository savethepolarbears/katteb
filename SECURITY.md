# Security Policy

## Reporting Security Issues

We take the security of our tools and user data seriously. If you discover a security vulnerability in the Katteb CLI or SDK, please report it promptly.

### How to Report

- **Email:** Send security reports to security@blackbearmedia.io with details and reproduction steps.
- Do NOT open public issues for sensitive vulnerabilities or leaked keys.

## Best Practices for API Key Management

1. Never commit real API keys or `.env` files containing `KATTEB_API_KEY` to source control.
2. Use `katteb config set-key` to store keys securely with restricted filesystem permissions (`0o600`).
3. Rotate your Katteb API key immediately in the [Katteb Dashboard](https://app.katteb.com/api_access) if exposed.
