# POS Packaging Sale (ff_pos_packaging_sale)

Sell products by configured packagings in Odoo 20 POS and Sales. Product selection prompts for the selling unit whenever packagings exist. Stock is tracked in the product's base UoM.

## Behavior

- POS selection combines enabled barcode packagings and standard product UoMs.
- Sales order selection offers the template's configured UoMs and uses native pricelist calculation after the chosen UoM is set.
- POS evaluates the active pricelist at the package's contained-unit quantity and multiplies the resulting per-unit price by that quantity.
- Without a matching pricelist rule, POS uses the product's sale price per unit multiplied by the package quantity.
- The base UoM is always a choice when a product has configured packaging.
- POS order lines retain packaging identity and contained quantity; stock quantities are converted at Odoo 20 stock hooks.
- POS invoices preserve packaging metadata. Refund lines preserve the selected package.

## Configure

1. Install `ff_pos_packaging_sale`.
2. Add standard packaging UoMs in the product template's Packagings field, or create product barcode packaging records.
3. For barcode packaging records, set the UoM, contained quantity, name and Available in POS.
4. Configure the desired pricelist rules. Quantity thresholds are evaluated using the package's contained-unit quantity.

## Validation

Run the module tests against the target Odoo 20 database and verify POS product selection, pricelist changes, stock pickings, refunds, invoice data, and Sales order UoM selection in a browser session before production rollout.

The port targets Odoo 20 Community. Browser cashier validation and live database installation are separate from static compatibility checks.
