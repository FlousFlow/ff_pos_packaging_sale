/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    async _barcodeProductAction(code) {
        const barcode = code.base_code;
        const strippedBarcode = /^0\d+$/.test(barcode) ? String(parseInt(barcode, 10)) : null;
        const packaging =
            this.pos.models["product.uom"].getBy("barcode", barcode) ||
            (strippedBarcode && this.pos.models["product.uom"].getBy("barcode", strippedBarcode));
        if (packaging?.product_id) {
            const product = packaging.product_id;
            this.sound.play("beep");
            if (!(await this.pos.canAddProductToCurrentOrder(product.product_tmpl_id))) {
                return;
            }
            await this._ffAddPackagingLine(product, packaging);
            this.numberBuffer.reset();
            return;
        }
        // Regular product barcodes follow Odoo's normal flow and add the base
        // unit directly. Packaging barcodes above already identify the unit.
        return super._barcodeProductAction(code);
    },

    async _ffAddPackagingLine(variant, packaging) {
        const contained =
            packaging.ff_contained_qty ||
            (packaging.uom_id && variant.product_tmpl_id.uom_id
                ? packaging.uom_id.factor / variant.product_tmpl_id.uom_id.factor
                : 1);
        const price = this._ffPackagingPrice(variant, packaging, contained);
        await this.pos.addLineToCurrentOrder({
            product_tmpl_id: variant.product_tmpl_id,
            product_id: variant,
            qty: this.currentOrder?.preset_id?.is_return ? -1 : 1,
            price_unit: price,
            ...(packaging.ff_is_template_uom
                ? { ff_packaging_uom_id: packaging.ff_uom_record }
                : { ff_packaging_id: packaging }),
            ff_packaging_count: 1,
            ff_packaging_qty: contained,
            ff_packaging_name:
                packaging.ff_pos_name || packaging.ff_pos_display_name || packaging.name || packaging.uom_id?.name || "",
            ff_packaging_unit_price: price,
        });
    },

    /** Price one package using the pricelist at its contained-unit quantity. */
    _ffPackagingPrice(variant, _packaging, contained) {
        const pricelist = this.currentOrder?.pricelist_id;
        try {
            const unitPrice = variant.product_tmpl_id.getPrice(
                pricelist || null,
                contained,
                0,
                false,
                variant
            );
            return unitPrice * contained;
        } catch {
            return variant.product_tmpl_id.list_price * contained;
        }
    },
});
