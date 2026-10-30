# POS Packaging Sale — Odoo 20

## Selling behavior

- When a product has configured commercial packagings, POS asks for the selling unit every time it is selected.
- The POS picker combines product-specific barcode packagings (`product.uom`) with the product template's configured UoMs.
- Sales orders use the native `product_uom_id` field. Odoo computes the line price using the order pricelist and selected UoM.
- POS packaging prices are fallback prices only when no applicable pricelist rule exists.
- Stock quantities convert back to the product base UoM at Odoo 20's POS stock hooks.
- POS invoices retain structured packaging metadata on invoice lines.

## Removed settings

The product-level Ask/Default/Unit mode and POS configuration behavior selector were removed. They contradicted the rule that configured packaging always prompts at selection time.

## Compatibility boundary

This addon targets Odoo 20 APIs. It uses Odoo 20 invoice-line preparation, POS stock quantity, lot quantity, and product-cost hooks. Runtime install and cashier browser validation must be performed against the target Odoo 20 server before production activation.
