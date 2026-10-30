# ff_pos_packaging_sale — Technical Architecture & Blueprint (Odoo 19 Community)

## Audit findings (source of truth: Odoo 19.0-20260619 container)

| Area | Finding |
|---|---|
| Barcode packaging model | **`product.uom`** (merged into product addon): `product_id` (M2o product.product), `uom_id` (M2o uom.uom = contained unit), `barcode` (unique, required), `company_id`. `_rec_name = 'barcode'` |
| Standard product packaging | **`product.template.uom_ids`** (M2M to `uom.uom`), configured directly on the product form and loaded into POS by this module. |
| Contained qty | `packaging.uom_id.factor / product.uom_id.factor` (e.g. Carton uom relative_factor=24 → 24 Units) |
| POS data loading | `product.template.load_product_from_pos()` returns `{'product.uom': [...]}`; fields whitelisted via `product.uom._load_pos_data_fields(config)` = `['id','barcode','product_id','uom_id']` |
| JS field metadata | `pos.session.load_data_params()` sends per-model `fields` + `relations` from `_load_pos_data_fields` → **any field added there becomes known & serializable on the JS side** |
| Order sync | `sync_from_ui` → `_process_order(order, existing)` → line vals filtered by `_is_field_accepted` (passes any real model field) → `_process_saved_order` → `action_pos_order_paid()` + `_create_order_picking()` (+ invoice) |
| Stock | `stock.picking._create_picking_from_pos_order_lines` → `_create_move_from_pos_order_lines` → `_prepare_stock_move_vals` uses `abs(sum(lines.mapped('qty')))` and base `product_id.uom_id`; move lines via `move.quantity = move.product_uom_qty` (untracked) or `abs(line.qty)` per lot (tracked — needs override) |
| Shipping path | `pos.order.line._launch_stock_rule_from_pos_order_lines` uses `product_qty = line.qty` (needs conversion) |
| Invoice | `pos.order._prepare_invoice_lines` → `_get_invoice_lines_values(line_values, pos_line, move_type)`; quantity = `line.qty` (commercial in our design), taxes on `price_unit × qty` |
| Refund (JS) | `TicketScreen.onDoRefund` creates `pos.order.line` with `refunded_orderline_id` but does NOT copy custom fields → we inject via `PosOrderline.setup` |
| Refund (backend) | `pos.order.line._prepare_refund_data` → we copy packaging fields |
| Receipt | `Orderline` component `lineScreenValues` renders `unitPart` from `line.getQuantityStr()` — commercial count is what shows |
| Taxes | `_prepare_tax_base_line_values` uses `quantity=line.qty`, `price_unit` → commercial count × packaging price = correct tax base |

## Core design decision — Commercial vs Stock quantity

**`pos.order.line.qty` stays the COMMERCIAL count (2 cartons) and `price_unit` stays the PACKAGING price (300).**

- Taxes / invoice amounts / reports: `2 × 300 = 600` ✔ (standard engine, untouched)
- Stock: converted at the stock boundary: `stock_qty = qty × ff_packaging_qty` = 48 base units ✔
- Accounting stays standard: invoice line `quantity = 2` with structured packaging fields; revenue = 600 ✔; COGS/valuation untouched (driven by stock moves, which carry 48) ✔
- The user explicitly allowed this: "عدل Invoice report بحيث يظهر Commercial Quantity … مع الاحتفاظ بالقيم الصحيحة في الـ backend"

## Data model

### product.uom (packaging) — new fields
- `ff_available_in_pos` Boolean
- `ff_pos_name` Char (display override, e.g. "كرتونة")
- `ff_pos_price` Float(digits='Product Price') — fixed POS price; **fallback** = contained_qty × pricelist unit price when empty
- `ff_is_default_pos_packaging` Boolean
- `ff_sequence` Integer default 10
- `ff_contained_qty` Float(compute) = uom factor ratio (used by tests/views; JS uses same ratio)
- `ff_pos_display_name` Float(compute) = ff_pos_name or uom_id.name
- Constraints: `ff_pos_price >= 0`; one default per product; default implies available_in_pos; POS-loading extended.

### product.template
- `ff_pos_packaging_behavior` Selection: `pos_config` / `default` / `ask` / `unit` (default `pos_config`)
- `ff_pos_default_packaging_id` M2o(product.uom) — must belong to this product (constraint)
- `ff_pos_allow_unit_sale` Boolean default True
- `uom_ids` is included in the POS data payload so standard product-form
  packagings can be selected even when no `product.uom` barcode rows exist.

### pos.config
- `ff_packaging_selection_behavior` Selection: `default` / `ask` / `unit` (default `default`)

### pos.order.line
- `ff_packaging_id` M2o(product.uom), `ff_packaging_name` Char snapshot,
  `ff_packaging_uom_id` M2o(uom.uom) for standard product-form packagings,
  `ff_packaging_qty` Float snapshot (contained qty), `ff_packaging_count` Float (commercial count),
  `ff_packaging_unit_price` Float snapshot
- `ff_base_uom_qty` Float(compute, store) = qty × ff_packaging_qty (reporting: Product|Packaging|Packages Sold|Base Units)
- `_ff_stock_qty()` helper = qty × ff_packaging_qty (or qty)
- Refund: copy packaging fields in `_prepare_refund_data`
- Added to `_load_pos_data_fields` → survive reload + offline sync

### account.move.line
- `ff_pos_packaging_id`, `ff_commercial_packaging_qty`, `ff_commercial_packaging_count` — structured data for the invoice report (not just description strings)

## JS (OWL patches, all scoped)

1. `PosOrderline` patch: setup defensive M2o resolve + refund-line inheritance of packaging fields + `canBeMergedWith` requires same packaging + `getTotalCost` × packaging qty
2. `ProductScreen` patch: `addProductToOrder` + `_barcodeProductAction` → `_ffHandlePackagingSelection` (behavior resolution → direct add / popup)
3. `PackagingSelectionPopup` (new Dialog): rows = Packaging name | contained qty | price (+ Unit row when allowed)
4. `TicketScreen`: refund handled via PosOrderline.setup inheritance (no core copy)
5. `Orderline` component patch + template extension: render "2 Carton" (commercial count + packaging label) on screen and receipt

## Views / reports
- product.template form: POS page fields
- product.uom: inherited editable list + own action + menu (POS → Configuration → Products → POS Packagings)
- pos.config form: behavior field
- Invoice report: `account.report_invoice_document` `td[name=td_quantity]` replaced with a packaging-aware version (commercial count + packaging name; base block hidden)

## Compromises (documented in README)
1. Rescan of the same packaging creates a sibling line (core blocks merge when `price_unit` is passed); cashier uses numpad for qty — merging packaging lines is possible later by adding a merge hook in `addLineToOrder`.
2. Lot-tracked products + packaging: move-level qty is converted; per-lot move lines use converted qty for lot-type tracking (serial × packaging is semantically ambiguous in v1).
3. Grouped invoice lines ("hide details" mode) don't display packaging (POS invoices use standard lines).
4. `product.uom` has no dedicated form view in v19 — managed via the editable list + menu.
