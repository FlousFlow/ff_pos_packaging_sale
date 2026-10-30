# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _prepare_stock_move_vals(self, first_line, order_lines):
        """ POS pickings: convert the commercial packaging count to the product
        base UoM. The move keeps the base uom; only the quantity is converted
        (2 Carton x 24 => 48 Units), so valuation / FIFO / AVCO stay standard.
        """
        vals = super()._prepare_stock_move_vals(first_line, order_lines)
        vals['product_uom_qty'] = abs(sum(line._ff_stock_qty() for line in order_lines))
        return vals


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
        """ Lot-tracked branch: core assigns `abs(line.qty)` (commercial count)
        per lot. We must assign the converted base-UoM quantity instead.
        (Copy of core method with the quantity source changed.) """
        lines_data = self._prepare_lines_data_dict(related_order_lines)
        # Moves with product_id not in related_order_lines. This can happen e.g.
        # when product_id has a phantom-type bom.
        moves_to_assign = self.filtered(
            lambda m: m.product_id.id not in lines_data
            or m.product_id.tracking == 'none'
            or (not m.picking_type_id.use_existing_lots and not m.picking_type_id.use_create_lots)
        )

        # Check for any conversion issues in the moves before setting quantities
        uoms_with_issues = set()
        for move in moves_to_assign.filtered(
            lambda m: m.product_uom_qty and m.product_uom != m.product_id.uom_id
        ):
            converted_qty = move.product_uom._compute_quantity(
                move.product_uom_qty,
                move.product_id.uom_id,
                rounding_method='HALF-UP'
            )
            if not converted_qty:
                uoms_with_issues.add(
                    (move.product_uom.name, move.product_id.uom_id.name)
                )

        if uoms_with_issues:
            error_message_lines = [
                _("Conversion Error: The following unit of measure conversions result "
                  "in a zero quantity due to rounding:")
            ]
            for uom_from, uom_to in uoms_with_issues:
                error_message_lines.append(
                    _(' - From "%(uom_from)s" to "%(uom_to)s"',
                      uom_from=uom_from, uom_to=uom_to)
                )
            error_message_lines.append(
                _("\nThis issue occurs because the quantity becomes zero after rounding "
                  "during the conversion. To fix this, adjust the conversion factors or "
                  "rounding method to ensure that even the smallest quantity in the "
                  "original unit does not round down to zero in the target unit.")
            )
            raise UserError('\n'.join(error_message_lines))

        for move in moves_to_assign:
            move.quantity = move.product_uom_qty
        moves_remaining = self - moves_to_assign
        existing_lots = moves_remaining._create_production_lots_for_pos_order(related_order_lines)
        move_lines_to_create = []
        if are_qties_done:
            for move in moves_remaining:
                move.move_line_ids.unlink()
                for line in lines_data[move.product_id.id]['order_lines']:
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        # FF: base-UoM quantity per lot (commercial count x contained qty)
                        qty = (
                            1
                            if line.product_id.tracking == 'serial'
                            else abs(line._ff_stock_qty())
                        )
                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([
                                ('product_id', '=', line.product_id.id),
                                ('name', '=', lot.lot_name),
                            ])
                            quants = self.env['stock.quant']
                            if existing_lot:
                                quants = self.env['stock.quant'].search(
                                    [('lot_id', '=', existing_lot.id), ('quantity', '>', '0.0'),
                                     ('location_id', 'child_of', move.location_id.id)],
                                    order='id desc',
                                )
                            qty_left_to_assign = qty
                            for quant in quants:
                                if qty_left_to_assign <= 0:
                                    break
                                qty_chg = min(qty_left_to_assign, quant.quantity)
                                ml_vals = dict(move._prepare_move_line_vals(qty_chg))
                                qty_left_to_assign -= qty_chg
                                ml_vals.update({
                                    'quant_id': quant.id,
                                })
                                move_lines_to_create.append(ml_vals)
                            if qty_left_to_assign > 0:
                                ml_vals = dict(move._prepare_move_line_vals(qty_left_to_assign))
                                ml_vals.update({
                                    'lot_name': existing_lot.name,
                                    'lot_id': existing_lot.id,
                                })
                                move_lines_to_create.append(ml_vals)
                        else:
                            ml_vals = dict(move._prepare_move_line_vals(qty))
                            ml_vals.update({'lot_name': lot.lot_name})
                            move_lines_to_create.append(ml_vals)

            self.env['stock.move.line'].create(move_lines_to_create)
        else:
            for move in moves_remaining:
                for line in lines_data[move.product_id.id]['order_lines']:
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        if line.product_id.tracking == 'serial':
                            qty = 1
                        else:
                            # FF: base-UoM quantity per lot
                            qty = abs(line._ff_stock_qty())
                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([
                                ('product_id', '=', line.product_id.id),
                                ('name', '=', lot.lot_name),
                            ])
                            if existing_lot:
                                move._update_reserved_quantity(qty, move.location_id, lot_id=existing_lot)
                                continue
