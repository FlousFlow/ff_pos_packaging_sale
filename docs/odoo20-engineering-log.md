# Odoo 20 Engineering Log

## 2026-11-08 — Remove POS packaging choice popup

- Module: `ff_pos_packaging_sale` `20.0.1.0.5`.
- Decision: product-card clicks and regular product barcodes follow the native POS flow with the base UoM. A packaging barcode still selects its own packaging directly.
- Preserved: packaging pricing, order-line metadata, stock conversion, invoice/refund support, and the Sales order UoM selector.
- Validation: fresh Odoo 20 database installation and all 13 selected module tests passed (0 failures, 0 errors); Python/JavaScript syntax and `git diff --check` passed.
- Boundary: no production database or cashier session was changed during this local implementation.

## 2026-11-19 — Packaging barcode selection in Sales

- Module/version: `ff_pos_packaging_sale` 20.0.1.0.7.
- Issue: Sales autocomplete resolved a product packaging barcode to the product template, but the selected sale line kept the template's default UoM.
- Evidence: The rendered sales line uses the `sol_label_text` field, whose autocomplete is implemented by Odoo's `SaleLabelTextField` and whose selection flows through `updateMany2XProduct`; the prior patch targeted `SaleOrderLineProductField`, so it never handled this UI. Production record `product.uom` barcode `33333333` resolves to product template 18633 and UoM `كرتون` (contained qty 10).
- Change: Capture the typed packaging barcode at autocomplete selection and carry it on the actual `SaleLabelTextField` instance through product-template update; set the packaging UoM after Odoo completes its standard product/configurator update.
- Verification: On the live `aghsan` database, typed `33333333` into the sales-line product search, selected `[0034456] 890 جودي بدون غطاء شد 10`, and confirmed the line changed from base UoM `ربطة` to `كرتون`; the price recalculated from 28.00 to 280.00 for the 10-unit carton. Odoo service is active and module version 20.0.1.0.7 is installed. JavaScript syntax and `git diff --check` passed.
- Safety/boundary: No quotation was confirmed. UI testing left empty draft quotes visible in Sales (S00007–S00009); they were not deleted because permanently deleting production records requires explicit approval. POS and Purchase barcode flows were not retested in this sales-focused fix.
