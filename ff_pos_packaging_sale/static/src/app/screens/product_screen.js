/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { SalePackagingSelectionDialog } from "@ff_pos_packaging_sale/sale/packaging_selection_dialog";

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        const choices = this._ffPackagingChoices(product);
        if (!choices.length || product.isConfigurable() || product.isCombo()) {
            return super.addProductToOrder(...arguments);
        }
        if (!(await this.pos.canAddProductToCurrentOrder(product))) {
            return;
        }
        const choice = await new Promise((resolve) => {
            this.dialog.add(
                SalePackagingSelectionDialog,
                {
                    choices,
                    onSelect: resolve,
                },
                { onClose: () => resolve(null) }
            );
        });
        if (!choice) {
            return;
        }
        if (choice.isBase) {
            return super.addProductToOrder(...arguments);
        }

        const variant = product.product_variant_ids[0];
        const line = await this._ffAddPackagingLine(variant, choice);
        if (line) {
            this.showOptionalProductPopupIfNeeded(product);
        }
        return line;
    },

    _ffPackagingChoices(product) {
        const base = product.uom_id;
        if (!base) {
            return [];
        }
        const choices = [];
        const includedUomIds = new Set();
        const variants = new Set((product.product_variant_ids || []).map((variant) => variant.id));
        const barcodePackagings = this.pos.models["product.uom"]
            .getAll()
            .filter(
                (packaging) =>
                    packaging.ff_available_in_pos &&
                    variants.has(packaging.product_id?.id) &&
                    packaging.uom_id?.id
            )
            .sort((a, b) => a.ff_sequence - b.ff_sequence);

        for (const packaging of barcodePackagings) {
            const uom = packaging.uom_id;
            includedUomIds.add(uom.id);
            choices.push({
                id: `packaging-${packaging.id}`,
                name: packaging.ff_pos_name || uom.name,
                contained: packaging.ff_contained_qty || this._ffUomContained(uom, base),
                packaging,
            });
        }

        for (const uom of product.uom_ids || []) {
            if (!uom || uom.id === base.id || includedUomIds.has(uom.id)) {
                continue;
            }
            includedUomIds.add(uom.id);
            choices.push({
                id: `uom-${uom.id}`,
                name: uom.name,
                contained: this._ffUomContained(uom, base),
                uom,
            });
        }

        if (choices.length) {
            choices.push({ id: `base-${base.id}`, name: base.name, contained: 1, isBase: true });
        }
        return choices;
    },

    _ffUomContained(uom, base) {
        return uom.factor && base?.factor ? uom.factor / base.factor : 1;
    },

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
        const uom = packaging.uom || packaging.uom_id;
        const contained = packaging.contained || packaging.ff_contained_qty || this._ffUomContained(
            uom,
            variant.product_tmpl_id.uom_id
        );
        const price = this._ffPackagingPrice(variant, packaging, contained);
        return this.pos.addLineToCurrentOrder({
            product_tmpl_id: variant.product_tmpl_id,
            product_id: variant,
            qty: this.currentOrder?.preset_id?.is_return ? -1 : 1,
            price_unit: price,
            ...(packaging.uom
                ? { ff_packaging_uom_id: packaging.uom }
                : { ff_packaging_id: packaging.packaging || packaging }),
            ff_packaging_count: 1,
            ff_packaging_qty: contained,
            ff_packaging_name: packaging.name || packaging.ff_pos_name || uom?.name || "",
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
