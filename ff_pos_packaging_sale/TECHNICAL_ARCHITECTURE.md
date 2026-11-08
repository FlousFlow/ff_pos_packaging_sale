# POS Packaging Sale — Odoo 20

## Selling behavior

- Product-card selection and regular product-barcode scans use the standard POS flow and add the product in its base UoM, without opening a unit picker.
- Scanning an enabled product-specific packaging barcode (`product.uom`) adds that packaging directly, because the barcode already identifies the selling unit.
- Sales orders use the native `product_uom_id` field. Odoo computes the line price using the order pricelist and selected UoM.
- POS evaluates pricelist rules at the package's contained-unit quantity, then multiplies the resulting unit price by that quantity. If no rule applies, it uses the product sale price per unit times the contained quantity.
- Stock quantities convert back to the product base UoM at Odoo 20's POS stock hooks.
- POS invoices retain structured packaging metadata on invoice lines.

## POS interaction

The POS packaging-selection popup is not used. Sales orders retain their native packaging UoM selector. Packaging metadata and price/stock conversion remain recorded for packaging-barcode sales.

## Compatibility boundary

This addon targets Odoo 20 APIs. It uses Odoo 20 invoice-line preparation, POS stock quantity, lot quantity, and product-cost hooks. Runtime install and cashier browser validation must be performed against the target Odoo 20 server before production activation.
