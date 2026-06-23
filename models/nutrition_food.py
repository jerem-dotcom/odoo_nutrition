import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2/product/%s.json"
OFF_FIELDS = (
    "product_name,product_name_fr,brands,image_url,quantity,"
    "product_quantity_unit,nutriscore_grade,nova_group,nutriments"
)
OFF_USER_AGENT = "Odoo-Nutrition/1.0 (perso)"
OFF_TIMEOUT = 10

# Mapping macro Odoo -> clé OpenFoodFacts dans "nutriments" (valeurs pour 100 g)
OFF_NUTRIMENT_MAP = {
    "energy_kcal": "energy-kcal_100g",
    "proteins": "proteins_100g",
    "carbohydrates": "carbohydrates_100g",
    "sugars": "sugars_100g",
    "fat": "fat_100g",
    "saturated_fat": "saturated-fat_100g",
    "fiber": "fiber_100g",
    "salt": "salt_100g",
}


class NutritionFood(models.Model):
    _name = "nutrition.food"
    _description = "Aliment"
    _order = "name"
    _rec_names_search = ["name", "barcode"]

    name = fields.Char(string="Nom", required=True)
    barcode = fields.Char(string="Code-barres", index=True)
    brand = fields.Char(string="Marque")
    image_url = fields.Char(string="Image (URL)")
    total_quantity = fields.Float(string="Quantité totale")
    total_unit = fields.Selection(
        [("g", "g"), ("ml", "mL")],
        string="Unité",
        default="g",
    )

    # Macros pour 100 g
    energy_kcal = fields.Float(string="Calories (kcal)")
    proteins = fields.Float(string="Protéines (g)")
    carbohydrates = fields.Float(string="Glucides (g)")
    sugars = fields.Float(string="dont sucres (g)")
    fat = fields.Float(string="Lipides (g)")
    saturated_fat = fields.Float(string="dont saturés (g)")
    fiber = fields.Float(string="Fibres (g)")
    salt = fields.Float(string="Sel (g)")

    # Classification OpenFoodFacts (axes de stats)
    nutriscore_grade = fields.Selection(
        [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("e", "E")],
        string="Nutri-Score",
    )
    nova_group = fields.Selection(
        [
            ("1", "1 - Non/peu transformé"),
            ("2", "2 - Ingrédient culinaire"),
            ("3", "3 - Transformé"),
            ("4", "4 - Ultra-transformé"),
        ],
        string="Groupe NOVA",
    )

    _barcode_uniq = models.Constraint(
        "unique(barcode)",
        "Un aliment existe déjà avec ce code-barres.",
    )

    # -- OpenFoodFacts ----------------------------------------------------

    @api.model
    def _off_fetch(self, barcode):
        """Interroge l'API OpenFoodFacts et renvoie un dict de valeurs prêtes à écrire
        sur un enregistrement nutrition.food. Lève UserError en cas d'échec."""
        if not barcode:
            raise UserError("Aucun code-barres fourni.")
        url = OFF_BASE_URL % barcode
        try:
            response = requests.get(
                url,
                params={"fields": OFF_FIELDS},
                headers={"User-Agent": OFF_USER_AGENT},
                timeout=OFF_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            _logger.warning("Échec de l'appel OpenFoodFacts pour %s : %s", barcode, exc)
            raise UserError(
                "Impossible de contacter OpenFoodFacts pour le code-barres %s.\n%s"
                % (barcode, exc)
            )

        product = data.get("product")
        # En v2, status==0 (ou absence de product) signale un produit introuvable.
        if not product or data.get("status") == 0:
            raise UserError(
                "Aucun produit trouvé sur OpenFoodFacts pour le code-barres %s." % barcode
            )

        nutriments = product.get("nutriments") or {}
        values = {
            "barcode": barcode,
            "name": product.get("product_name_fr")
            or product.get("product_name")
            or ("Produit %s" % barcode),
            "brand": product.get("brands"),
            "image_url": product.get("image_url"),
        }

        qty = product.get("product_quantity")
        unit = (product.get("product_quantity_unit") or "").lower()
        try:
            values["total_quantity"] = float(qty) if qty else 0.0
        except (TypeError, ValueError):
            values["total_quantity"] = 0.0
        values["total_unit"] = "ml" if unit == "ml" else "g"
        for field_name, off_key in OFF_NUTRIMENT_MAP.items():
            values[field_name] = nutriments.get(off_key, 0.0) or 0.0

        grade = (product.get("nutriscore_grade") or "").lower()
        values["nutriscore_grade"] = grade if grade in ("a", "b", "c", "d", "e") else False
        nova = product.get("nova_group")
        nova = str(nova) if nova not in (None, "") else ""
        values["nova_group"] = nova if nova in ("1", "2", "3", "4") else False

        return values

    @api.onchange("barcode")
    def _onchange_barcode(self):
        """Récupère automatiquement nom, marque, image et macros depuis OpenFoodFacts
        dès qu'un code-barres est saisi dans le formulaire."""
        barcode = (self.barcode or "").strip()
        if not barcode:
            return
        try:
            values = self._off_fetch(barcode)
        except UserError as exc:
            return {
                "warning": {
                    "title": "OpenFoodFacts",
                    "message": str(exc),
                }
            }
        self.update(values)

    @api.model
    def _get_or_create_by_barcode(self, barcode):
        """Renvoie l'aliment correspondant au code-barres, en le récupérant depuis
        OpenFoodFacts et en le créant s'il n'existe pas encore."""
        barcode = (barcode or "").strip()
        if not barcode:
            raise UserError("Aucun code-barres fourni.")
        food = self.search([("barcode", "=", barcode)], limit=1)
        if food:
            return food
        return self.create(self._off_fetch(barcode))

    def action_refresh_off(self):
        """Re-synchronise les macros depuis OpenFoodFacts à partir du code-barres."""
        for food in self:
            if not food.barcode:
                raise UserError("Renseignez un code-barres avant de synchroniser.")
            food.write(self._off_fetch(food.barcode))
        return True
