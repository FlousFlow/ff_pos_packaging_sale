# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Structured POS packaging data (NOT description strings) so the invoice
    # report can display the commercial unit and future reports can aggregate
    # per packaging (Product | Packaging | Packages Sold | Base Units).
    ff_pos_packaging_id = fields.Many2one(
        comodel_name='product.uom',
        string='POS Packaging',
        index='btree_not_null',
        copy=False,
        readonly=True,
    )
    ff_pos_packaging_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='POS Packaging UoM',
        copy=False,
        readonly=True,
    )
    ff_commercial_packaging_qty = fields.Float(
        string='Commercial Packaging Qty',
        digits='Product Unit',
        copy=False,
        readonly=True,
        help="Number of base units inside one packaging (snapshot).",
    )
    ff_commercial_packaging_count = fields.Float(
        string='Commercial Packaging Count',
        digits='Product Unit',
        copy=False,
        readonly=True,
        help="Number of packagings sold (commercial quantity shown to the customer).",
    )
