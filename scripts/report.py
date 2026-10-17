#!/usr/bin/env python3
"""Génère un rapport explicatif (Markdown, en français) à partir des sorties JSON
des outils de sécurité et décide si le "security gate" doit bloquer le pipeline.

Usage : report.py <outil> <fichier.json> [--no-fail]
Outils : gitleaks | semgrep | trivy | grype | pip-audit
Code de sortie : 1 si des constats bloquants existent, sinon 0.
"""
import argparse
import json
import os
import sys

BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}


def load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        content = fh.read().strip()
    return json.loads(content) if content else None


# --- Analyseurs : chacun renvoie (titre, colonnes, lignes, nb_bloquants, remédiation) ---

def parse_gitleaks(data):
    findings = data or []
    rows = [
        [f.get("RuleID", "?"), f"{f.get('File', '?')}:{f.get('StartLine', '?')}",
         (f.get("Commit") or "")[:8], f.get("Author", "?")]
        for f in findings
    ]
    fix = (
        "1. **Révoquer/régénérer immédiatement** le secret exposé (il est compromis dès qu'il est commité).\n"
        "2. Retirer le secret du code et le lire depuis une variable d'environnement ou un coffre "
        "(GitHub Secrets, Vault).\n"
        "3. Purger l'historique Git si nécessaire (`git filter-repo`) — la révocation reste indispensable."
    )
    return "Détection de secrets (Gitleaks)", ["Règle", "Emplacement", "Commit", "Auteur"], rows, len(rows), fix


def parse_semgrep(data):
    results = (data or {}).get("results", [])
    rows, blocking = [], 0
    for r in results:
        sev = r.get("extra", {}).get("severity", "INFO")
        if sev == "ERROR":
            blocking += 1
        msg = " ".join(r.get("extra", {}).get("message", "").split())[:140]
        rows.append([sev, r.get("check_id", "?").split(".")[-1],
                     f"{r.get('path')}:{r.get('start', {}).get('line')}", msg])
    fix = (
        "Corriger le code signalé (voir colonne *Description*). Les règles de sévérité `ERROR` "
        "bloquent le pipeline ; `WARNING`/`INFO` sont remontées à titre informatif."
    )
    return "Analyse statique du code — SAST (Semgrep)", ["Sévérité", "Règle", "Emplacement", "Description"], rows, blocking, fix


def parse_trivy(data):
    rows, blocking = [], 0
    for res in (data or {}).get("Results", []):
        for v in res.get("Vulnerabilities") or []:
            sev = v.get("Severity", "UNKNOWN")
            fixed = v.get("FixedVersion", "")
            is_blocking = sev in BLOCKING_SEVERITIES and bool(fixed)
            blocking += is_blocking
            if sev in BLOCKING_SEVERITIES:
                rows.append([sev, v.get("VulnerabilityID"), v.get("PkgName"),
                             v.get("InstalledVersion"), fixed or "aucun correctif"])
        for m in res.get("Misconfigurations") or []:
            sev = m.get("Severity", "UNKNOWN")
            if sev in BLOCKING_SEVERITIES:
                blocking += 1
                rows.append([sev, m.get("ID"), m.get("Title"), res.get("Target"), "voir config"])
    rows.sort(key=lambda r: r[0] != "CRITICAL")
    fix = (
        "Mettre à jour l'image de base (`FROM`) vers une version maintenue et à jour, puis les paquets "
        "listés vers la version corrigée (colonne *Correctif*). Les vulnérabilités sans correctif "
        "disponible ne bloquent pas (`ignore-unfixed`)."
    )
    return "Scan de l'image Docker (Trivy)", ["Sévérité", "ID", "Paquet", "Installé", "Correctif"], rows, blocking, fix


def parse_grype(data):
    rows, blocking = [], 0
    for m in (data or {}).get("matches", []):
        vuln, art = m.get("vulnerability", {}), m.get("artifact", {})
        sev = (vuln.get("severity") or "Unknown").upper()
        fixed = ", ".join(vuln.get("fix", {}).get("versions") or [])
        if sev in BLOCKING_SEVERITIES:
            rows.append([sev, vuln.get("id"), art.get("name"), art.get("version"), fixed or "aucun correctif"])
            blocking += bool(fixed)
    rows.sort(key=lambda r: r[0] != "CRITICAL")
    fix = (
        "Les composants listés proviennent du **SBOM** généré par Syft. Mettre à jour les dépendances "
        "ou l'image de base vers la version indiquée dans la colonne *Correctif*."
    )
    return "Analyse du SBOM (Syft + Grype)", ["Sévérité", "ID", "Composant", "Version", "Correctif"], rows, blocking, fix


def parse_pip_audit(data):
    rows, blocking = [], 0
    deps = data.get("dependencies", []) if isinstance(data, dict) else (data or [])
    for d in deps:
        for v in d.get("vulns", []):
            blocking += 1
            rows.append([v.get("id"), d.get("name"), d.get("version"),
                         ", ".join(v.get("fix_versions") or []) or "aucun correctif"])
    fix = "Mettre à jour la dépendance Python vers la version corrigée (colonne *Correctif*) dans `requirements.txt`."
    return "Analyse des dépendances — SCA (pip-audit)", ["ID", "Paquet", "Version", "Correctif"], rows, blocking, fix


PARSERS = {
    "gitleaks": parse_gitleaks,
    "semgrep": parse_semgrep,
    "trivy": parse_trivy,
    "grype": parse_grype,
    "pip-audit": parse_pip_audit,
}


def render(title, cols, rows, blocking, fix):
    ok = blocking == 0
    out = [f"## {'✅' if ok else '❌'} {title}", ""]
    if ok:
        out.append("Aucun constat bloquant.")
    else:
        out.append(f"**{blocking} constat(s) bloquant(s)** — le déploiement est refusé.")
    if rows:
        out += ["", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in rows[:50]:
            out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
        if len(rows) > 50:
            out.append(f"\n… et {len(rows) - 50} autre(s) (voir l'artefact de rapport JSON).")
    if not ok:
        out += ["", "### Comment corriger", fix]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tool", choices=PARSERS)
    ap.add_argument("path")
    ap.add_argument("--no-fail", action="store_true", help="ne pas bloquer (rapport seul)")
    args = ap.parse_args()

    data = load(args.path)
    if data is None and args.tool != "gitleaks":
        print(f"::error::Rapport introuvable ou vide : {args.path}")
        return 1

    title, cols, rows, blocking, fix = PARSERS[args.tool](data)
    md = render(title, cols, rows, blocking, fix)
    print(md)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    if blocking:
        print(f"::error title={title}::{blocking} constat(s) bloquant(s). Voir le résumé du job.")
    return 1 if blocking and not args.no_fail else 0


if __name__ == "__main__":
    sys.exit(main())
