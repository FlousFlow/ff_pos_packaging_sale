# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from itertools import groupby

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_invoice_lines_values(self, line_values, pos_line, move_type):
        vals = super()._get_invoice_lines_values(line_values, pos_line, move_type)
        if (pos_line.ff_packaging_id or pos_line.ff_packaging_uom_id) and vals.get('display_type') != 'line_section':
            vals.update({
                'ff_pos_packaging_id': pos_line.ff_packaging_id.id if pos_line.ff_packaging_id else False,
                'ff_pos_packaging_uom_id': pos_line.ff_packaging_uom_id.id if pos_line.ff_packaging_uom_id else False,
                'ff_commercial_packaging_qty': pos_line.ff_packaging_qty,
                'ff_commercial_packaging_count': pos_line.qty,
            })
        return vals


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # ---- Commercial packaging data (structured, survives sync & reload) ----
    ff_packaging_id = fields.Many2one(
        comodel_name='product.uom',
        string='Packaging',
        copy=True,
        index='btree_not_null',
        ondelete='restrict',
        help="Commercial packaging the customer bought (e.g. Carton).",
    )
    ff_packaging_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Packaging UoM',
        copy=True,
        index='btree_not_null',
        ondelete='restrict',
        help="Standard product packaging UoM selected in POS.",
    )
    ff_packaging_name = fields.Char(
        string='Packaging Name',
        copy=True,
        help="Snapshot of the commercial packaging name (receipt/invoice resilience).",
    )
    ff_packaging_qty = fields.Float(
        string='Packaging Contained Qty',
        digits='Product Unit',
        copy=True,
        help="Snapshot of the number of base units inside one packaging.",
    )
    ff_packaging_count = fields.Float(
        string='Packaging Count',
        digits='Product Unit',
        compute='_compute_ff_packaging_count',
        store=True,
        readonly=False,
        copy=True,
        help="Number of packagings sold (commercial quantity, always positive). "
             "Always kept equal to abs(qty) so reports stay consistent.",
    )
    ff_packaging_unit_price = fields.Float(
        string='Packaging Unit Price',
        digits='Product Price',
        copy=True,
        help="Price of ONE packaging (e.g. Carton = 300).",
    )
    ff_base_uom_qty = fields.Float(
        string='Base UoM Quantity',
        compute='_compute_ff_base_uom_qty',
        store=True,
        digits='Product Unit',
        help="Inventory quantity in the product base UoM: "
             "packaging_count x packaging_contained_qty.",
    )

    @api.depends('qty', 'ff_packaging_qty', 'ff_packaging_id', 'ff_packaging_uom_id')
    def _compute_ff_base_uom_qty(self):
        for line in self:
            line.ff_base_uom_qty = line._ff_stock_qty()

    @api.depends('qty', 'ff_packaging_id', 'ff_packaging_uom_id')
    def _compute_ff_packaging_count(self):
        for line in self:
            line.ff_packaging_count = (
                abs(line.qty) if (line.ff_packaging_id or line.ff_packaging_uom_id) else line.qty
            )

    def _ff_stock_qty(self):
        """ Inventory quantity in the product base UoM for this line.

        Commercial quantity (qty = packaging count) and stock quantity are
        deliberately separated: the stock movement is converted here, once,
        at the stock boundary — everything else (taxes, invoice, reports)
        keeps using the commercial quantity and the packaging price.
        """
        self.ensure_one()
        if (self.ff_packaging_id or self.ff_packaging_uom_id) and self.ff_packaging_qty:
            return self.qty * self.ff_packaging_qty
        return self.qty

    # ---- Constraints ----
    @api.constrains('ff_packaging_id', 'ff_packaging_uom_id', 'product_id')
    def _check_ff_packaging_product(self):
        for line in self:
            if line.ff_packaging_id and line.ff_packaging_id.product_id != line.product_id:
                raise ValidationError(_(
                    "Packaging %(packaging)s does not belong to product %(product)s.",
                    packaging=line.ff_packaging_id.display_name,
                    product=line.product_id.display_name,
                ))
            if line.ff_packaging_uom_id and line.ff_packaging_uom_id not in line.product_id.product_tmpl_id.uom_ids:
                raise ValidationError(_(
                    "Packaging UoM %(packaging)s is not configured on product %(product)s.",
                    packaging=line.ff_packaging_uom_id.display_name,
                    product=line.product_id.display_name,
                ))

    @api.constrains('ff_packaging_id', 'ff_packaging_uom_id', 'ff_packaging_count', 'ff_packaging_qty')
    def _check_ff_packaging_data(self):
        for line in self:
            if line.ff_packaging_id or line.ff_packaging_uom_id:
                if line.ff_packaging_count <= 0:
                    raise ValidationError(_(
                        "The packaging count must be strictly positive."
                    ))
                if line.ff_packaging_qty <= 0:
                    raise ValidationError(_(
                        "The packaging contained quantity must be strictly positive."
                    ))

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + [
            'ff_packaging_id', 'ff_packaging_uom_id', 'ff_packaging_name', 'ff_packaging_qty',
            'ff_packaging_count', 'ff_packaging_unit_price',
        ]

    def _prepare_refund_data(self, refund_order, PosPackOperationLot):
        vals = super()._prepare_refund_data(refund_order, PosPackOperationLot)
        if self.ff_packaging_id or self.ff_packaging_uom_id:
            vals.update({
                'ff_packaging_id': self.ff_packaging_id.id if self.ff_packaging_id else False,
                'ff_packaging_uom_id': self.ff_packaging_uom_id.id if self.ff_packaging_uom_id else False,
                'ff_packaging_name': self.ff_packaging_name,
                'ff_packaging_qty': self.ff_packaging_qty,
                # commercial count stays positive; the refund sign lives in qty
                'ff_packaging_count': abs(self.qty - self.refunded_qty) or abs(self.qty),
                'ff_packaging_unit_price': self.ff_packaging_unit_price,
            })
        return vals

    def _launch_stock_rule_from_pos_order_lines(self):
        """ Shipping-date path: convert commercial quantity to base UoM before
        running the stock rules. (Copy of core with product_qty conversion.) """
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.product_id.type != 'consu':
                continue

            reference_ids = line.order_id.stock_reference_ids
            if not reference_ids:
                reference_ids = self.env['stock.reference'].create(
                    line._prepare_reference_vals()
                )
                line.order_id.stock_reference_ids = [
                    fields.Command.set(reference_ids.ids)
                ]

            values = line._prepare_procurement_values()
            product_qty = line._ff_stock_qty()  # FF: commercial -> base UoM

            procurement_uom = line.product_id.uom_id
            procurements.append(self.env['stock.rule'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values)
            )
        if procurements:
            self.env['stock.rule'].run(procurements)

        # This next block is currently needed only because the scheduler trigger
        # is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                tracked_lines = order.lines.filtered(
                    lambda l: l.product_id.tracking != 'none'
                )
                lines_by_tracked_product = groupby(
                    sorted(tracked_lines, key=lambda l: l.product_id.id),
                    key=lambda l: l.product_id.id,
                )
                pickings_to_confirm.action_confirm()
                for product_id, lines in lines_by_tracked_product:
                    lines = self.env['pos.order.line'].concat(*lines)
                    moves = pickings_to_confirm.move_ids.filtered(
                        lambda m: m.product_id.id == product_id
                    )
                    moves.move_line_ids.unlink()
                    moves._add_mls_related_to_order(lines, are_qties_done=False)
                    moves._recompute_state()
        return True

    def _compute_total_cost(self, stock_moves):
        """ Margin/cost must be based on the inventory quantity (base UoM),
        not the commercial packaging count. (Copy of core with qty conversion.) """
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            product = line.product_id
            cost_currency = product.sudo().cost_currency_id
            moves = (
                line._get_stock_moves_to_consider(stock_moves, product)
                if stock_moves else None
            )
            if moves and line._is_product_storable_fifo_avco():
                product_cost = line._get_product_cost_with_moves(moves)
                if cost_currency.is_zero(product_cost) and line.order_id.shipping_date:
                    if line.refunded_orderline_id:
                        product_cost = (
                            line.refunded_orderline_id.total_cost
                            / line.refunded_orderline_id._ff_stock_qty()
                        )
                    else:
                        product_cost = product.standard_price
            else:
                product_cost = product.standard_price
            line.total_cost = line._ff_stock_qty() * cost_currency._convert(  # FF
                from_amount=product_cost,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            )
            line.is_total_cost_computed = True
