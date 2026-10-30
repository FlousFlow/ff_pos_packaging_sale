# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_account_move_line_data_from_base_line(self, base_lines):
        vals_list = super()._prepare_account_move_line_data_from_base_line(base_lines)
        for vals in vals_list:
            line = vals.get('metadata', {}).get('line')
            if line and (line.ff_packaging_id or line.ff_packaging_uom_id):
                vals['account.move.line'].update({
                    'ff_pos_packaging_id': line.ff_packaging_id.id or False,
                    'ff_pos_packaging_uom_id': line.ff_packaging_uom_id.id or False,
                    'ff_commercial_packaging_qty': line.ff_packaging_qty,
                    'ff_commercial_packaging_count': line.qty,
                })
        return vals_list


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    ff_packaging_id = fields.Many2one(
        'product.uom', string='Packaging', copy=True, index='btree_not_null',
        ondelete='restrict', help="Commercial packaging the customer bought.",
    )
    ff_packaging_uom_id = fields.Many2one(
        'uom.uom', string='Packaging UoM', copy=True, index='btree_not_null',
        ondelete='restrict', help="Standard product packaging UoM selected in POS.",
    )
    ff_packaging_name = fields.Char(string='Packaging Name', copy=True)
    ff_packaging_qty = fields.Float(string='Packaging Contained Qty', digits='Product Unit', copy=True)
    ff_packaging_count = fields.Float(
        string='Packaging Count', digits='Product Unit', compute='_compute_ff_packaging_count',
        store=True, readonly=False, copy=True,
    )
    ff_packaging_unit_price = fields.Float(string='Packaging Unit Price', digits='Product Price', copy=True)
    ff_base_uom_qty = fields.Float(
        string='Base UoM Quantity', compute='_compute_ff_base_uom_qty', store=True,
        digits='Product Unit',
    )

    @api.depends('qty', 'ff_packaging_qty', 'ff_packaging_id', 'ff_packaging_uom_id')
    def _compute_ff_base_uom_qty(self):
        for line in self:
            line.ff_base_uom_qty = line._ff_stock_qty()

    @api.depends('qty', 'ff_packaging_id', 'ff_packaging_uom_id')
    def _compute_ff_packaging_count(self):
        for line in self:
            line.ff_packaging_count = abs(line.qty) if (line.ff_packaging_id or line.ff_packaging_uom_id) else line.qty

    def _ff_stock_qty(self):
        self.ensure_one()
        if (self.ff_packaging_id or self.ff_packaging_uom_id) and self.ff_packaging_qty:
            return self.qty * self.ff_packaging_qty
        return self.qty

    @api.constrains('ff_packaging_id', 'ff_packaging_uom_id', 'product_id')
    def _check_ff_packaging_product(self):
        for line in self:
            if line.ff_packaging_id and line.ff_packaging_id.product_id != line.product_id:
                raise ValidationError(_("Packaging %(packaging)s does not belong to product %(product)s.",
                                        packaging=line.ff_packaging_id.display_name,
                                        product=line.product_id.display_name))
            if line.ff_packaging_uom_id and line.ff_packaging_uom_id not in line.product_id.product_tmpl_id.uom_ids:
                raise ValidationError(_("Packaging UoM %(packaging)s is not configured on product %(product)s.",
                                        packaging=line.ff_packaging_uom_id.display_name,
                                        product=line.product_id.display_name))

    @api.constrains('ff_packaging_id', 'ff_packaging_uom_id', 'ff_packaging_count', 'ff_packaging_qty')
    def _check_ff_packaging_data(self):
        for line in self:
            if (line.ff_packaging_id or line.ff_packaging_uom_id) and (line.ff_packaging_count <= 0 or line.ff_packaging_qty <= 0):
                raise ValidationError(_("Packaging count and contained quantity must be strictly positive."))

    @api.model
    def _load_pos_data_fields(self, config):
        loaded_fields = super()._load_pos_data_fields(config)
        packaging_fields = [
            'ff_packaging_id', 'ff_packaging_uom_id', 'ff_packaging_name', 'ff_packaging_qty',
            'ff_packaging_count', 'ff_packaging_unit_price',
        ]
        extra_fields = [field for field in packaging_fields if field not in loaded_fields]
        return loaded_fields + extra_fields

    @api.model
    def _load_pos_data_dependencies(self):
        return ['pos.order']

    def _prepare_refund_data(self, refund_order):
        vals = super()._prepare_refund_data(refund_order)
        if self.ff_packaging_id or self.ff_packaging_uom_id:
            vals.update({
                'ff_packaging_id': self.ff_packaging_id.id or False,
                'ff_packaging_uom_id': self.ff_packaging_uom_id.id or False,
                'ff_packaging_name': self.ff_packaging_name,
                'ff_packaging_qty': self.ff_packaging_qty,
                'ff_packaging_count': abs(self.qty - self.refunded_qty) or abs(self.qty),
                'ff_packaging_unit_price': self.ff_packaging_unit_price,
            })
        return vals

    def _get_qty_to_move(self):
        self.ensure_one()
        qty = super()._get_qty_to_move()
        if self.ff_packaging_id or self.ff_packaging_uom_id:
            factor = self.ff_packaging_qty or 1.0
            # pos_sale_stock returns a quantity in the commercial UoM; preserve
            # any outstanding-delivery cap, then convert it to the base UoM.
            return qty * factor
        return qty

    def _get_product_cost(self, at_closing=False):
        cost = super()._get_product_cost(at_closing)
        if self.ff_packaging_id or self.ff_packaging_uom_id:
            return cost * (self.ff_packaging_qty or 1.0)
        return cost
