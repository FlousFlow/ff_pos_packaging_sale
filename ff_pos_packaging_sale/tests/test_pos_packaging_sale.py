# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosPackagingSale(TestPoSCommon):

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))

        # --- Unit of measures ---
        uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_box6 = self.env['uom.uom'].create({
            'name': 'Box of 6',
            'relative_factor': 6,
            'relative_uom_id': uom_unit.id,
        })
        self.uom_carton24 = self.env['uom.uom'].create({
            'name': 'Carton of 24',
            'relative_factor': 24,
            'relative_uom_id': uom_unit.id,
        })

        # --- Products ---
        self.product_pepsi = self.env['product.product'].create({
            'name': 'Pepsi Can',
            'is_storable': True,
            'list_price': 15.0,
            'standard_price': 8.0,
            'barcode': '123456789',
            'available_in_pos': True,
            'uom_id': uom_unit.id,
        })
        self.product_plain = self.env['product.product'].create({
            'name': 'Plain Product (no packaging)',
            'is_storable': False,
            'list_price': 10.0,
            'available_in_pos': True,
            'uom_id': uom_unit.id,
        })

        # --- Packagings ---
        self.packaging_box = self.env['product.uom'].create({
            'product_id': self.product_pepsi.id,
            'uom_id': self.uom_box6.id,
            'barcode': 'FFBOX0000001',
            'ff_available_in_pos': True,
            'ff_pos_name': 'Box',
            'ff_pos_price': 80.0,
            'ff_sequence': 5,
        })
        self.packaging_carton = self.env['product.uom'].create({
            'product_id': self.product_pepsi.id,
            'uom_id': self.uom_carton24.id,
            'barcode': 'FFCARTON00001',
            'ff_available_in_pos': True,
            'ff_pos_name': 'Carton',
            'ff_pos_price': 290.0,
            'ff_sequence': 10,
        })

        self.pos_config = self.config
        self.pos_config.write({'payment_method_ids': [Command.set(self.cash_pm1.ids)]})
        self.session = self.open_new_session()

        # 14% VAT on the packaging price
        self.tax_14 = self.env['account.tax'].create({
            'name': 'VAT 14%',
            'amount_type': 'percent',
            'amount': 14.0,
            'type_tax_use': 'sale',
            'company_id': self.env.company.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _order_line_vals(self, product, packaging=None, count=0, price=None, taxes=None):
        unit_price = price if price is not None else (
            packaging.ff_pos_price if packaging else product.list_price
        )
        subtotal = unit_price * count
        vals = {
            'product_id': product.id,
            'qty': count,
            'price_unit': unit_price,
            'price_subtotal': subtotal,
            'price_subtotal_incl': subtotal,
            'uuid': str(uuid.uuid4()),
        }
        if taxes:
            vals.update({
                'tax_ids': [Command.set(taxes.ids)],
                'price_subtotal_incl': subtotal * (1 + taxes.amount / 100.0),
            })
        if packaging:
            vals.update({
                'ff_packaging_id': packaging.id,
                'ff_packaging_name': packaging.ff_pos_name,
                'ff_packaging_qty': packaging.ff_contained_qty,
                'ff_packaging_count': abs(count),
                'ff_packaging_unit_price': vals['price_unit'],
            })
        return vals

    def _create_order(self, lines, to_invoice=False):
        payment_method = self.pos_config.payment_method_ids[0]
        total = sum(
            (line['price_unit'] * line['qty'])
            for line in lines
        )
        order = self.env['pos.order'].create({
            'session_id': self.session.id,
            'company_id': self.env.company.id,
            'lines': [Command.create(line) for line in lines],
            'payment_ids': [Command.create({
                'payment_method_id': payment_method.id,
                'amount': total,
                'uuid': str(uuid.uuid4()),
            })],
            # stored required columns are filled before the price compute runs
            'amount_paid': total,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': total,
            'to_invoice': to_invoice,
            'is_total_cost_computed': False,
            'uuid': str(uuid.uuid4()),
        })
        return order

    # ------------------------------------------------------------------
    # TEST 1 — Sell 2 cartons: commercial qty = 2, stock qty = 48
    # ------------------------------------------------------------------
    def test_01_two_cartons_stock_conversion(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 2)
        ])
        self.action_paid(order)
        line = order.lines
        self.assertEqual(line.qty, 2, "commercial count stays 2 Cartons")
        self.assertEqual(line.ff_base_uom_qty, 48, "2 x 24 = 48 base units")
        self.assertTrue(order.picking_ids)
        move = order.picking_ids.move_ids
        self.assertEqual(move.product_uom_qty, 48, "stock move takes 48 Units")
        self.assertEqual(move.uom_id.id, self.product_pepsi.uom_id.id,
                         "stock move stays in the base UoM")

    def action_paid(self, order):
        order.action_pos_order_paid()
        order._create_order_picking()

    # ------------------------------------------------------------------
    # TEST 2 — Receipt data: commercial name present, never raw units
    # ------------------------------------------------------------------
    def test_02_receipt_shows_packaging(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 2)
        ])
        line = order.lines
        self.assertEqual(line.ff_packaging_name, 'Carton')
        # The receipt renders line.qty (2) + ff_packaging_name ("Carton")
        # — verify the data the JS template consumes:
        self.assertEqual(line.qty, 2)
        self.assertIn('Carton', line.ff_packaging_name)

    # ------------------------------------------------------------------
    # TEST 3 — Invoice from POS: structured packaging data
    # ------------------------------------------------------------------
    def test_03_invoice_packaging_fields(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 2)
        ])
        self.action_paid(order)
        base_lines = order.lines._prepare_base_lines_for_taxes_computation()
        self.env['account.tax']._add_tax_details_in_base_lines(base_lines, order.company_id)
        self.env['account.tax']._round_base_lines_tax_details(base_lines, order.company_id)
        self.env['account.tax']._add_accounting_data_in_base_lines_tax_details(
            base_lines, order.company_id, include_caba_tags=True,
        )
        invoice_vals_list = order._prepare_account_move_line_data_from_base_line(base_lines)
        product_line_data = [
            v['account.move.line'] for v in invoice_vals_list
            if v['account.move.line'].get('display_type', 'product') == 'product'
        ][0]
        self.assertEqual(product_line_data['quantity'], 2,
                         "invoice quantity = commercial count")
        self.assertEqual(product_line_data['price_unit'], 290.0,
                         "invoice price = packaging price")
        self.assertEqual(product_line_data['ff_pos_packaging_id'], self.packaging_carton.id)
        self.assertEqual(product_line_data['ff_commercial_packaging_count'], 2)
        self.assertEqual(product_line_data['ff_commercial_packaging_qty'], 24)

    # ------------------------------------------------------------------
    # TEST 4 — Refund 1 carton => +24 units back
    # ------------------------------------------------------------------
    def test_04_refund_keeps_packaging(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 2)
        ])
        self.action_paid(order)
        refund_orders = order._refund()
        refund_line = refund_orders.lines
        # partial refund through the UI edits the qty before payment:
        # refund only 1 of the 2 cartons
        refund_line.qty = -1
        refund_orders._compute_prices()
        self.assertEqual(refund_line.qty, -1, "refund shows -1 Carton")
        self.assertEqual(refund_line.ff_packaging_id.id, self.packaging_carton.id)
        self.assertEqual(refund_line.ff_base_uom_qty, -24,
                         "stock side returns 24 units")
        refund_orders._create_order_picking()
        return_move = refund_orders.picking_ids.move_ids
        self.assertEqual(return_move.product_uom_qty, 24)

    # ------------------------------------------------------------------
    # TEST 5 — Packaging price independence (Carton 290 != 24 x 15 = 360)
    # ------------------------------------------------------------------
    def test_05_packaging_price_independent(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 1)
        ])
        order._compute_prices()
        line = order.lines
        self.assertEqual(line.price_unit, 290.0)
        self.assertEqual(line.price_subtotal, 290.0,
                         "total is the packaging price, not 24 x unit price")

    # ------------------------------------------------------------------
    # TEST 6 — Barcode uniqueness of packaging (data side of scanning)
    # ------------------------------------------------------------------
    def test_06_packaging_barcode_unique(self):
        with self.assertRaises(ValidationError):
            self.env['product.uom'].create({
                'product_id': self.product_pepsi.id,
                'uom_id': self.uom_box6.id,
                'barcode': self.product_pepsi.barcode,  # product barcode
            })

    # ------------------------------------------------------------------
    # TEST 7 — Product without packaging: standard behavior untouched
    # ------------------------------------------------------------------
    def test_07_plain_product_untouched(self):
        order = self._create_order([
            self._order_line_vals(self.product_plain, None, 3)
        ])
        self.action_paid(order)
        line = order.lines
        self.assertFalse(line.ff_packaging_id)
        self.assertEqual(line.ff_base_uom_qty, 3)
        move = order.picking_ids.move_ids
        self.assertEqual(move.product_uom_qty, 3)

    # ------------------------------------------------------------------
    # TEST 8 — Packaging fields survive POS data loading (sync/reload)
    # ------------------------------------------------------------------
    def test_08_fields_in_pos_data_loading(self):
        loaded = self.env['pos.order.line']._load_pos_data_fields(self.pos_config)
        for field in ('ff_packaging_id', 'ff_packaging_name', 'ff_packaging_qty',
                      'ff_packaging_count', 'ff_packaging_unit_price'):
            self.assertIn(field, loaded)
        pkg_loaded = self.env['product.uom']._load_pos_data_fields(self.pos_config)
        for field in ('ff_available_in_pos', 'ff_pos_price', 'ff_pos_name',
                      'ff_sequence', 'ff_contained_qty'):
            self.assertIn(field, pkg_loaded)
        tmpl_loaded = self.env['product.template']._load_pos_data_fields(self.pos_config)
        for field in ('uom_ids',):
            self.assertIn(field, tmpl_loaded)

    # ------------------------------------------------------------------
    # TEST 9 — Taxes on packaging price (Carton 290 + 14% = 330.60)
    # ------------------------------------------------------------------
    def test_09_taxes_on_packaging_price(self):
        self.product_pepsi.taxes_id = [Command.set(self.tax_14.ids)]
        order = self._create_order([
            self._order_line_vals(
                self.product_pepsi, self.packaging_carton, 1,
                taxes=self.tax_14,
            )
        ])
        order._compute_prices()
        line = order.lines
        self.assertEqual(line.price_subtotal, 290.0)
        self.assertAlmostEqual(line.price_subtotal_incl, 330.60, places=3,
                               msg="290 + 14% VAT = 330.60 (tax on packaging price)")
        # tax base must be 290 (packaging price), never 24 x 15
        base_lines = line._prepare_base_lines_for_taxes_computation()
        self.assertEqual(sum(bl['price_unit'] * bl['quantity'] for bl in base_lines), 290.0)
        self.product_pepsi.taxes_id = [Command.clear()]

    # ------------------------------------------------------------------
    # TEST 10 — Multiple packagings: each converts with its own ratio
    # ------------------------------------------------------------------
    def test_10_multiple_packagings(self):
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_box, 3),
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 2),
        ])
        self.action_paid(order)
        by_pkg = {l.ff_packaging_id.id: l for l in order.lines}
        self.assertEqual(by_pkg[self.packaging_box.id]._ff_stock_qty(), 18)   # 3 x 6
        self.assertEqual(by_pkg[self.packaging_carton.id]._ff_stock_qty(), 48)  # 2 x 24
        move = order.picking_ids.move_ids
        self.assertEqual(move.product_uom_qty, 66, "18 + 48 = 66 units in one move")

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    def test_constraints(self):
        with self.assertRaises(ValidationError):
            self.packaging_box.ff_pos_price = -5
        # packaging must belong to the product of the line
        other = self.env['product.product'].create({
            'name': 'Other', 'type': 'consu', 'available_in_pos': True,
        })
        other_pkg = self.env['product.uom'].create({
            'product_id': other.id,
            'uom_id': self.uom_box6.id,
            'barcode': 'FFOTHER00001',
            'ff_available_in_pos': True,
        })
        order = self._create_order([
            self._order_line_vals(self.product_pepsi, self.packaging_carton, 1)
        ])
        with self.assertRaises(ValidationError):
            order.lines.ff_packaging_id = other_pkg.id
