# POS Packaging Sale (ff_pos_packaging_sale)

Sell products by configured packagings in Odoo 20 POS and Sales. In POS, a product click or regular product barcode adds the base unit without an extra prompt; scanning a configured packaging barcode adds that packaging directly. Sales orders keep their packaging-unit selector. Stock is tracked in the product's base UoM.

## Behavior

- POS product selection and regular product scans add the base unit directly, with no unit-selection popup.
- Scanning an enabled packaging barcode adds that packaging directly, without an extra choice screen.
- Sales order selection offers the template's configured UoMs and uses native pricelist calculation after the chosen UoM is set.
- POS evaluates the active pricelist at the package's contained-unit quantity and multiplies the resulting per-unit price by that quantity.
- Without a matching pricelist rule, POS uses the product's sale price per unit multiplied by the package quantity.
- POS order lines retain packaging identity and contained quantity; stock quantities are converted at Odoo 20 stock hooks.
- POS invoices preserve packaging metadata. Refund lines preserve the selected package.

## Configure

1. Install `ff_pos_packaging_sale`.
2. Add standard packaging UoMs in the product template's Packagings field, or create product barcode packaging records.
3. For barcode packaging records, set the UoM, contained quantity, name and Available in POS.
4. Configure the desired pricelist rules. Quantity thresholds are evaluated using the package's contained-unit quantity.

## Validation

Run the module tests against the target Odoo 20 database and verify regular product selection, packaging-barcode scans, pricelist changes, stock pickings, refunds, invoice data, and Sales order UoM selection before production rollout.

The port targets Odoo 20 Community. Browser cashier validation and live database installation are separate from static compatibility checks.
