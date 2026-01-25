# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of MultiModelGenerator seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to the project maintainers. You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: We will acknowledge your email within 48 hours
- **Communication**: We will keep you informed of the progress towards a fix
- **Disclosure**: We will coordinate the public disclosure date with you
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices for Users

### API Keys

- Never commit API keys to version control
- Use environment variables or `.env` files (which should be gitignored)
- Rotate API keys periodically
- Use separate API keys for development and production

### Knowledge Base Security

- Use password protection for sensitive knowledge bases
- Be cautious about what documents you upload to knowledge bases
- Regularly audit knowledge base contents

### Deployment

- Always use HTTPS in production
- Keep dependencies up to date
- Implement proper authentication if exposing the API publicly
- Use rate limiting to prevent abuse

## Security Updates

Security updates will be released as patch versions and announced in:
- GitHub Security Advisories
- Release notes
- Project README (for critical issues)

We recommend always running the latest version to ensure you have all security patches.
