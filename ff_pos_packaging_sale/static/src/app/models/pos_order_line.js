/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

/**
 * Commercial packaging support on POS order lines.
 *
 * The line `qty` is the COMMERCIAL count (e.g. 2 Cartons) and `price_unit`
 * the packaging price (e.g. 300 per carton). The conversion to the base UoM
 * (2 x 24 = 48 units) happens on the backend at the stock boundary only —
 * the customer always sees the packaging.
 */
patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(vals);
        if (this.ff_packaging_id === false) this.ff_packaging_id = null;
        if (this.ff_packaging_uom_id === false) this.ff_packaging_uom_id = null;
        if (this.ff_packaging_id || this.ff_packaging_uom_id) {
            this.price_type = "original";
        }
        // Defensive: resolve a raw packaging id (can happen after deserialize)
        if (this.ff_packaging_id && typeof this.ff_packaging_id === "number") {
            this.ff_packaging_id = this.models["product.uom"].get(this.ff_packaging_id);
        }
        if (this.ff_packaging_uom_id && typeof this.ff_packaging_uom_id === "number") {
            this.ff_packaging_uom_id = this.models["uom.uom"].get(this.ff_packaging_uom_id);
        }
        if (this.ff_packaging_id === false) this.ff_packaging_id = null;
        if (this.ff_packaging_uom_id === false) this.ff_packaging_uom_id = null;
        // Refund lines are created by the core refund flow without the custom
        // packaging fields — inherit them from the refunded line.
        const refunded = this.refunded_orderline_id;
        if (refunded && (refunded.ff_packaging_id || refunded.ff_packaging_uom_id)
            && !this.ff_packaging_id && !this.ff_packaging_uom_id) {
            this.ff_packaging_id = refunded.ff_packaging_id;
            this.ff_packaging_uom_id = refunded.ff_packaging_uom_id;
            this.ff_packaging_name = refunded.ff_packaging_name;
            this.ff_packaging_qty = refunded.ff_packaging_qty;
            this.ff_packaging_count = Math.abs(this.qty) || 0;
            this.ff_packaging_unit_price = refunded.ff_packaging_unit_price;
        }
    },

    canBeMergedWith(orderline) {
        const packagingKey = (line) =>
            line.ff_packaging_id?.id ? `product.uom:${line.ff_packaging_id.id}`
                : line.ff_packaging_uom_id?.id ? `uom.uom:${line.ff_packaging_uom_id.id}` : "unit";
        const samePackaging = packagingKey(this) === packagingKey(orderline);
        return super.canBeMergedWith(orderline) && samePackaging;
    },

    setQuantity() {
        const result = super.setQuantity(...arguments);
        if (result === true && (this.ff_packaging_id || this.ff_packaging_uom_id)) {
            this.ff_packaging_count = Math.abs(this.getQuantity());
            if (this.price_type === "original") this.recomputeUnitPrice();
        }
        return result;
    },

    isPosGroupable() {
        return this.ff_packaging_id || this.ff_packaging_uom_id
            ? false
            : super.isPosGroupable(...arguments);
    },

    getTotalCost() {
        // Cost must follow the inventory quantity (base UoM), not the count
        return this.product_id.standard_price * this._ffStockQty();
    },

    recomputeUnitPrice() {
        if (this.ff_packaging_id || this.ff_packaging_uom_id) {
            const contained = this.ff_packaging_qty || 1;
            const quantity = this.getQuantity() * contained;
            const unitPrice = this.product_id.product_tmpl_id.getPrice(
                this.order_id.pricelist_id,
                quantity,
                this.getPriceExtra(),
                false,
                this.product_id
            );
            this.setUnitPrice(unitPrice * contained);
            return;
        }
        return super.recomputeUnitPrice(...arguments);
    },

    /** Inventory quantity in the product base UoM for this line. */
    _ffStockQty() {
        if ((this.ff_packaging_id || this.ff_packaging_uom_id) && this.ff_packaging_qty) {
            return this.qty * this.ff_packaging_qty;
        }
        return this.qty;
    },

    serializeForORM() {
        const data = super.serializeForORM(...arguments);
        data.ff_packaging_id = this.ff_packaging_id?.id || false;
        data.ff_packaging_uom_id = this.ff_packaging_uom_id?.id || false;
        data.ff_packaging_name = this.ff_packaging_name || "";
        data.ff_packaging_qty = this.ff_packaging_qty || 0;
        data.ff_packaging_count = this.ff_packaging_count || Math.abs(this.qty);
        data.ff_packaging_unit_price = this.ff_packaging_unit_price || this.price_unit;
        return data;
    },

    /** Commercial quantity label: the count + packaging name ("2 Carton"). */
    get ffPackagingLabel() {
        if (!this.ff_packaging_id && !this.ff_packaging_uom_id) {
            return "";
        }
        return (
            this.ff_packaging_name
            || this.ff_packaging_id?.ff_pos_display_name
            || this.ff_packaging_id?.uom_id?.name
            || this.ff_packaging_uom_id?.name
            || ""
        );
    },
});
