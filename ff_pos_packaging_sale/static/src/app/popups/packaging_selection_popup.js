/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatCurrency } from "@web/core/currency";

/**
 * Fast cashier-friendly packaging picker.
 * Each row shows: Packaging name | contained qty | price.
 * The base unit is always included as an explicit choice.
 * Resolves with the selected product.uom record (getPayload),
 * null for the base unit, or undefined when cancelled.
 */
export class PackagingSelectionPopup extends Component {
    static template = "ff_pos_packaging_sale.PackagingSelectionPopup";
    static components = { Dialog };
    static props = ["close", "product", "packagings", "pricelist", "getPayload?"];

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
        rows.push({ packaging: null, name: this.props.product.uom_id?.name || "Unit", contained: 1,
            price: this._price(null, 1) });
        return rows;
    }

    _price(packaging, contained) {
        const template = this.props.product.product_tmpl_id;
        try {
            const unitPrice = template.getPrice(
                this.props.pricelist || null,
                contained,
                0,
                false,
                this.props.product
            );
            return unitPrice * contained;
        } catch {
            return template.list_price * contained;
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
