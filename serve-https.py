#!/usr/bin/env python3
"""Serves the game to an iPad or iPhone on the same Wi-Fi.

iOS only allows the microphone and motion sensors on https pages, so this makes
a throwaway certificate for this Mac's local address. Safari warns about it once.
"""
import http.server
import pathlib
import socket
import ssl
import subprocess
import urllib.parse

PORT = 8765
HERE = pathlib.Path(__file__).resolve().parent
# Kept outside the game folder so the private key can never be served or uploaded with it.
CERTS = pathlib.Path.home() / ".boop-the-dot-certs"


def local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]


def make_cert(ip):
    CERTS.mkdir(exist_ok=True)
    cert, key = CERTS / f"{ip}.pem", CERTS / f"{ip}.key"
    if not cert.exists():
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
             "-keyout", str(key), "-out", str(cert), "-subj", "/CN=Boop the Dot",
             "-addext", f"subjectAltName=IP:{ip},DNS:localhost",
             "-addext", "extendedKeyUsage=serverAuth"],
            check=True, capture_output=True)
    return cert, key


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def send_head(self):
        # Only the game itself is served, never this script.
        if urllib.parse.unquote(self.path.split("?")[0]).endswith(".py"):
            self.send_error(404)
            return None
        return super().send_head()


ip = local_ip()
cert, key = make_cert(ip)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(cert, key)
server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
server.socket = context.wrap_socket(server.socket, server_side=True)
print(f"On the iPad or iPhone, open Safari and go to:  https://{ip}:{PORT}", flush=True)
print("Safari warns the connection is not private: tap Show Details, then visit this website.", flush=True)
server.serve_forever()
