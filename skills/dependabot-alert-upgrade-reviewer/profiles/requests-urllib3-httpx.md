# requests / urllib3 / httpx profile

Use for HTTP client dependency updates, including common security alerts. Most relevant for urllib3 1.x -> 2.x or requests/httpx major bumps.

## Common risks

- TLS/certificate verification behavior changes
- proxy configuration semantics (HTTP vs HTTPS, NO_PROXY handling)
- retry policy changes (`Retry` parameter defaults)
- timeout defaults or exception types changed
- redirect behavior (`allow_redirects`, followed vs not)
- response streaming and body consumption / close semantics
- changed exception class hierarchy (`ConnectionError`, `Timeout`, `SSLError`)
- `Session` / `Client` reuse and connection pooling
- `mount()` adapter changes

## Searches

```bash
rg -n "requests\.|urllib3|httpx\." .
rg -n "requests\.get\(|requests\.post\(|requests\.put\(|requests\.delete\(|requests\.request\(" .
rg -n "httpx\.get\(|httpx\.post\(|httpx\.put\(|httpx\.delete\(|httpx\.request\(" .
rg -n "Session\(|with requests|with httpx" .
rg -n "verify=|cert=|proxies=|timeout=|stream=|allow_redirects" .
rg -n "Retry\(|HTTPAdapter|mount\(|PoolManager" .
rg -n "raise_for_status|ConnectionError|Timeout\b|SSLError|HTTPError" .
rg -n "MaxRetryError|NewConnectionError" .
```

## Smoke tests

- mock successful response with expected status/body
- mock timeout behavior (connect, read)
- mock 4xx/5xx behavior (raise_for_status, custom handlers)
- verify retry policy still applies (status_forcelist, backoff_factor)
- verify sessions/clients are properly closed (no resource leaks)
- verify TLS/proxy settings are preserved across versions
- verify redirect handling matches expectations

## Version awareness

This profile is most relevant for urllib3 1.x -> 2.x or requests major bumps where TLS, retry, and exception behavior changed. Patch bumps rarely need the full profile; correlate the search patterns to the exact version jump in the alert.
