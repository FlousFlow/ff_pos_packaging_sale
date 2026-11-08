# Odoo 20 Engineering Log

## 2026-11-08 — Remove POS packaging choice popup

- Module: `ff_pos_packaging_sale` `20.0.1.0.5`.
- Decision: product-card clicks and regular product barcodes follow the native POS flow with the base UoM. A packaging barcode still selects its own packaging directly.
- Preserved: packaging pricing, order-line metadata, stock conversion, invoice/refund support, and the Sales order UoM selector.
- Validation: fresh Odoo 20 database installation and all 13 selected module tests passed (0 failures, 0 errors); Python/JavaScript syntax and `git diff --check` passed.
- Boundary: no production database or cashier session was changed during this local implementation.
