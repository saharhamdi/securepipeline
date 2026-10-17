# SecurePipeline — DevSecOps CI/CD Pipeline

Pipeline CI/CD GitHub Actions qui **teste le code, détecte les vulnérabilités et bloque les déploiements dangereux**, avec un rapport explicatif en français à chaque échec.

## Architecture

```
Commit ─► Build & Test ─► Gitleaks ─► Semgrep ─► SCA ─► Docker build ─► Trivy ─► Syft (SBOM) ─► Grype ─► SECURITY GATE ─► Publish (GHCR)
                          secrets     SAST       pip-audit             image     inventaire      CVE du SBOM    bloque si échec     main seulement
```

| Étape | Outil | Ce qui est détecté | Condition de blocage |
|---|---|---|---|
| Build & Test | pytest + coverage | Régressions | Test en échec ou couverture < 70 % |
| Secrets | **Gitleaks** | Clés/tokens dans tout l'historique Git | 1 secret détecté |
| SAST | **Semgrep** | Injection SQL, debug actif, mauvaises pratiques | Règle de sévérité `ERROR` |
| SCA | **pip-audit** (+ OWASP Dependency-Check hebdo) | CVE dans les dépendances Python | 1 CVE avec correctif |
| Image | **Trivy** | CVE de l'image + mauvaises configs Dockerfile | `HIGH`/`CRITICAL` avec correctif |
| SBOM | **Syft** → **Grype** | Inventaire CycloneDX/SPDX puis CVE du SBOM | `HIGH`/`CRITICAL` avec correctif |
| Gate | job `security-gate` | Agrège tous les jobs | Un seul job rouge = pas de publication |

Les jobs de sécurité produisent un **résumé Markdown** (onglet *Summary* du run) : constat, emplacement, sévérité, et section « Comment corriger ». Les rapports JSON et les SBOM sont conservés comme artefacts.

## Structure

```
app/                       API Flask de démonstration
tests/                     Tests unitaires
Dockerfile                 Image durcie (non-root, slim, healthcheck)
.github/workflows/
  secure-pipeline.yml      Pipeline principal (7 jobs)
  dependency-check.yml     OWASP Dependency-Check (hebdo / manuel)
.gitleaks.toml             Config Gitleaks
.semgrep/custom-rules.yml  Règles Semgrep personnalisées
scripts/report.py          Rapports explicatifs + décision de blocage
demo/run_scenario.sh       Génère les branches de démo (secret, image, dépendance, SAST)
```

## Mise en route

1. Crée un dépôt GitHub (public, ou privé avec GitHub Advanced Security pour les SARIF) et pousse ce projet sur `main` :
   ```bash
   git init -b main && git add -A && git commit -m "feat: SecurePipeline"
   git remote add origin git@github.com:<toi>/securepipeline.git && git push -u origin main
   ```
2. Vérifie que le run sur `main` est **vert** (la base propre doit passer tous les contrôles).
3. Dans *Settings → Branches*, protège `main` : exige la Pull Request et le check **« 6 · Security Gate »** avant fusion.
4. Facultatif : ajoute le secret `NVD_API_KEY` pour le workflow Dependency-Check.

> Le runtime de l'image de base évolue : si une nouvelle CVE `HIGH` avec correctif apparaît sur `python:3.12-slim-bookworm`, le pipeline devient rouge, ce qui est le comportement voulu. Reconstruis alors l'image avec la base à jour.

## Démonstration : un commit dangereux fait échouer la pipeline

Chaque scénario crée une branche avec **une** faille volontaire. Pousse-la et ouvre une Pull Request vers `main`.

```bash
demo/run_scenario.sh secret       # token GitHub en dur       → job « Secrets (Gitleaks) » rouge
demo/run_scenario.sh image        # image de base obsolète     → job « Image Docker » rouge (Trivy + Grype)
demo/run_scenario.sh dependency   # Flask 1.0 vulnérable        → job « SCA » rouge
demo/run_scenario.sh sast         # injection SQL               → job « SAST » rouge
git push -u origin demo/<scénario>
```

Pour chaque échec : ouvre le run, onglet **Summary** → tu obtiens le tableau des constats et les étapes de correction. Le job **Security Gate** est bloqué, la publication n'a pas lieu et la PR ne peut pas être fusionnée.

Pistes pour la capture d'écran / vidéo du portfolio : run vert sur `main`, run rouge sur `demo/secret` avec son résumé, et PR bloquée par la protection de branche.

### Remarques

- **Push protection GitHub** : le token factice du scénario `secret` peut être refusé au `git push` par le *secret scanning*. Fais la démo sur un dépôt de test avec push protection désactivée (*Settings → Code security*), ou utilise le lien de contournement « c'est un faux secret » proposé par GitHub. Le token est généré aléatoirement et n'a aucune valeur.
- Un secret poussé réellement doit toujours être **révoqué**, même après suppression du commit.

## Pistes d'amélioration

- Signer l'image (Cosign) et attacher le SBOM comme attestation.
- Ajouter DAST (OWASP ZAP) sur un environnement éphémère.
- Passer en `trivy` + `grype` avec une politique d'exceptions (`.trivyignore`, VEX) tracée et datée.
- Déployer via GitOps (ArgoCD) et Kubernetes avec politiques OPA, comme sur le schéma d'architecture.
