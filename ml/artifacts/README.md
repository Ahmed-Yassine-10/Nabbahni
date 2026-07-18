# Modèles entraînés

Ces artefacts sont versionnés pour qu'un nouveau contributeur puisse lancer la
plateforme **sans attendre 10 à 20 minutes d'entraînement**. `setup.bat` détecte
`shortage.joblib` et saute l'étape 5.

## ⚠️ Entraînés sur des données synthétiques

Ils sont issus du générateur (`data-generator/`), **pas** de données de vente
réelles. Ils servent à faire tourner la démonstration de bout en bout. Ils ne
sont ni validés cliniquement, ni utilisables pour une décision réelle
d'approvisionnement. Un déploiement national exige un réentraînement sur les
données réelles de la PCT, suivi d'une validation métier.

## Contenu

| Fichier | Rôle |
|---|---|
| `demand-champion-7.joblib` | Prévision de demande, horizon 7 jours |
| `demand-champion-14.joblib` | Horizon 14 jours |
| `demand-champion-30.joblib` | Horizon 30 jours |
| `demand-champion-90.joblib` | Horizon 90 jours |
| `shortage.joblib` | Classifieur de rupture (LightGBM) |

Les candidats par famille (`demand-lightgbm-*`, `demand-xgboost-*`) ne sont pas
versionnés : chaque champion en est une copie octet pour octet, et les métriques
des perdants sont déjà enregistrées dans la table `model_runs`.

## Portabilité

Les 16 features sont purement comportementales — lags, moyennes glissantes,
calendrier, indice grippal, prix, statut essentiel. **Aucun identifiant
(UUID de médicament ou de gouvernorat) n'est encodé dans le modèle**, donc ces
artefacts restent valides après un `seed --reset` qui régénère de nouveaux
identifiants.

## Réentraîner

```bat
rem supprimer les artefacts force un entraînement complet
rd /s /q ml\artifacts
cd ml && %LOCALAPPDATA%\SentinelleRx\venv\Scripts\python.exe -m ml.train_all
```

Le champion de chaque horizon est sélectionné par WAPE en validation à origine
glissante (3 plis). Performances de la version versionnée :

| Horizon | Famille | WAPE |
|---|---|---|
| 7 j | LightGBM | 6,0 % |
| 14 j | LightGBM | 6,0 % |
| 30 j | LightGBM | 6,1 % |
| 90 j | XGBoost | 10,9 % |

Classifieur de rupture : AUC 0,999 · AP 0,981.
