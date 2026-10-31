/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PackagingSelectionPopup } from "@ff_pos_packaging_sale/app/popups/packaging_selection_popup";

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        // Configurable products must first pass through Odoo's configurator so
        // the selected variant is known before the selling unit is requested.
        if (product.isConfigurable() || product.isCombo()) {
            return super.addProductToOrder(product);
        }
        if (await this._ffHandlePackagingSelection(product)) {
            return;
        }
        return super.addProductToOrder(product);
    },

    async _barcodeProductAction(code) {
        const barcode = code.base_code;
        const strippedBarcode = /^0\d+$/.test(barcode) ? String(parseInt(barcode, 10)) : null;
        const packaging =
            this.pos.models["product.uom"].getBy("barcode", barcode) ||
            (strippedBarcode && this.pos.models["product.uom"].getBy("barcode", strippedBarcode));
        if (packaging?.ff_available_in_pos && packaging.product_id) {
            const product = packaging.product_id;
            this.sound.play("beep");
            if (!(await this.pos.canAddProductToCurrentOrder(product.product_tmpl_id))) {
                return;
            }
            await this._ffAddPackagingLine(product, packaging);
            this.numberBuffer.reset();
            return;
        }
        const product = await this._getProductByBarcode(code);
        if (!product) {
            return super._barcodeProductAction(code);
        }
        this.sound.play("beep");
        if (!(await this.pos.canAddProductToCurrentOrder(product.product_tmpl_id))) {
            return;
        }
        if (await this._ffHandlePackagingSelection(product)) {
            this.numberBuffer.reset();
            return;
        }
        return super._barcodeProductAction(code);
    },

    /**
     * Resolve the selling-unit choice for a product and, when applicable,
     * add the order line with the chosen packaging. Returns true when the
     * standard product flow must be skipped.
     * `product` may be a product.template (product card click) or a
     * product.product (barcode scan) — normalize to the variant here.
     */
    async _ffHandlePackagingSelection(product) {
        const variant = this._ffVariantOf(product);
        const packagings = this._ffGetPosPackagings(variant);
        if (!packagings.length) {
            return false; // standard behavior, untouched
        }

        const picked = await makeAwaitable(this.dialog, PackagingSelectionPopup, {
                product: variant,
                packagings,
                pricelist: this.currentOrder?.pricelist_id || null,
            });
        if (picked === undefined) {
            return true;
        }
        if (picked === null) {
            await this.pos.addLineToCurrentOrder({
                product_tmpl_id: variant.product_tmpl_id,
                product_id: variant,
            });
            return true;
        }
        await this._ffAddPackagingLine(variant, picked);
        return true;
    },

    /** Return the product.product for a template-or-variant input. */
    _ffVariantOf(product) {
        if (product.product_variant_ids?.length) {
            return product.product_variant_ids[0];
        }
        return product;
    },

    _ffGetPosPackagings(variant) {
        const barcodePackagings = this.pos.models["product.uom"]
            .getAll()
            .filter(
                (p) =>
                    p.product_id?.id === variant.id &&
                    p.ff_available_in_pos
            )
            .sort((a, b) => (a.ff_sequence ?? 10) - (b.ff_sequence ?? 10));
        // Product forms configure standard POS packagings in product.template
        // `uom_ids`.  They are regular uom.uom records, not product.uom
        // barcode links, so expose them as lightweight picker descriptors.
        const tmpl = variant.product_tmpl_id;
        const baseFactor = tmpl?.uom_id?.factor || 1;
        // A packaging can be configured both as a product-specific barcode
        // unit and as a standard product UoM. Prefer the barcode record so the
        // cashier sees one choice with the configured label and barcode.
        const barcodeUomIds = new Set(
            barcodePackagings.map((packaging) => packaging.uom_id?.id).filter(Boolean)
        );
        const standardPackagings = (tmpl?.uom_ids || [])
            .filter((uom) => uom?.id && uom.id !== tmpl.uom_id?.id && !barcodeUomIds.has(uom.id))
            .map((uom) => ({
                ff_is_template_uom: true,
                ff_uom_record: uom,
                name: uom.name,
                factor: uom.factor,
                ff_contained_qty: baseFactor ? uom.factor / baseFactor : 1,
                ff_sequence: uom.sequence ?? 10,
            }))
            .filter((packaging) => packaging.ff_contained_qty > 0)
            .sort((a, b) => (a.ff_sequence ?? 10) - (b.ff_sequence ?? 10));
        return [...barcodePackagings, ...standardPackagings];
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
