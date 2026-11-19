# Part of Flous Flow. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Resolve a product when the scanned value is a packaging barcode."""
        args = list(args or [])
        result = super().name_search(name, args, operator, limit)
        if not name:
            return result
        packaging_ids = self.env["product.uom"].sudo().search([
            ("barcode", "=", name), ("product_id", "!=", False),
        ]).mapped("product_id").ids
        if not packaging_ids:
            return result
        existing_ids = {record_id for record_id, _label in result}
        products = self.browse(packaging_ids).filtered(lambda product: product.id not in existing_ids)
        remaining = max(limit - len(result), 0) if limit else len(products)
        return result + [(product.id, product.display_name) for product in products[:remaining]]

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        """Include packaging barcode matches in the web product autocomplete."""
        records = super().web_name_search(name, specification, domain, operator, limit)
        if not name:
            return records
        product_domain = list(domain or [])
        packaging = self.env["product.uom"].sudo().search([
            ("barcode", "=", name), ("product_id", "!=", False),
        ])
        products = packaging.mapped("product_id").filtered_domain(product_domain)
        existing_ids = {record["id"] for record in records}
        extra = products.filtered(lambda product: product.id not in existing_ids)[:max(limit - len(records), 0)]
        if extra:
            records.extend(extra.web_read(specification))
            for read_vals, product in zip(records[-len(extra):], extra):
                if "display_name" in specification:
                    read_vals["__formatted_display_name"] = product.with_context(
                        formatted_display_name=True
                    ).display_name
        return records
