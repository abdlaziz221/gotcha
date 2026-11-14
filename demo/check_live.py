"""Vérifie, juste avant la démo, que le site en ligne répond comme le scénario l'attend.

Usage : python demo/check_live.py [https://<domaine>]
Sans dépendance. Chaque ligne dit OK ou ÉCHEC ; en cas d'échec, basculer sur la vidéo
de secours (docs/DEMO.md, « Si quelque chose casse en direct »).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_SITE = "https://gotcha-80c95631.platform-systalink.com"


def fetch(url: str, data: bytes | None = None) -> tuple[int, dict[str, str], str]:
    headers = {"User-Agent": "gotcha-demo-check"}
    if data is not None:
        headers |= {"Content-Type": "application/json", "Accept": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return response.status, dict(response.headers), response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode(errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        return 0, {}, str(exc)


def main(site: str) -> int:
    site = site.rstrip("/")
    checks: list[tuple[str, bool]] = []

    code, _, body = fetch(f"{site}/healthz?db=1")
    checks.append(("Site en ligne et base jointe", code == 200 and '"database":"ok"' in body))

    code, _, body = fetch(f"{site}/fiches/wave-sn")
    checks.append(("Fiche Wave ouverte sans compte", code == 200))
    checks.append(("Piège « Aucun bac à sable public » publié", "Aucun bac à sable public" in body))

    code, _, body = fetch(f"{site}/fiches/wave-sn?mode=pas-a-pas&etape=1")
    checks.append(("Mode pas à pas (fin de la démo, sur mobile)", code == 200))

    code, _, _ = fetch(f"{site}/fiches/mpesa-ke")
    checks.append(("Fiche M-Pesa, piège de rechange", code == 200))

    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    code, headers, _ = fetch(f"{site}/mcp", json.dumps(init).encode())
    auth = {k.lower(): v for k, v in headers.items()}.get("www-authenticate", "")
    checks.append(("Serveur MCP prêt, connexion GitHub demandée", code == 401 and "Bearer" in auth))

    for label, ok in checks:
        sys.stdout.write(f"{'OK    ' if ok else 'ÉCHEC '} {label}\n")
    failed = sum(not ok for _, ok in checks)
    sys.stdout.write(
        "Prêt pour la démo.\n" if not failed else f"{failed} échec(s) : vidéo de secours.\n"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE))
