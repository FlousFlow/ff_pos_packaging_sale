# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Packaging Sale',
    'version': '20.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Prompt for the selling unit in POS and Sales and keep stock in base UoM',
    'description': """
POS Packaging Sale
==================
Sell products in Point of Sale using commercial packagings (Carton, Box, Pack...)
while the actual stock movement stays in the product base UoM.

Key principles:
- One product, one barcode — no separate products or BoMs per packaging
- The customer sees "2 Carton" on the POS screen, receipt and invoice
- Stock picking / stock move deducts 48 Units internally (2 x 24)
- Applicable pricelist rules determine packaging prices; optional packaging prices are fallback values
- Taxes are computed on the packaging price
- Partial refunds keep the same commercial unit (-1 Carton => +24 Units)
- Structured packaging data is stored on pos.order.line and account.move.line
""",
    'author': 'Flous Flow',
    'website': 'https://flousflow.com',
    'support': 'support@flousflow.com',
    'license': 'LGPL-3',
    'images': [
        'static/description/images/cover_screenshot.png',
        'static/description/images/packaging_popup.png',
        'static/description/images/orderline_2_carton.png',
        'static/description/images/receipt_2_carton.png',
    ],
    'depends': ['point_of_sale', 'pos_stock', 'sale_management'],
    'data': [
        'views/product_uom_views.xml',
        'report/report_invoice_templates.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'ff_pos_packaging_sale/static/src/app/**/*',
        ],
        'web.assets_backend': [
            'ff_pos_packaging_sale/static/src/sale/**/*',
        ],
    },
    'installable': True,
    'application': False,
}
