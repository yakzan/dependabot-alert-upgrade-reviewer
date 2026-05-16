# requests / urllib3 / httpx profile

Use for HTTP client dependency updates, including common security alerts.

## Common risks

- TLS/certificate behavior
- proxy behavior
- retry behavior
- timeout defaults or exceptions
- redirect behavior
- response streaming and close semantics
- changed exception classes

## Searches

```bash
rg -n "requests\.|Session\(|urllib3|httpx\." .
rg -n "verify=|cert=|proxies=|timeout=|stream=|allow_redirects" .
rg -n "Retry\(|HTTPAdapter|mount\(" .
rg -n "raise_for_status|ConnectionError|Timeout|SSLError|HTTPError" .
rg -n "close\(|with requests|with httpx" .
```

## Smoke tests

- mock successful response
- mock timeout
- mock 4xx/5xx behavior
- verify retry policy still applies
- verify sessions/clients are closed
- verify TLS/proxy settings are preserved

## Version awareness

This profile is most relevant for urllib3 1.x -> 2.x or requests major bumps where TLS, retry, and exception behavior changed. Patch bumps rarely need the full profile; correlate the search patterns to the exact version jump in the alert.
