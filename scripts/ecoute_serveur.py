#!/usr/bin/env python
"""Sert la page d'écoute en local et enregistre chaque geste dans le projet.

    python scripts/ecoute_serveur.py            # puis http://127.0.0.1:8765/

Un navigateur ne peut pas écrire un fichier : une page ouverte en local garde
donc son travail dans sa propre mémoire, séparée de tout. Ce serveur donne à la
page locale ce que la base de l'artefact donne à la page en ligne -- un
endroit où déposer l'état après chaque geste -- et cet endroit est le dépôt :

    GET  /            la page d'écoute (data/ecoute_de_controle.html)
    GET  /etat        l'état enregistré, ou 404 s'il n'y en a pas encore
    PUT  /etat        enregistre l'état, puis régénère confirmation.yaml

L'état est écrit dans `data/empreintes/ecoute.json`, versionné, au même format
que le document de la base en ligne (`{debat, misAJour, etat}`) ; le YAML de
confirmation en est régénéré à chaque écriture par `confirmation_merge.merge`,
de sorte que le projet porte le résultat sans qu'aucune étape manuelle ne
s'intercale. N'écoute que sur 127.0.0.1.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from confirmation_merge import HEADER, merge  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "data" / "ecoute_de_controle.html"
STATE = ROOT / "data" / "empreintes" / "ecoute.json"
CONFIRMATION = ROOT / "data" / "empreintes" / "confirmation.yaml"
LOCK = threading.Lock()


def save_state(document: dict) -> None:
    """Écrit l'état, puis le YAML qui en découle -- sous verrou, en entier."""
    with LOCK:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(document, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STATE)
        if CONFIRMATION.exists():
            confirmation = yaml.safe_load(CONFIRMATION.read_text(encoding="utf-8"))
            merged = merge(confirmation, document.get("etat", {}))
            CONFIRMATION.write_text(
                HEADER + yaml.safe_dump(merged, allow_unicode=True, sort_keys=False),
                encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        # La page peut aussi être ouverte en file:// (origine « null ») :
        # on répond à quiconque parle à 127.0.0.1, c'est-à-dire cette machine.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status: int, body: bytes = b"", content_type: str = "application/json") -> None:
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            if not PAGE.exists():
                self._send(404, "page absente : python scripts/confirmation_page.py".encode(),
                           "text/plain")
                return
            self._send(200, PAGE.read_bytes(), "text/html")
        elif self.path == "/etat":
            if STATE.exists():
                self._send(200, STATE.read_bytes())
            else:
                self._send(404, b"{}")
        else:
            self._send(404, b"", "text/plain")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path != "/etat":
            self._send(404, b"", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            document = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(document, dict) or not isinstance(document.get("etat"), dict):
                raise ValueError("document attendu : {debat, misAJour, etat}")
        except ValueError as error:
            self._send(400, str(error).encode(), "text/plain")
            return
        save_state(document)
        self._send(200, b'{"ok": true}')

    def log_message(self, fmt: str, *args) -> None:
        if self.command == "PUT":
            print(f"  {datetime.now():%H:%M:%S}  etat enregistre -> {STATE.relative_to(ROOT)}",
                  file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--sans-navigateur", action="store_true")
    args = ap.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Page d'ecoute : {url}\nEtat : {STATE.relative_to(ROOT)} "
          f"(existe : {STATE.exists()})\nCtrl+C pour arreter.", file=sys.stderr)
    if not args.sans_navigateur:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
