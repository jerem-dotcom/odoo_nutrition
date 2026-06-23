from odoo import api, fields, models


class NutritionRecipe(models.Model):
    _name = "nutrition.recipe"
    _description = "Recette"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    food_ids = fields.Many2many("nutrition.food", string="Aliments")

    # Totaux de la recette complète (somme des produits entiers).
    energy_kcal = fields.Float(string="Calories (kcal)", compute="_compute_totals", store=True)
    proteins = fields.Float(string="Protéines (g)", compute="_compute_totals", store=True)
    carbohydrates = fields.Float(string="Glucides (g)", compute="_compute_totals", store=True)
    sugars = fields.Float(string="dont sucres (g)", compute="_compute_totals", store=True)
    fat = fields.Float(string="Lipides (g)", compute="_compute_totals", store=True)
    saturated_fat = fields.Float(string="dont saturés (g)", compute="_compute_totals", store=True)
    fiber = fields.Float(string="Fibres (g)", compute="_compute_totals", store=True)
    salt = fields.Float(string="Sel (g)", compute="_compute_totals", store=True)

    @api.depends(
        "food_ids",
        "food_ids.total_quantity",
        "food_ids.energy_kcal",
        "food_ids.proteins",
        "food_ids.carbohydrates",
        "food_ids.sugars",
        "food_ids.fat",
        "food_ids.saturated_fat",
        "food_ids.fiber",
        "food_ids.salt",
    )
    def _compute_totals(self):
        """Somme des macros de chaque produit pris en entier :
        macro_produit = macro_pour_100g * poids_total / 100."""
        for recipe in self:
            foods = recipe.food_ids
            recipe.energy_kcal = sum(f.energy_kcal * f.total_quantity / 100 for f in foods)
            recipe.proteins = sum(f.proteins * f.total_quantity / 100 for f in foods)
            recipe.carbohydrates = sum(f.carbohydrates * f.total_quantity / 100 for f in foods)
            recipe.sugars = sum(f.sugars * f.total_quantity / 100 for f in foods)
            recipe.fat = sum(f.fat * f.total_quantity / 100 for f in foods)
            recipe.saturated_fat = sum(f.saturated_fat * f.total_quantity / 100 for f in foods)
            recipe.fiber = sum(f.fiber * f.total_quantity / 100 for f in foods)
            recipe.salt = sum(f.salt * f.total_quantity / 100 for f in foods)
