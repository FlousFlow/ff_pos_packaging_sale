# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductUom(models.Model):
    """ Odoo 19 packaging model (product-specific UoM barcodes) extended for POS sale. """
    _inherit = 'product.uom'

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
        help="Fixed selling price for ONE packaging in POS (e.g. Carton = 300). "
             "If empty, the fallback price is: contained quantity x unit price.",
    )
    ff_is_default_pos_packaging = fields.Boolean(
        string='Default in POS',
        help="Added automatically when the product barcode is scanned, "
             "if the product behavior is 'Default Packaging'.",
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

    @api.constrains('ff_is_default_pos_packaging', 'ff_available_in_pos', 'product_id')
    def _check_ff_pos_packaging(self):
        for packaging in self:
            if packaging.ff_is_default_pos_packaging:
                if not packaging.ff_available_in_pos:
                    raise ValidationError(_(
                        "Packaging %(name)s cannot be the default POS packaging "
                        "because it is not available in POS.",
                        name=packaging.ff_pos_name or packaging.barcode,
                    ))
                same_product_defaults = packaging.product_id.product_uom_ids.filtered(
                    lambda p: p.ff_is_default_pos_packaging
                )
                if len(same_product_defaults) > 1:
                    raise ValidationError(_(
                        "Product %(product)s can only have one default POS packaging.",
                        product=packaging.product_id.display_name,
                    ))

    @api.constrains('uom_id', 'product_id')
    def _check_ff_uom(self):
        """ In v19 uom.uom is a relative-factor tree (no categories): guard
        against zero/invalid conversion instead. """
        for packaging in self:
            if packaging.ff_contained_qty <= 0:
                raise ValidationError(_(
                    "Packaging %(name)s must contain a strictly positive "
                    "quantity of the product base unit.",
                    name=packaging.ff_pos_name or packaging.barcode,
                ))

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + [
            'ff_available_in_pos', 'ff_pos_name', 'ff_pos_price',
            'ff_is_default_pos_packaging', 'ff_sequence', 'ff_contained_qty',
        ]
        # NOTE: the loading domain is intentionally NOT narrowed to
        # ff_available_in_pos — core POS resolves packaging barcodes
        # (product.uom records) during scans and expects them to be loaded.
