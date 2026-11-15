"""Boutique de démonstration : une page produit et un bouton « Payer » sans paiement branché.

C'est le terrain de jeu de l'agent pendant la démo du jury (docs/DEMO.md). Aucune
dépendance : `python app.py`, puis ouvrir http://localhost:8080.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

PRODUCT = {"name": "Panier de mangues de Casamance", "price_xof": 5000}

PAGE = """<!doctype html>
<html lang="fr"><meta charset="utf-8"><title>Boutique Ndaw</title>
<h1>{name}</h1><p>{price} FCFA</p>
<form method="post" action="/payer"><button>Payer avec Wave</button></form>
</html>"""


class Shop(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self._send(200, PAGE.format(name=PRODUCT["name"], price=PRODUCT["price_xof"]))

    def do_POST(self) -> None:
        if self.path != "/payer":
            self._send(404, "Introuvable")
            return
        # TODO : brancher le paiement Wave ici.
        self._send(501, "Paiement pas encore branché")


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Shop).serve_forever()
