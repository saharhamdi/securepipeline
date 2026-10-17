#!/usr/bin/env bash
# Crée une branche de démonstration contenant UNE faille volontaire.
# Usage : demo/run_scenario.sh <secret|image|dependency|sast>
# Ensuite : git push -u origin demo/<scénario> puis ouvrir une Pull Request.
set -euo pipefail

SCENARIO="${1:-}"
BRANCH="demo/${SCENARIO}"

case "$SCENARIO" in
  secret|image|dependency|sast) ;;
  *) echo "Usage: $0 <secret|image|dependency|sast>"; exit 1 ;;
esac

git rev-parse --git-dir >/dev/null 2>&1 || { echo "À lancer dans le dépôt Git du projet."; exit 1; }
git checkout -b "$BRANCH"

case "$SCENARIO" in
  secret)
    # Faux token GitHub au format réel (aléatoire, sans aucune valeur) — détecté par Gitleaks
    TOKEN="ghp_$(python3 -c 'import secrets,string; print("".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(36)))')"
    cat > app/config.py <<EOF
# ERREUR VOLONTAIRE (démo) : secret en dur dans le code
GITHUB_TOKEN = "${TOKEN}"
EOF
    MSG="feat: ajout de la configuration (contient un secret - DEMO)"
    ;;
  image)
    # Image de base obsolète (Debian buster en fin de vie) : nombreuses CVE HIGH/CRITICAL
    sed -i 's#^FROM .*#FROM python:3.8-slim-buster#' Dockerfile
    MSG="chore: changement de l'image de base (obsolète - DEMO)"
    ;;
  dependency)
    # Dépendance Python avec CVE connues
    sed -i 's#^flask==.*#flask==1.0#' requirements.txt
    MSG="chore: rétrogradation de Flask (vulnérable - DEMO)"
    ;;
  sast)
    cat >> app/main.py <<'EOF'


@app.get("/search")
def search():  # ERREUR VOLONTAIRE (démo) : injection SQL
    term = request.args.get("q", "")
    conn = get_db()
    rows = conn.execute(f"SELECT id, name FROM users WHERE name = '{term}'").fetchall()
    return jsonify(rows)
EOF
    MSG="feat: endpoint de recherche (injection SQL - DEMO)"
    ;;
esac

git add -A
git commit -m "$MSG"
echo
echo "Branche '$BRANCH' prête. Lance maintenant :"
echo "  git push -u origin $BRANCH   # puis ouvre une Pull Request vers main"
echo "Le pipeline doit échouer ; consulte le résumé du job pour le rapport explicatif."
