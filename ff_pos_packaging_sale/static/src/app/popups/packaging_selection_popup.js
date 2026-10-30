/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatCurrency } from "@web/core/currency";

/**
 * Fast cashier-friendly packaging picker.
 * Each row shows: Packaging name | contained qty | price.
 * A "Unit" row is appended when the product allows unit sale.
 * Resolves with the selected product.uom record (getPayload),
 * null for the base unit, or undefined when cancelled.
 */
export class PackagingSelectionPopup extends Component {
    static template = "ff_pos_packaging_sale.PackagingSelectionPopup";
    static components = { Dialog };
    static props = ["close", "product", "packagings", "canSellUnit", "pricelist", "getPayload?"];

    setup() {
        this.pos = usePos();
    }

    formatPrice(price) {
        return formatCurrency(price, this.pos?.currency?.id);
    }

    get rows() {
        const rows = this.props.packagings.map((packaging) => {
            const contained =
                packaging.ff_contained_qty ||
                (packaging.uom_id && this.props.product.product_tmpl_id.uom_id
                    ? packaging.uom_id.factor / this.props.product.product_tmpl_id.uom_id.factor
                    : 1);
            return {
                packaging,
                name:
                    packaging.ff_pos_name ||
                    packaging.ff_pos_display_name ||
                    packaging.name ||
                    packaging.uom_id?.name ||
                    "",
                contained,
                price: this._price(packaging, contained),
            };
        });
        if (this.props.canSellUnit) {
            rows.push({ packaging: null, name: this.props.product.uom_id?.name || "Unit", contained: 1, price: null });
        }
        return rows;
    }

    _price(packaging, contained) {
        if (packaging.ff_pos_price) {
            return packaging.ff_pos_price;
        }
        // Documented fallback: contained qty x pricelist unit price
        try {
            const unitPrice = this.props.product.product_tmpl_id.getPrice(
                this.props.pricelist,
                contained,
                0,
                false,
                this.props.product
            );
            return unitPrice * contained;
        } catch {
            return this.props.product.product_tmpl_id.list_price * contained;
        }
    }

    confirm(row) {
        if (this.props.getPayload) {
            this.props.getPayload(row.packaging); // null = base unit
        }
        this.props.close();
    }

    cancel() {
        if (this.props.getPayload) {
            this.props.getPayload(undefined); // undefined = cancelled
        }
        this.props.close();
    }
}
