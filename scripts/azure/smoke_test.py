"""End-to-end smoke test of a deployed RentFlow environment.

    python scripts/azure/smoke_test.py --api-url https://... --web-url https://...

Proves the app runs against the provisioned Azure resources, not just Docker
Compose. Each check exercises a different piece of infrastructure:

  health/ready               PostgreSQL over private networking with an Entra token
  register + login + /me     JWT signed with the Key Vault secret-key
  property/unit/maintenance  M2-M5 API writes and reads
  document upload/download   Blob Storage through the api managed identity
  CORS preflight             BACKEND_CORS_ORIGINS wired to the web app URL
  web root                   the Next.js app is serving

It creates a throwaway landlord account ("smoke+<timestamp>@rentflow.test")
and a small amount of data. Only run it against staging.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class SmokeTestError(Exception):
    pass


def request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: Any = None,
    raw: bytes | None = None,
    headers: dict[str, str] | None = None,
    expect: tuple[int, ...] = (200,),
) -> tuple[int, dict[str, str], bytes]:
    all_headers = dict(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        all_headers["Content-Type"] = "application/json"
    if token:
        all_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=all_headers)

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args: Any, **kwargs: Any) -> None:
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=60) as response:
            status, resp_headers, payload = response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        status, resp_headers, payload = error.code, dict(error.headers), error.read()
    if status not in expect:
        raise SmokeTestError(f"{method} {url} -> HTTP {status}: {payload[:300]!r}")
    return status, resp_headers, payload


def as_json(payload: bytes) -> Any:
    return json.loads(payload.decode())


def multipart(
    fields: dict[str, str], filename: str, content: bytes, content_type: str
) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def run(api_url: str, web_url: str) -> None:
    api = api_url.rstrip("/") + "/api/v1"
    passed: list[str] = []

    def check(name: str) -> None:
        passed.append(name)
        print(f"  ok  {name}")

    # Scale-to-zero apps may need a cold start; give readiness a few tries.
    for attempt in range(12):
        try:
            request("GET", f"{api}/health/ready")
            break
        except SmokeTestError:
            if attempt == 11:
                raise
            time.sleep(10)
    request("GET", f"{api}/health/live")
    check("api live + ready (PostgreSQL reachable over the private network, Entra auth)")

    status, _, _ = request("GET", web_url, expect=(200, 301, 302, 307, 308))
    check(f"web app serving (HTTP {status})")

    email = f"smoke+{int(time.time())}@rentflow.test"
    password = secrets.token_urlsafe(18)
    request(
        "POST",
        f"{api}/auth/register",
        body={"email": email, "password": password, "full_name": "Smoke Test", "role": "landlord"},
        expect=(201,),
    )
    _, _, payload = request(
        "POST", f"{api}/auth/login", body={"email": email, "password": password}
    )
    token = as_json(payload)["access_token"]
    _, _, payload = request("GET", f"{api}/auth/me", token=token)
    assert as_json(payload)["email"] == email
    check("register + login + /auth/me (JWT signed with the Key Vault secret)")

    _, _, payload = request(
        "POST",
        f"{api}/properties",
        token=token,
        body={
            "name": "Smoke test property",
            "address_line1": "1 Deploy Street",
            "city": "Hamilton",
            "region": "ON",
            "postal_code": "L8S 4L8",
            "country": "Canada",
            "property_type": "single_family",
        },
        expect=(201,),
    )
    property_id = as_json(payload)["id"]
    _, _, payload = request(
        "POST",
        f"{api}/units",
        token=token,
        body={
            "property_id": property_id,
            "label": "Smoke 1",
            "bedrooms": "1",
            "bathrooms": "1",
            "market_rent": "1000.00",
            "status": "vacant",
        },
        expect=(201,),
    )
    unit_id = as_json(payload)["id"]
    _, _, payload = request(
        "POST",
        f"{api}/maintenance",
        token=token,
        body={
            "unit_id": unit_id,
            "title": "Smoke test request",
            "description": "Created by scripts/azure/smoke_test.py",
            "priority": "low",
        },
        expect=(201,),
    )
    request_id = as_json(payload)["id"]
    _, _, payload = request("GET", f"{api}/maintenance?unit_id={unit_id}", token=token)
    assert as_json(payload)["total"] == 1
    check("property -> unit -> maintenance request written and read back")

    body, content_type = multipart(
        {"owner_type": "maintenance_request", "owner_id": request_id},
        "smoke.pdf",
        PDF,
        "application/pdf",
    )
    _, _, payload = request(
        "POST",
        f"{api}/documents",
        token=token,
        raw=body,
        headers={"Content-Type": content_type},
        expect=(201,),
    )
    document_id = as_json(payload)["id"]
    _, _, downloaded = request("GET", f"{api}/documents/{document_id}/content", token=token)
    if downloaded != PDF:
        raise SmokeTestError("downloaded document does not match the upload")
    check("document upload + download (Blob Storage via managed identity)")

    _, headers, _ = request(
        "OPTIONS",
        f"{api}/properties",
        headers={
            "Origin": web_url.rstrip("/"),
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    allowed = {k.lower(): v for k, v in headers.items()}.get("access-control-allow-origin")
    if allowed != web_url.rstrip("/"):
        raise SmokeTestError(f"CORS allows {allowed!r}, expected {web_url!r}")
    check("CORS preflight allows the web app origin")

    print(f"\nAll {len(passed)} checks passed against {api_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--web-url", required=True)
    args = parser.parse_args()
    try:
        run(args.api_url, args.web_url)
    except (SmokeTestError, AssertionError, KeyError) as error:
        print(f"\nFAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
