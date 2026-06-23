{
    'name': 'Nutrition',
    'version': '1.0',
    'summary': 'A custom module for Odoo',
    'description': 'This is a custom module developed for learning purposes.',
    'author': 'Jérémy',
    'depends': ['base', 'web'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',

        'views/nutrition_food_views.xml',
        'views/nutrition_recipe_views.xml',
        'views/nutrition_menus.xml',
    ],
    'installable': True,
    'application': True,
}