# `.github/rulesets/` : les règles de `main`

**Responsable :** Abdoul Aziz (administrateur du dépôt). **Relecteur :** Khalifa.

`protection-main.json` décrit l'ensemble de règles « Protection de main », appliqué sur GitHub. `main` est déployée telle quelle sur Datacloud : elle doit toujours marcher.

## Ce qui est imposé

- **pas de push direct** : tout passe par une PR ;
- **une approbation** d'un autre membre, et toutes les conversations résolues ;
- une nouvelle modification **annule** l'approbation précédente ;
- les **huit contrôles CircleCI** (`ci/circleci: pr-rules`, `lint`, `tests-py3.11`, `tests-py3.12`, `tests-py3.13`, `licences`, `docker`, `audit`) doivent être **verts**, sur une branche **à jour** avec `main` ;
- fusion en **squash** uniquement, historique linéaire ;
- pas de suppression ni de réécriture (`force push`) de `main`.

L'administrateur du dépôt peut contourner les règles **pour une PR** seulement, en cas d'urgence (CircleCI en panne, par exemple). Ça ne doit pas arriver en temps normal.

## Modifier la règle

1. Modifier `protection-main.json` dans une PR (par exemple quand un job CircleCI est ajouté ou renommé : son statut `ci/circleci: <job>` change de nom).
2. Une fois la PR approuvée, l'administrateur applique la règle :

   ```bash
   gh api repos/abdlaziz221/gotcha/rulesets --jq '.[] | select(.name == "Protection de main") | .id'
   ```

   ```bash
   gh api -X PUT repos/abdlaziz221/gotcha/rulesets/<id> --input .github/rulesets/protection-main.json
   ```

3. Vérifier ce qui s'applique réellement à `main` :

   ```bash
   gh api repos/abdlaziz221/gotcha/rules/branches/main
   ```

Un contrôle obligatoire qui n'existe plus (job renommé, supprimé) bloque **toutes** les fusions : appliquer la nouvelle règle dans la foulée.
