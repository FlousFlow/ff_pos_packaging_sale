# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_fields(self, config):
        loaded_fields = super()._load_pos_data_fields(config)
        return loaded_fields if 'uom_ids' in loaded_fields else loaded_fields + ['uom_ids']

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
