# Journal des versions

Toutes les dates sont au format AAAA-MM-JJ.

## 1.1.1 — 2026-10-20

### Corrigé
- **Montants au format français** : « 1.500,50 » (point de milliers) est désormais accepté,
  comme « 1 500,50 », « 1500,50 » ou « 1500.50 ». Les séparateurs de milliers multiples
  (« 1.234.567,89 ») sont également gérés.
- **Messages de validation visibles** : la fenêtre s'agrandit pour afficher l'erreur au lieu
  de la laisser hors écran (impression que « rien ne se passe »). Un montant non reconnu
  colore le champ en rouge pendant la saisie.

## 1.1.0 — 2026-10-20

### Ajouté
- **Catalogue complet des types de comptes** : 37 types répartis en 5 familles
  (comptes courants, épargne, placements, retraite, espèces & autres), avec sélection
  en deux temps (famille puis type) et couleur automatique selon le type.
- Répartition du patrimoine par **famille de comptes** sur le tableau de bord.
- `LICENSE` (MIT), `CHANGELOG.md`, `requirements-dev.txt`.
- Compilation automatique de l'exécutable Windows via GitHub Actions
  (`.github/workflows/build.yml`), avec publication dans les Releases.

### Corrigé
- **Listes déroulantes inutilisables** : une option de police mal formée dans le thème
  empêchait l'ouverture de toutes les boîtes déroulantes (types, comptes, catégories…).
- Démarrage impossible sur certains PC (*« Could not create temporary directory! »*) :
  l'application est désormais livrée en **mode dossier** (plus d'auto-extraction
  dans `%TEMP%`).
- Données de démonstration : plus aucune opération datée dans le futur.

### Modifié
- Application livrée avec `Installer PatrimoinePro.bat` (installation dans le profil
  utilisateur + raccourci Bureau), recommandée pour les dossiers synchronisés OneDrive.

## 1.0.0 — 2026-10-20

- Version initiale : portefeuille, transactions, projets d'épargne, budgets, rapports,
  tableau de bord, thème clair, base SQLite locale, sauvegarde et export CSV.
