# Security

## API keys

Put a model key only in the gitignored `.env`. `.env.example` ships with `LLM_API_KEY` empty. `GET /api/health` reports whether a key is set and does not return it.

If a key was committed, pasted into an issue, or left in a screenshot, revoke it at the provider and create a new one. Do not open a pull request whose only purpose is to delete a key that is already in git history; revoke it first, then remove it from the tree.

## Reporting a vulnerability

Use a [private security advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on this repository. Do not file a public issue for a vulnerability, and do not include a live key, a database file, or an uploaded document.

## What this edition already refuses

The link fetcher allows public `http` and `https` only, and it refuses loopback, private, link-local, and reserved addresses before a request is sent. Quiz answers and later chapter lessons stay on the server until the learner reaches them.
