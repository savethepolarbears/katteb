# Security Policy

## Supported Versions

We release security patches and updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2.0 | :x:                |

---

## Reporting a Vulnerability

We take the security of our tools and user data seriously. If you discover a vulnerability in Katteb CLI or SDK, please report it privately through one of the channels below.

### 1. GitHub Private Vulnerability Reporting (Preferred)
Submit an advisory directly via GitHub:
- [Submit a private security advisory](https://github.com/savethepolarbears/katteb/security/advisories/new)

### 2. Email
If you are unable to use GitHub Security Advisories, send an encrypted report or plain text email to:
- **Email:** `security@blackbearmedia.io`
- **Subject:** `[Vulnerability Report] Katteb - <Brief Title>`

### What to Include
To help us triage and resolve the issue quickly, please provide:
1. Description of the vulnerability and attack vector.
2. Step-by-step reproduction steps or proof-of-concept (PoC).
3. Affected versions, operating systems, and environments.
4. Suggested remediation or patch if available.

### Response Timelines & SLA
- **Initial Acknowledgment:** Within 48 hours.
- **Triage & Assessment:** Within 5 business days.
- **Fix & Public Advisory:** Coordinated release with reporter attribution.

> [!CAUTION]
> **Please do NOT open public GitHub issues or discussions for sensitive security vulnerabilities.**

---

## Best Practices for API Key Management

1. **Never Commit Secrets:** Never commit `.env` files, production credentials, or `KATTEB_API_KEY` to git repositories.
2. **Restrict Configuration Permissions:** When using `katteb config set-key`, credentials are saved to `~/.katteb/config.json` with restricted `0600` filesystem permissions (owner read/write only).
3. **Automated Secret Rotation:** If a Katteb API key is suspected to be exposed, revoke and regenerate it immediately in the [Katteb Dashboard](https://app.katteb.com/api_access).
4. **Environment Isolation:** Use CI/CD secret managers (e.g. GitHub Actions Encrypted Secrets) rather than hardcoded environment strings.
