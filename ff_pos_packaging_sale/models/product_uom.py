# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductUom(models.Model):
    """Product-specific barcode packaging extended for POS sale."""
    _inherit = 'product.uom'

    @api.model
    def _load_pos_data_domain(self, data):
        return [('product_id', 'in', data['product.product'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.product']

    ff_available_in_pos = fields.Boolean(
        string='Available in POS',
        help="Sell this packaging in the Point of Sale as a commercial unit.",
    )
    ff_pos_name = fields.Char(
        string='POS Name',
        help="Commercial name shown to the customer in POS/receipt/invoice (e.g. Carton). "
             "If empty, the packaging UoM name is used.",
    )
    ff_pos_price = fields.Float(
        string='POS Price',
        digits='Product Price',
        help="Legacy value retained for compatibility. POS package prices are now calculated "
             "from the product sale price or applicable quantity-based pricelist rule.",
    )
    ff_sequence = fields.Integer(string='Sequence', default=10)
    ff_contained_qty = fields.Float(
        string='Contained Quantity',
        compute='_compute_ff_contained_qty',
        digits='Product Unit',
        help="Number of base units inside one packaging.",
    )
    ff_pos_display_name = fields.Char(
        string='POS Display Name',
        compute='_compute_ff_pos_display_name',
        help="Commercial name used on receipts and invoices (ff_pos_name or UoM name).",
    )

    _ff_pos_price_non_negative = models.Constraint(
        'CHECK (ff_pos_price >= 0)',
        'The POS price of a packaging cannot be negative.',
    )

    @api.depends('uom_id.factor', 'product_id.uom_id.factor')
    def _compute_ff_contained_qty(self):
        for packaging in self:
            base_factor = packaging.product_id.uom_id.factor
            packaging.ff_contained_qty = (
                packaging.uom_id.factor / base_factor if base_factor else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_ff_uom()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'product_id', 'uom_id'} & vals.keys():
            self._check_ff_uom()
        return result

    @api.depends('ff_pos_name', 'uom_id.name')
    def _compute_ff_pos_display_name(self):
        for packaging in self:
            packaging.ff_pos_display_name = packaging.ff_pos_name or packaging.uom_id.name

    @api.depends('ff_pos_name', 'uom_id.name')
    def _compute_display_name(self):
        """ Show the commercial POS name when set, even without show_variant_name. """
        super()._compute_display_name()
        for packaging in self:
            if packaging.ff_pos_name:
                packaging.display_name = packaging.ff_pos_name

    @api.constrains('ff_pos_price')
    def _check_ff_pos_price(self):
        for packaging in self:
            if packaging.ff_pos_price < 0:
                raise ValidationError(_("The POS price of a packaging cannot be negative."))

    @api.constrains('uom_id', 'product_id')
    def _check_ff_uom(self):
        """Ensure each barcode packaging converts to a positive base quantity."""
        for packaging in self:
            if packaging.ff_contained_qty <= 0:
                raise ValidationError(_(
                    "Packaging %(name)s must contain a strictly positive "
                    "quantity of the product base unit.",
                    name=packaging.ff_pos_name or packaging.barcode,
                ))

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'barcode', 'product_id', 'uom_id', 'ff_available_in_pos',
                'ff_pos_name', 'ff_sequence', 'ff_contained_qty']
