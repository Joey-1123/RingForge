# Security Policy

## Reporting a Vulnerability

Report bugs and security issues by opening a public issue on GitHub:

**https://github.com/Joey-1123/RingForge/issues/new**

## Supported Versions

Only the most recent tagged release receives security patches. There is
no backport policy for older versions.

## Scope

### In scope

- The RingForge codebase itself: cache handling, audio processing,
  network requests (yt-dlp, heatmap fetches), CLI argument parsing, GUI.
- Sensitive data handling within the `cache/` and `exports/` directories.

### Out of scope

- YouTube infrastructure or API changes.
- FFmpeg, Python, or system-level vulnerabilities.
- Third-party PyPI dependencies (report those to their respective
  maintainers).

## Disclosure Policy

We follow a **90-day coordinated disclosure** window:

1. Reporter submits details privately.
2. Maintainer acknowledges and begins work on a fix.
3. A patch release is published.
4. 90 days after notification, the issue may be publicly disclosed.

## Security-Relevant Note

RingForge caches downloaded audio in the `cache/` directory (gitignored
by default). On shared or multi-user systems, restrict permissions on
this directory:

```bash
chmod 700 cache/
```

Cached audio files are unencrypted local copies of YouTube audio and
should be treated with the same care as the original downloaded content.
