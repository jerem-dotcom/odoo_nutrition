from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class NutritionLog(models.Model):
    _name = "nutrition.log"
    _description = "Journée de consommation"
    _order = "date desc"

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    food_line_ids = fields.One2many("nutrition.log.food", "log_id", string="Aliments")
    recipe_line_ids = fields.One2many("nutrition.log.recipe", "log_id", string="Recettes")

    # Champ de saisie rapide : un code-barres à ajouter via le bouton dédié.
    barcode = fields.Char(string="Code-barres", copy=False)

    # Totaux du jour = lignes aliments + lignes recettes.
    energy_kcal = fields.Float(string="Calories (kcal)", compute="_compute_totals", store=True)
    proteins = fields.Float(string="Protéines (g)", compute="_compute_totals", store=True)
    carbohydrates = fields.Float(string="Glucides (g)", compute="_compute_totals", store=True)
    sugars = fields.Float(string="dont sucres (g)", compute="_compute_totals", store=True)
    fat = fields.Float(string="Lipides (g)", compute="_compute_totals", store=True)
    saturated_fat = fields.Float(string="dont saturés (g)", compute="_compute_totals", store=True)
    fiber = fields.Float(string="Fibres (g)", compute="_compute_totals", store=True)
    salt = fields.Float(string="Sel (g)", compute="_compute_totals", store=True)

    _date_uniq = models.Constraint(
        "unique(date)",
        "Une journée existe déjà pour cette date.",
    )

    @api.depends(
        "food_line_ids.energy_kcal", "food_line_ids.proteins",
        "food_line_ids.carbohydrates", "food_line_ids.sugars", "food_line_ids.fat",
        "food_line_ids.saturated_fat", "food_line_ids.fiber", "food_line_ids.salt",
        "recipe_line_ids.energy_kcal", "recipe_line_ids.proteins",
        "recipe_line_ids.carbohydrates", "recipe_line_ids.sugars", "recipe_line_ids.fat",
        "recipe_line_ids.saturated_fat", "recipe_line_ids.fiber", "recipe_line_ids.salt",
    )
    def _compute_totals(self):
        for log in self:
            foods, recipes = log.food_line_ids, log.recipe_line_ids
            log.energy_kcal = sum(foods.mapped("energy_kcal")) + sum(recipes.mapped("energy_kcal"))
            log.proteins = sum(foods.mapped("proteins")) + sum(recipes.mapped("proteins"))
            log.carbohydrates = sum(foods.mapped("carbohydrates")) + sum(recipes.mapped("carbohydrates"))
            log.sugars = sum(foods.mapped("sugars")) + sum(recipes.mapped("sugars"))
            log.fat = sum(foods.mapped("fat")) + sum(recipes.mapped("fat"))
            log.saturated_fat = sum(foods.mapped("saturated_fat")) + sum(recipes.mapped("saturated_fat"))
            log.fiber = sum(foods.mapped("fiber")) + sum(recipes.mapped("fiber"))
            log.salt = sum(foods.mapped("salt")) + sum(recipes.mapped("salt"))

    def action_add_barcode(self):
        """Résout le code-barres via OpenFoodFacts (crée l'aliment si besoin) et ajoute
        une ligne aliment à la journée."""
        self.ensure_one()
        barcode = (self.barcode or "").strip()
        if not barcode:
            raise UserError("Saisissez un code-barres.")
        food = self.env["nutrition.food"]._get_or_create_by_barcode(barcode)
        self.food_line_ids = [Command.create({"food_id": food.id})]
        self.barcode = False
        return True


class NutritionLogFood(models.Model):
    _name = "nutrition.log.food"
    _description = "Ligne aliment consommé"

    log_id = fields.Many2one("nutrition.log", string="Journée", required=True, ondelete="cascade")
    food_id = fields.Many2one("nutrition.food", string="Aliment", required=True)
    percentage = fields.Float(string="% consommé", default=100.0)

    energy_kcal = fields.Float(string="Calories (kcal)", compute="_compute_macros", store=True)
    proteins = fields.Float(string="Protéines (g)", compute="_compute_macros", store=True)
    carbohydrates = fields.Float(string="Glucides (g)", compute="_compute_macros", store=True)
    sugars = fields.Float(string="dont sucres (g)", compute="_compute_macros", store=True)
    fat = fields.Float(string="Lipides (g)", compute="_compute_macros", store=True)
    saturated_fat = fields.Float(string="dont saturés (g)", compute="_compute_macros", store=True)
    fiber = fields.Float(string="Fibres (g)", compute="_compute_macros", store=True)
    salt = fields.Float(string="Sel (g)", compute="_compute_macros", store=True)

    @api.depends(
        "percentage", "food_id.total_quantity",
        "food_id.energy_kcal", "food_id.proteins", "food_id.carbohydrates",
        "food_id.sugars", "food_id.fat", "food_id.saturated_fat", "food_id.fiber",
        "food_id.salt",
    )
    def _compute_macros(self):
        """% consommé du produit entier :
        macros_pour_100 × total_quantity/100 × pourcentage/100."""
        for line in self:
            food = line.food_id
            coef = food.total_quantity * (line.percentage or 0.0) / 10000.0
            line.energy_kcal = food.energy_kcal * coef
            line.proteins = food.proteins * coef
            line.carbohydrates = food.carbohydrates * coef
            line.sugars = food.sugars * coef
            line.fat = food.fat * coef
            line.saturated_fat = food.saturated_fat * coef
            line.fiber = food.fiber * coef
            line.salt = food.salt * coef


class NutritionLogRecipe(models.Model):
    _name = "nutrition.log.recipe"
    _description = "Ligne recette consommée"

    log_id = fields.Many2one("nutrition.log", string="Journée", required=True, ondelete="cascade")
    recipe_id = fields.Many2one("nutrition.recipe", string="Recette", required=True)
    percentage = fields.Float(string="% consommé", default=100.0)

    energy_kcal = fields.Float(string="Calories (kcal)", compute="_compute_macros", store=True)
    proteins = fields.Float(string="Protéines (g)", compute="_compute_macros", store=True)
    carbohydrates = fields.Float(string="Glucides (g)", compute="_compute_macros", store=True)
    sugars = fields.Float(string="dont sucres (g)", compute="_compute_macros", store=True)
    fat = fields.Float(string="Lipides (g)", compute="_compute_macros", store=True)
    saturated_fat = fields.Float(string="dont saturés (g)", compute="_compute_macros", store=True)
    fiber = fields.Float(string="Fibres (g)", compute="_compute_macros", store=True)
    salt = fields.Float(string="Sel (g)", compute="_compute_macros", store=True)

    @api.depends(
        "percentage", "recipe_id.energy_kcal", "recipe_id.proteins",
        "recipe_id.carbohydrates", "recipe_id.sugars", "recipe_id.fat",
        "recipe_id.saturated_fat", "recipe_id.fiber", "recipe_id.salt",
    )
    def _compute_macros(self):
        """macros_totales_recette × pourcentage / 100."""
        for line in self:
            factor = (line.percentage or 0.0) / 100.0
            recipe = line.recipe_id
            line.energy_kcal = recipe.energy_kcal * factor
            line.proteins = recipe.proteins * factor
            line.carbohydrates = recipe.carbohydrates * factor
            line.sugars = recipe.sugars * factor
            line.fat = recipe.fat * factor
            line.saturated_fat = recipe.saturated_fat * factor
            line.fiber = recipe.fiber * factor
            line.salt = recipe.salt * factor
