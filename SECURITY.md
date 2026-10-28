# Security

## Reporting

Report a vulnerability by opening a private security advisory on the repository, or by email to the maintainer listed on the GitHub profile. Please include the request that shows the problem. A first reply can be expected within a week.

## Measures in the code

- Responses carry a Content Security Policy that allows scripts only from the site and imagery only from NASA GIBS, HSTS over HTTPS, a frame ban and a permissions policy.
- Lookups and chat are rate limited per client; the client address is the entry added by the nearest trusted proxy (`TRUSTED_PROXY_HOPS`), so a forged `X-Forwarded-For` does not reset a limit.
- API keys are held as `SecretStr` and read from the environment or a local `.env`, which is git ignored. They are not logged or included in `repr`.
- Access logs carry method, path, status and time only. Query strings, which hold what people asked, are not logged, and the telemetry store keeps a hash and length of each question unless `LOG_QUESTIONS` is enabled.
- The container runs as an unprivileged user and writes only to `data/cache`.
- Dependencies are pinned in `requirements.lock`.
