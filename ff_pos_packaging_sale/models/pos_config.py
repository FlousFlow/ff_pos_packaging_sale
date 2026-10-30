# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    ff_packaging_selection_behavior = fields.Selection(
        selection=[
            ('default', 'Default Packaging'),
            ('ask', 'Ask Every Time'),
            ('unit', 'Unit by Default'),
        ],
        string='Packaging Selection Behavior',
        default='default',
        required=True,
        help="Default behavior for products whose own behavior is 'Per POS Config'.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['ff_packaging_selection_behavior']
