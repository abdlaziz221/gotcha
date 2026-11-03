"""Mesure les limites de l'hébergeur et rédige le compte rendu (tâche A2).

Usage : python scripts/probe_platform.py https://<domaine> [--rapide] [--max 300]

Le site doit tourner avec GOTCHA_PROBE=1 (à retirer après les mesures). Le compte rendu,
en Markdown, est à reporter dans docs/DECISIONS.md et dans la fiche Datacloud (A10).
Durée : environ 10 minutes, dont 9 pour la durée maximale d'une requête (--rapide : 2).
Pour mesurer le démarrage à froid, lancer le script après 30 minutes sans visite.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

WAITS = (5, 15, 30, 60, 120, 300)
BACKGROUND_SECONDS = 20
# Adresse réservée à la documentation (RFC 5737) : sert à voir si le proxy la recopie.
FAKE_CLIENT_IP = "203.0.113.7"


@dataclass(frozen=True)
class Reply:
    code: int | None  # None : aucune réponse (délai dépassé, connexion coupée)
    seconds: float
    body: dict[str, Any]
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 200


def get(base: str, path: str, *, timeout: float, headers: dict[str, str] | None = None) -> Reply:
    request = urllib.request.Request(  # noqa: S310 (adresse http ou https vérifiée au départ)
        base + path, headers={"User-Agent": "gotcha-sonde/0.1", **(headers or {})}
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw, code = response.read(), response.status
    except urllib.error.HTTPError as exc:
        return Reply(exc.code, time.monotonic() - start, {}, f"HTTP {exc.code}")
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return Reply(None, time.monotonic() - start, {}, type(reason).__name__)
    try:
        body = json.loads(raw)
    except ValueError:
        body = {}
    return Reply(code, time.monotonic() - start, body if isinstance(body, dict) else {})


def step(message: str) -> None:
    print(f"… {message}", file=sys.stderr, flush=True)


def describe_failure(reply: Reply) -> str:
    return f"{reply.error or reply.code} après {reply.seconds:.0f} s"


def measure(base: str, *, max_wait: float) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    instances: set[str] = set()

    step("premier appel")
    first = get(base, "/healthz?db=1", timeout=120)
    info = get(base, "/_sonde/requete", timeout=30)
    if info.code == 404:
        sys.exit("La sonde est introuvable : démarrez le site avec GOTCHA_PROBE=1.")
    if not first.ok and first.code != 503:
        sys.exit(f"Le site ne répond pas : {describe_failure(first)}.")
    uptime = info.body.get("en_service_depuis_s", "?")
    rows.append(
        (
            "Premier appel (démarrage à froid si l'instance venait de démarrer)",
            f"{first.seconds:.1f} s ; instance en service depuis {uptime} s",
        )
    )
    rows.append(("`/healthz?db=1`", json.dumps(first.body, ensure_ascii=False)))

    step("en-têtes du proxy")
    proxy = get(base, "/_sonde/requete", timeout=30, headers={"X-Forwarded-For": FAKE_CLIENT_IP})
    instances.add(proxy.body.get("instance", "?"))
    forwarded = proxy.body.get("x_forwarded_for")
    if not forwarded:
        verdict = "absent : les quotas voient l'adresse du proxy, pas celle du client"
    elif forwarded.strip() == FAKE_CLIENT_IP:
        verdict = "transmis **tel quel** : le client choisit son adresse (A11)"
    elif FAKE_CLIENT_IP in forwarded:
        verdict = "le proxy **ajoute** l'adresse réelle : lire la dernière valeur (A11)"
    else:
        verdict = "le proxy **remplace** la valeur : fiable pour les quotas"
    rows.append(("Proxy : `X-Forwarded-For` reçu", f"`{forwarded}` : {verdict}"))
    rows.append(("Protocole vu par le site", f"`{proxy.body.get('protocole')}`"))
    rows.append(("En-têtes reçus", ", ".join(proxy.body.get("en_tetes", []))))

    step("base de données (3 connexions)")
    bases = [get(base, "/_sonde/base", timeout=30) for _ in range(3)]
    last = bases[-1].body
    if last.get("base") == "ok":
        delays = sorted(b.body.get("connexion_ms", 0) for b in bases)
        rows.append(
            (
                "Base : connexion neuve",
                f"ok, {delays[0]} à {delays[-1]} ms ; requête {last.get('requete_ms')} ms ;"
                f" SSL {'oui' if last.get('ssl') else 'non'} ; {last.get('version', '')[:40]}",
            )
        )
    else:
        rows.append(("Base : connexion neuve", str(last.get("base", describe_failure(bases[-1])))))

    step("sortie vers Internet")
    out = get(base, "/_sonde/sortie", timeout=60).body
    rows.append(
        (
            "Sortie vers Internet (flux Flutterwave)",
            f"{out.get('sortie')} ; HTTP {out.get('code', '-')} en {out.get('duree_ms')} ms",
        )
    )

    step(f"tâche de fond ({BACKGROUND_SECONDS} s après la réponse, sans visite entre-temps)")
    started = get(base, f"/_sonde/tache-de-fond?lancer={BACKGROUND_SECONDS}", timeout=30).body
    time.sleep(BACKGROUND_SECONDS + 10)
    later = get(base, "/_sonde/tache-de-fond", timeout=30).body
    instances.update({started.get("instance", "?"), later.get("instance", "?")})
    if later.get("instance") != started.get("instance"):
        verdict = "inconnu : la vérification est arrivée sur une autre instance"
    elif (later.get("tache") or {}).get("terminee_le"):
        verdict = "exécutée jusqu'au bout"
    else:
        verdict = "**pas terminée** : le processus est gelé ou coupé entre deux requêtes"
    rows.append(("Tâche de fond après la réponse", verdict))

    passed: float | None = None
    failure = ""
    for seconds in (s for s in WAITS if s <= max_wait):
        step(f"requête de {seconds} s")
        reply = get(base, f"/_sonde/attente?secondes={seconds}", timeout=seconds + 60)
        instances.add(reply.body.get("instance", "?"))
        if not reply.ok:
            failure = f" ; {seconds} s échoue ({describe_failure(reply)})"
            break
        passed = seconds
    tried = f"{passed} s aboutissent" if passed is not None else "aucune attente n'aboutit"
    rows.append(("Durée maximale d'une requête", tried + (failure or " (plus long non testé)")))
    rows.append(("Instances vues", str(len(instances - {"?"}))))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Mesure les limites de l'hébergeur (tâche A2).")
    parser.add_argument("url", help="adresse du site, ex. https://gotcha.example")
    parser.add_argument("--rapide", action="store_true", help="attentes jusqu'à 30 s seulement")
    parser.add_argument("--max", type=float, default=WAITS[-1], help="attente maximale (s)")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        sys.exit("L'adresse doit commencer par http:// ou https://.")

    rows = measure(base, max_wait=30 if args.rapide else args.max)
    day = datetime.now(UTC).date().isoformat()
    print(f"\n## Mesures de l'hébergeur, {day} ({base})\n")
    print("| Question | Mesure |\n| --- | --- |")
    for question, answer in rows:
        print(f"| {question} | {answer.replace('|', '/')} |")
    print("\nÀ reporter dans docs/DECISIONS.md et dans la fiche Datacloud ; puis GOTCHA_PROBE=0.")


if __name__ == "__main__":
    main()
