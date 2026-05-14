# Contributing to weather-alert-agent

Thanks for your interest in contributing.

weather-alert-agent is a self-hosted, privacy-focused weather intelligence tool built around the public National Weather Service API.

The goal is to keep the project:

- Lightweight
- Reliable
- Easy to self-host
- Easy to audit
- Minimal in dependencies
- Useful during real-world weather events

## Before Contributing

Please:

- Read the README first
- Search existing issues/discussions before opening new ones
- Keep pull requests focused and small when possible
- Test your changes locally before submitting

## Areas Especially Welcome

Contributions are especially useful for:

- Marine/coastal weather improvements
- Alert relevance filtering
- Notification integrations
- Setup/install improvements
- Documentation
- RSS/feed improvements
- Cross-platform automation
- Accessibility improvements
- Additional regional alert handling
- Better alert summarization

## Project Philosophy

This project intentionally avoids:

- Cloud lock-in
- User accounts
- Telemetry
- Heavy frameworks
- Excessive dependencies
- Unnecessary complexity

Please keep contributions aligned with those goals.

## Security

Do not commit:

- API tokens
- Webhook URLs
- Matrix access tokens
- Telegram bot tokens
- Real personal coordinates
- `.env` files
- `config.yaml`

If you discover a security issue, please use private security reporting instead of opening a public issue.

See:

- `SECURITY.md`

## Development Setup

Clone the repository:

```bash
git clone https://github.com/sidneyer/weather-alert-agent.git
cd weather-alert-agent
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run setup:

```bash
python3 setup.py
```

Test:

```bash
./weather_alert_agent.py --test
```

## Pull Requests

Good pull requests generally:

- Explain the problem being solved
- Keep changes focused
- Include testing notes
- Avoid unrelated refactors
- Preserve backward compatibility when practical

Large architectural changes should usually be discussed first in Discussions or Issues.

## Code Style

Preferred style:

- Readable over clever
- Small focused functions
- Minimal dependencies
- Clear configuration
- Straightforward debugging

## Discussions

Use GitHub Discussions for:

- Setup help
- Feature ideas
- Deployment examples
- Regional weather use cases
- Notification workflows
- Homelab/self-hosting discussion

## Disclaimer

This project is unofficial and is not affiliated with NOAA, the National Weather Service, or any government agency.
