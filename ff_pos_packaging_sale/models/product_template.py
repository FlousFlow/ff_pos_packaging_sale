# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ff_pos_packaging_behavior = fields.Selection(
        selection=[
            ('pos_config', 'Per POS Config'),
            ('default', 'Default Packaging'),
            ('ask', 'Ask Every Time'),
            ('unit', 'Unit by Default'),
        ],
        string='Packaging Selection Behavior',
        default='pos_config',
        required=True,
        help="What happens when this product is clicked or its barcode is scanned in POS:\n"
             "- Per POS Config: use the behavior configured on the POS\n"
             "- Default Packaging: always add the default packaging\n"
             "- Ask Every Time: open the packaging selection popup\n"
             "- Unit by Default: standard behavior (base unit)",
    )
    ff_pos_default_packaging_id = fields.Many2one(
        comodel_name='product.uom',
        string='Default POS Packaging',
        copy=False,
        check_company=True,
        help="Packaging added automatically when the product is scanned/clicked "
             "and the behavior is 'Default Packaging'.",
    )
    ff_pos_allow_unit_sale = fields.Boolean(
        string='Allow Unit Sale',
        default=True,
        help="Show the base unit as a choice in the packaging selection popup.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + [
            'ff_pos_packaging_behavior', 'ff_pos_default_packaging_id',
            'ff_pos_allow_unit_sale', 'uom_ids',
        ]
