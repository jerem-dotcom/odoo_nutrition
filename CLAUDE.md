# CLAUDE.md — Module Odoo « Nutrition »

Contexte projet à charger à chaque session. Tenir ce fichier à jour quand l'archi ou les
décisions évoluent.

## But du projet

Module **Odoo v19** personnel de suivi de **nutrition sportive** au quotidien. On saisit
ce qu'on mange par **code-barres**, les données nutritionnelles sont récupérées via l'API
**OpenFoodFacts (OFF)**. On suit les macros : calories, protéines, glucides (dont
sucres), lipides (dont saturés), fibres, sel.

Contraintes structurantes :
- **Mono-utilisateur** : ne PAS lier les enregistrements à un `res.users`/utilisateur.
- Rester **simple** : éviter la sur-ingénierie et les abstractions prématurées (code
  explicite préféré, même un peu répétitif, plutôt que des helpers génériques).

## Stack & conventions Odoo v19

- Module à la racine du repo (`__manifest__.py`, `__init__.py`). Dépend de `base`, `web`.
- `requests` (fourni par l'env Python d'Odoo) pour appeler OFF. Pas de controller web :
  les appels OFF sont **sortants** (Odoo → OFF).
- **Conventions v19** (vérifier dans le code source Odoo : `E:\mckay\odoo\addons`) :
  - Contraintes SQL via `models.Constraint("sql", "message")` — PAS `_sql_constraints`.
  - Vues liste : balise racine `<list>` (pas `<tree>`) ; syntaxe `invisible="..."` /
    `readonly="..."` (pas d'`attrs`).
  - Search view : bloc de regroupement = `<group>` **sans attributs** (`expand`/`string`
    déclenchent une erreur) contenant les `<filter context="{'group_by': ...}"/>`.
  - Focus auto sur un champ : `default_focus="1"` (un seul par form).

## Modèles

Les 8 champs macro (mêmes noms partout) : `energy_kcal`, `proteins`, `carbohydrates`,
`sugars`, `fat`, `saturated_fat`, `fiber`, `salt`.

### `nutrition.food` — Aliment (`models/nutrition_food.py`) ✅
Catalogue de produits, cache des données OFF. Représente un **produit complet**.
- Champs : `name`, `barcode` (unique), `brand`, `image_url`, `total_quantity` +
  `total_unit` (`g`/`ml`), les 8 macros **pour 100 g (ou 100 mL)**, `nutriscore_grade`
  (A-E), `nova_group` (1-4).
- OFF : `_off_fetch(barcode)` (appel API v2, header User-Agent, gestion erreurs via
  `UserError`), `_onchange_barcode` (auto-remplissage à la saisie),
  `_get_or_create_by_barcode` (find-or-create, utilisé par le journal),
  `action_refresh_off` (bouton re-sync).
- Macros stockées **par 100 unités** ; pour le produit entier : `macro/100 ×
  total_quantity`. Valable g ET mL (cf. mémoire OFF quirks).

### `nutrition.recipe` — Recette (`models/nutrition_recipe.py`) ✅
Agrégation de produits entiers. Une recette = un **Many2many `food_ids`** de
`nutrition.food`, prise à **100 %** de chaque produit.
- Totaux : `macro_recette = Σ (food.macro_pour_100 × food.total_quantity / 100)`.
  8 macros calculées **stockées** (`_compute_totals`), pour stats futures.
- Limite assumée (simplicité) : un aliment ne peut figurer qu'une fois (pas de doublon /
  pas de "2 pots"). Migrer vers un modèle de lignes si besoin un jour.

### `nutrition.log` — Journal de consommation 🔜 (à faire, cœur de l'usage)
Saisie quotidienne. Idée : saisie par **code-barres**, consommation d'un **aliment** (en
g/mL) ou d'une **recette** (en **% consommé** du total). Agrégation des macros par jour.

### `nutrition.day` + objectifs 🔜 (à faire)
Synthèse par journée : totaux réels vs **objectifs** (kcal, macros) vs restant. Objectifs
par défaut configurables (probable `res.config.settings`).

## OpenFoodFacts — points clés
- Endpoint v2 `world.openfoodfacts.org/api/v2/product/{barcode}.json`, header
  `User-Agent` requis, paramètre `fields` pour limiter la réponse.
- **Quirk** : pour récupérer le numérique `product_quantity`, demander `quantity` dans
  `fields` (sinon il n'apparaît pas). Nutriments toujours en `*_100g` même pour les mL.
- Voir la mémoire projet `off-api-quirks` pour le détail.

## État & feuille de route
- ✅ `nutrition.food` (+ OFF), `nutrition.recipe`, sécurité, menus, vues.
- 🔜 `nutrition.log` (journal), puis `nutrition.day` + objectifs, puis stats
  (pivot/graph par Nutri-Score / NOVA / date).

## Fichiers
- `models/` : `nutrition_food.py`, `nutrition_recipe.py` (+ `__init__.py`).
- `views/` : `nutrition_food_views.xml`, `nutrition_recipe_views.xml`,
  `nutrition_menus.xml`.
- `security/ir.model.access.csv` : accès complet `base.group_user` (mono-user).

## Vérification rapide
- Syntaxe Python : `python -m py_compile models/*.py`.
- XML bien formé : `python -c "import xml.dom.minidom as m; m.parse('views/<fichier>.xml')"`.
- Test fonctionnel : installer/maj le module (`-u nutrition`) sur une instance Odoo 19,
  puis dans **Nutrition → Aliments**, saisir un code-barres (ex. `3017620422003`) et
  vérifier le remplissage auto des macros.
