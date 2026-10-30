# POS Packaging Sale (ff_pos_packaging_sale)

Sell products in **Odoo 19 Point of Sale** by commercial **Packaging** (Carton / Box / Pack /
Shrink-wrap...) while the actual **stock movement stays in the base UoM**.

## The principle

One product. One barcode. No separate products, no BoM, no UoM change.

```
Product:      Water Bottle        Base UoM:   Unit
Packagings:   Unit   = 1 Unit     POS price:  15 EGP
              Box    = 6 Units     POS price:  80 EGP
              Carton = 24 Units    POS price:  300 EGP
```

Customer buys **2 Cartons**:

| Surface | Shows | Internal |
|---|---|---|
| POS order line | `2 Carton × 300.00 = 600.00` | qty = 2 (commercial count) |
| Receipt | `2 Carton` | — |
| Invoice | `2 Carton` (report) with `quantity = 2` | accounting amount = 600 |
| Stock picking / move | — | **48 Units** (2 × 24), base UoM |
| Taxes | on **300 × 2** (packaging price) | never on 48 × unit price |
| Refund `-1 Carton` | `-1 Carton` on receipt | **+24 Units** returned |

This clean separation between **Commercial Packaging Quantity** and
**Inventory Base Quantity** is the core of the module — see
[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) for the full audit of the
Odoo 19 POS internals and the design decisions.

## Features

- **Packaging POS fields** on `product.uom` (Odoo 19's packaging model):
  Available in POS, POS Name, POS Price, Default in POS, Sequence.
- **Standard product packagings** configured in the product form (`uom_ids`) are
  also available in the POS popup. This is the path used by products that have
  packaging tags such as “Pack of 6” or “Carton of 12” but no barcode packaging
  row.
- **Product behavior**: `Per POS Config` / `Default Packaging` / `Ask Every Time` /
  `Unit by Default` + `Allow Unit Sale`.
- **POS config default** behavior for products set to `Per POS Config`.
- **Cashier-friendly packaging popup**: each row shows name | contained qty | price.
  Products with exactly one default packaging and behavior `Default` are added
  without any popup.
- **One barcode**: scanning the product barcode applies the behavior; packaging
  barcodes are not required (core packaging-barcode scanning still works).
- **Structured data** on `pos.order.line` (`ff_packaging_id`, `ff_packaging_name`,
  `ff_packaging_qty`, `ff_packaging_count`, `ff_packaging_unit_price`,
  computed `ff_base_uom_qty`) and on `account.move.line`
  (`ff_pos_packaging_id`, `ff_commercial_packaging_qty`,
  `ff_commercial_packaging_count`) — no reliance on description strings.
- **Receipt + invoice report** show the commercial unit (`2 Carton`).
- **Refunds** keep the packaging semantics (`-1 Carton` → +24 units back).
- **Offline-safe**: all packaging fields are part of the POS data loading and the
  order synchronization payload.
- **Multi-company**: packagings keep their core `company_id`; POS loads only the
  packagings of the loaded products.

### Price priority

1. Packaging fixed price (`ff_pos_price`).
2. **Documented fallback**: contained quantity × pricelist unit price.

## Setup

1. Install the module.
2. Open **Point of Sale → Configuration → Products → POS Packagings**
   (or edit packagings from their existing list).
3. Either configure standard packagings in the product form, or manage barcode
   packagings from **POS Packagings**. For barcode packagings set the contained
   unit (`uom_id`), POS name, POS price, and tick *Available in POS* (+ *Default
   in POS* if needed).
4. On the product form → **Point of Sale** page: choose the *Packaging Selection
   Behavior* (or leave `Per POS Config` and set it on the POS config form).

## Tests

```bash
docker exec odoo_clean_web odoo -c /etc/odoo/odoo.conf -d <db> \
    -u ff_pos_packaging_sale --test-enable --stop-after-init \
    --test-tags /ff_pos_packaging_sale
```

Covers: stock conversion (2 cartons → 48 units), receipt data, invoice fields,
refund conversion, packaging price independence, barcode uniqueness, plain
products untouched, POS data loading, taxes on packaging price, multiple
packagings, and all constraints.

## Known compromises (v1)

1. **Re-scan does not merge**: core blocks line merging when an explicit
   `price_unit` is passed, so scanning the same packaging twice creates two
   lines. Cashiers should use the numpad to change the packaging count
   (2 Cartons = select line, qty 2). Adding a merge hook inside
   `addLineToOrder` is the planned v2 improvement.
2. **Lot/serial + packaging**: the move quantity is converted, but tracking a
   product by serial while selling it by carton is semantically ambiguous
   (which serials are inside the carton?) — lot-type tracking assigns the
   converted quantity per lot.
3. **Grouped invoice lines** (`hide details` mode) don't display packaging.
4. `product.uom` has no form view in v19 — packaging management uses the
   editable list.

## Compatibility

Odoo 19.0 Community. Depends only on `point_of_sale`.
