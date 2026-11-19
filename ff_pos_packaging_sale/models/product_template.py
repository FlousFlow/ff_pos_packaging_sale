# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ff_packaging_barcodes = fields.Char(compute='_compute_ff_packaging_barcodes')

    @api.depends('uom_ids')
    def _compute_ff_packaging_barcodes(self):
        for product in self:
            barcodes = self.env['product.uom'].search([
                ('product_id', 'in', product.product_variant_ids.ids),
            ]).mapped('barcode')
            product.ff_packaging_barcodes = ' '.join(filter(None, barcodes))

    @api.model
    def web_name_search(self, name, specification, domain=None, operator='ilike', limit=100):
        """Find product templates by barcode on their product-specific packaging."""
        records = super().web_name_search(name, specification, domain, operator, limit)
        if not name:
            return records
        packaging = self.env['product.uom'].sudo().search([
            ('barcode', '=', name), ('product_id', '!=', False),
        ])
        templates = packaging.mapped('product_id.product_tmpl_id').filtered_domain(list(domain or []))
        existing_ids = {record['id'] for record in records}
        extra = templates.filtered(lambda product: product.id not in existing_ids)[:max(limit - len(records), 0)]
        if extra:
            extra_values = extra.web_read(specification)
            for values, product in zip(extra_values, extra):
                if 'display_name' in specification:
                    values['__formatted_display_name'] = product.with_context(
                        formatted_display_name=True
                    ).display_name
            records.extend(extra_values)
        return records

    @api.model
    def _load_pos_data_fields(self, config):
        loaded_fields = super()._load_pos_data_fields(config)
        fields_to_load = list(loaded_fields)
        for field_name in ('uom_ids', 'ff_packaging_barcodes'):
            if field_name not in fields_to_load:
                fields_to_load.append(field_name)
        return fields_to_load

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.combo', 'pos.category', 'account.tax']


class UomUom(models.Model):
    _inherit = 'uom.uom'

    @api.model
    def _load_pos_data_fields(self, config):
        loaded_fields = super()._load_pos_data_fields(config)
        return loaded_fields if 'sequence' in loaded_fields else loaded_fields + ['sequence']

    @api.model
    def _load_pos_data_domain(self, data):
        template_ids = data['product.template'].ids
        templates = self.env['product.template'].browse(template_ids)
        return [('id', 'in', (templates.uom_ids | templates.uom_id).ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.template']
