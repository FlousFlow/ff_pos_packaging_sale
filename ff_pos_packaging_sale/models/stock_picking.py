# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_lot_line_qty(self, line, move, lines_data):
        if line.product_id.tracking == 'serial':
            return 1
        return abs(line._ff_stock_qty())
