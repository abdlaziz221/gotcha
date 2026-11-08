"""Mesure les limites de l'hébergeur et rédige le compte rendu (tâche A2).

Usage : GOTCHA_PROBE_TOKEN=<jeton> python scripts/probe_platform.py https://<domaine>
        [--rapide] [--max 300]

Le site doit tourner avec GOTCHA_PROBE=1 et le même GOTCHA_PROBE_TOKEN (à retirer après
les mesures). Une requête qui échoue donne « mesure impossible », jamais un faux résultat.
Le compte rendu, en Markdown, va dans docs/DECISIONS.md et dans la fiche Datacloud (A10).
Durée : environ 10 minutes, dont 9 pour la durée maximale d'une requête (--rapide : 2).
Pour mesurer le démarrage à froid, lancer le script après 30 minutes sans visite.
"""

from __future__ import annotations

import argparse
import json
import os
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
# Retard toléré pour la tâche de fond avant de conclure à un processus gelé.
BACKGROUND_SLACK_SECONDS = 5


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


def impossible(*replies: Reply) -> str | None:
    """« mesure impossible » si une requête a échoué : un corps vide ne vaut pas un résultat."""
    failed = [r for r in replies if not r.ok]
    return f"mesure impossible ({describe_failure(failed[0])})" if failed else None


def background_verdict(started: dict[str, Any], later: dict[str, Any]) -> str:
    """Terminée à l'heure, en retard (processus gelé puis réveillé), ou pas du tout."""
    if later.get("instance") != started.get("instance"):
        return "inconnu : la vérification est arrivée sur une autre instance"
    task = later.get("tache") or {}
    if not task.get("terminee_le"):
        return "**pas terminée** : le processus est gelé ou coupé entre deux requêtes"
    elapsed = (
        datetime.fromisoformat(task["terminee_le"]) - datetime.fromisoformat(task["lancee_le"])
    ).total_seconds()
    if elapsed > float(task["duree_s"]) + BACKGROUND_SLACK_SECONDS:
        return (
            f"**terminée en retard** ({elapsed:.0f} s au lieu de {task['duree_s']} s) :"
            " le processus est gelé entre deux requêtes, puis réveillé"
        )
    return "exécutée jusqu'au bout, à l'heure"


def measure(base: str, *, token: str, max_wait: float) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    instances: set[str] = set()

    def sonde(path: str, timeout: float, headers: dict[str, str] | None = None) -> Reply:
        sent = {"X-Sonde-Jeton": token, **(headers or {})}
        return get(base, path, timeout=timeout, headers=sent)

    step("premier appel")
    first = get(base, "/healthz?db=1", timeout=120)
    info = sonde("/_sonde/requete", timeout=30)
    if info.code == 404:
        sys.exit(
            "Sonde introuvable : GOTCHA_PROBE=1 et le même GOTCHA_PROBE_TOKEN des deux côtés ?"
        )
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
    proxy = sonde("/_sonde/requete", timeout=30, headers={"X-Forwarded-For": FAKE_CLIENT_IP})
    instances.add(proxy.body.get("instance", "?"))
    forwarded = proxy.body.get("x_forwarded_for")
    if failed := impossible(proxy):
        verdict = failed
    elif not forwarded:
        verdict = "absent : les quotas voient le proxy ; GOTCHA_PROXY_HOPS=0"
    elif forwarded.strip() == FAKE_CLIENT_IP:
        verdict = "transmis **tel quel**, rien d'ajouté : non fiable ; GOTCHA_PROXY_HOPS=0"
    elif FAKE_CLIENT_IP in forwarded:
        verdict = "le proxy **ajoute** l'adresse vue : GOTCHA_PROXY_HOPS=1 convient"
    else:
        verdict = "le proxy **remplace** la valeur : GOTCHA_PROXY_HOPS=1 convient"
    rows.append(("Proxy : `X-Forwarded-For` reçu", f"`{forwarded}` : {verdict}"))
    retained = proxy.body.get("ip_retenue_pour_les_quotas")
    rows.append(("IP retenue pour les quotas", f"`{retained}` : l'adresse publique de ce poste ?"))
    rows.append(("`X-Forwarded-Proto` reçu", f"`{proxy.body.get('x_forwarded_proto')}`"))
    rows.append(("En-têtes reçus", ", ".join(proxy.body.get("en_tetes", []))))

    step("base de données (3 connexions)")
    bases = [sonde("/_sonde/base", timeout=30) for _ in range(3)]
    last = bases[-1].body
    if failed := impossible(*bases):
        rows.append(("Base : connexion neuve", failed))
    elif all(b.body.get("base") == "ok" for b in bases):
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
    outbound = sonde("/_sonde/sortie", timeout=60)
    out = outbound.body
    rows.append(
        (
            "Sortie vers Internet (flux Flutterwave)",
            impossible(outbound)
            or f"{out.get('sortie')} ; HTTP {out.get('code', '-')} en {out.get('duree_ms')} ms",
        )
    )

    step(f"tâche de fond ({BACKGROUND_SECONDS} s après la réponse, sans visite entre-temps)")
    launch = sonde(f"/_sonde/tache-de-fond?lancer={BACKGROUND_SECONDS}", timeout=30)
    time.sleep(BACKGROUND_SECONDS + 10)
    check = sonde("/_sonde/tache-de-fond", timeout=30)
    instances.update({launch.body.get("instance", "?"), check.body.get("instance", "?")})
    verdict = impossible(launch, check) or background_verdict(launch.body, check.body)
    rows.append(("Tâche de fond après la réponse", verdict))

    passed: float | None = None
    failure = ""
    for seconds in (s for s in WAITS if s <= max_wait):
        step(f"requête de {seconds} s")
        reply = sonde(f"/_sonde/attente?secondes={seconds}", timeout=seconds + 60)
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

    # Variable d'environnement plutôt qu'argument : le jeton ne reste pas dans l'historique.
    token = os.environ.get("GOTCHA_PROBE_TOKEN", "")
    if not token:
        sys.exit("Définissez GOTCHA_PROBE_TOKEN (le même que sur le site).")

    rows = measure(base, token=token, max_wait=30 if args.rapide else args.max)
    day = datetime.now(UTC).date().isoformat()
    print(f"\n## Mesures de l'hébergeur, {day} ({base})\n")
    print("| Question | Mesure |\n| --- | --- |")
    for question, answer in rows:
        print(f"| {question} | {answer.replace('|', '/')} |")
    print("\nÀ reporter dans docs/DECISIONS.md et dans la fiche Datacloud ; puis GOTCHA_PROBE=0.")


if __name__ == "__main__":
    main()
