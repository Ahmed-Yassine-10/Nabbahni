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

### ⚠️ Ne lisez pas ces métriques comme une performance réelle

Une AUC de 0,999 n'arrive pas sur des données réelles. Elle s'explique par la
construction du jeu synthétique : le générateur fabrique les épisodes de rupture
à partir des mêmes signaux que le classifieur reçoit en entrée (couverture,
retards fournisseurs, historique de rupture). Le problème est donc quasi
séparable — le modèle retrouve une règle qui a été écrite en amont.

Cela se voit au scoring : les probabilités sont bimodales, proches de 0 ou
proches de 1, avec très peu de cas intermédiaires. Sur un seed différent
(777), 1700 prédictions ne produisent que 95 valeurs de probabilité distinctes.

Conséquence pratique : la plupart des niveaux `critical` proviennent de la règle
métier de sécurité (couverture < 5 jours sur un médicament essentiel), pas d'une
probabilité élevée du modèle. Le pipeline est correct et vérifiable de bout en
bout ; **la valeur prédictive, elle, ne sera mesurable qu'après réentraînement
sur des données réelles.**
