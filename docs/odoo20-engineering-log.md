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

## 2026-11-19 — Resolve fast packaging-barcode Enter in Sales

- Module/version: `ff_pos_packaging_sale` 20.0.1.0.9.
- Root cause: Odoo's `AccountLabelTextField` delays syncing the description textarea into its autocomplete input by 200 ms. When Enter was pressed immediately after typing a numeric packaging barcode, the extension read the still-empty autocomplete input, so native handling committed the digits as description text.
- Change: Read the first line directly from the Sales description textarea on Enter, resolve an exact unique packaging barcode, select its product template, and apply the packaging UoM after Odoo's normal template update completes. If the exact barcode does not resolve uniquely, preserve native product autocomplete behavior.
- Verification: Reproduced the immediate-Enter failure on the live sales form; updated the patch and repeated the action against barcode `33333333`. The resulting line selected `[0034456] 890 جودي بدون غطاء شد 10`, UoM `كرتون` (factor 10), and price 250.00. Database mapping confirms barcode `33333333` uniquely maps to product 18638 / template 18633 and UoM 5282 (`كرتون`). Odoo service active; JavaScript syntax and `git diff --check` passed.
- Boundary: No quotation was confirmed. Several test lines/drafts from repeated production UI trials remain visible; they were not deleted. POS and Purchase flows were not retested in this Sales-focused fix.

## 2026-11-19 — Restore POS selling-unit choice on product click

- Module/version: `ff_pos_packaging_sale` 20.0.1.0.10.
- Root cause: the 20.0.1.0.5 change intentionally removed the POS unit-choice popup. Packaging barcode scanning remained enabled, but clicking a product card followed the standard base-UoM path.
- Change: restore the unit-choice dialog when a POS product has alternate UoMs or POS packaging records; selecting the base unit uses Odoo's native flow, and selecting a package creates a package line with its contained quantity and computed price. Keep direct packaging barcode lookup intact. Register the dialog JavaScript and template in `point_of_sale._assets_pos` so POS loads both assets.
- Verification: on local Odoo 20 database `ff_demo_local20`, clicked Office Chair and confirmed the dialog listed `كرتون تجريبي (6 وحدة)` and the base unit. Selecting the carton closed the dialog and added `1 كرتون تجريبي Office Chair` at `$483.00` (6 × `$80.50`). JavaScript syntax, XML parsing, and `git diff --check` passed.
- Production: backed up the `aghsan` database, filestore, and existing addon to `/var/backups/odoo/ff-pos-packaging-20261119T132747Z/`; SHA256 checks passed. Upgraded production to 20.0.1.0.10 and restarted Odoo. Verified the module state/version, active service, and HTTPS login HTTP 200.
- Boundary: no POS payment or production order was created during verification. Cashier should refresh the POS page to load the rebuilt asset bundle; a fresh production cashier interaction remains to be confirmed.
