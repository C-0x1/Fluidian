# Security policy

## Supported versions

Security fixes are released for the latest minor version of the 1.x line.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
**Report a vulnerability** button under the repository's *Security* tab so the
report stays private until a fix is available. Include:

- the version (`./fluidian version`) and how the engine was started;
- the smallest scene, request or app that reproduces the problem;
- what you expected to happen and what happened instead.

You will get an acknowledgement, an assessment of severity, and a note in the
changelog when the fix ships.

## What is in scope

The engine's HTTP surface, the session and token model, static file serving,
scene normalisation, HTML output escaping in the runtime, redaction, the
injection shield, and the wire protocol parsers in every SDK.

The threat model, the defaults and the hardening checklist for production are
described in [docs/security.md](docs/security.md).
