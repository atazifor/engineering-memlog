# Security policy

## Supported version

Security fixes are made against the latest 0.2.x release line and the default
branch. Upgrade to the latest patch before reporting an issue already fixed
there.

## Reporting a vulnerability

Use GitHub's private vulnerability report form:

https://github.com/atazifor/engineering-memlog/security/advisories/new

If that form is unavailable, open a minimal issue asking the maintainer for a
private contact channel. Do not include exploit details, credentials, private
memory entries, repository names, or other sensitive data in a public issue.

Include the affected version, backend type, operating system, reproduction steps
using sanitized data, impact, and any known mitigation. Please allow reasonable
time for investigation and a coordinated fix before public disclosure.

## Trust boundaries

The built-in JSONL backend and lexical ranker make no network calls. Claude Code
hooks insert selected entries into the active model context, so those entries are
processed according to the configured Claude environment's data-handling terms.
A custom provider is trusted executable code selected by the user and may have
its own filesystem and network access.

Memlog validates entry structure but does not scan for secrets. Never store
tokens, passwords, credentials, private keys, session cookies, connection
strings, or unsanitized customer data.
