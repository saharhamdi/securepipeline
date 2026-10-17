"""Application de démonstration SecurePipeline (API Flask minimale)."""
import os
import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", ":memory:")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    return conn


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/users")
def users():
    name = request.args.get("name", "")
    conn = get_db()
    # Requête paramétrée : protège contre l'injection SQL
    rows = conn.execute("SELECT id, name FROM users WHERE name = ?", (name,)).fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])


if __name__ == "__main__":
    # Écoute sur toutes les interfaces dans le conteneur uniquement
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))  # nosemgrep
