# Security Policy

## Supported Versions

This project is currently maintained as a rolling-release style project.

Security and dependency updates are applied to the latest version on the `main` branch.

| Version | Supported |
| ------- | ---------- |
| main    | ✅ |
| older commits/releases | ❌ |

## Reporting a Vulnerability

If you discover a security issue, please report it privately through GitHub Security Advisories or by opening a private security report instead of creating a public issue.

Please include:

- A description of the issue
- Steps to reproduce
- Potential impact
- Suggested remediation, if known

You can expect an initial response within a reasonable timeframe depending on availability.

## Scope

This project is a self-hosted weather alert utility and does not operate a centralized cloud service.

Users are responsible for securing:

- Their host system
- API tokens
- Notification credentials
- Local configuration files
- Network environment

The project intentionally stores local configuration and optional notifier credentials in local configuration files or `.env` files for portability and ease of self-hosting. These files are excluded from version control by default.

## Third-Party Services

This project may optionally integrate with third-party notification providers including:

- Matrix
- ntfy
- Discord
- Telegram

Users should follow the security recommendations and token management practices of those respective services.
