/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field/sale_product_field";
import { SalePackagingSelectionDialog } from "@ff_pos_packaging_sale/sale/packaging_selection_dialog";

patch(SaleOrderLineProductField.prototype, {
    get m2oProps() {
        const props = super.m2oProps;
        const originalUpdate = props.update;
        return {
            ...props,
            update: async (value) => {
                const input = this.el?.querySelector('input');
                const query = input?.value?.trim() || props.value?.display_name || '';
                const result = await originalUpdate(value);
                if (!value?.id || !/^\d{5,}$/.test(query)) {
                    return result;
                }
                await this._ffSelectScannedPackaging(value.id, query);
                return result;
            },
        };
    },

    async _ffSelectScannedPackaging(productId, barcode) {
        const [packaging] = await this.orm.searchRead(
            "product.uom",
            [["barcode", "=", barcode], ["product_id", "=", productId]],
            ["uom_id"],
            { limit: 1 }
        );
        if (packaging?.uom_id?.[0]) {
            await this.props.record.update({
                product_uom_id: { id: packaging.uom_id[0], display_name: packaging.uom_id[1] },
            });
        }
    },

    async _onProductUpdate() {
        const scannedBarcode = this.el?.querySelector('input')?.value?.trim();
        await super._onProductUpdate(...arguments);
        const product = this.props.record.data.product_id;
        if (!product?.id) return;
        if (this.props.record.data.is_downpayment || this.props.record.data.display_type) return;
        if (scannedBarcode) {
            const [packaging] = await this.orm.searchRead(
                "product.uom",
                [["barcode", "=", scannedBarcode], ["product_id", "=", product.id]],
                ["uom_id", "ff_pos_name", "ff_pos_display_name", "ff_contained_qty"],
                { limit: 1 }
            );
            if (packaging?.uom_id?.[0]) {
                await this.props.record.update({
                    product_uom_id: {
                        id: packaging.uom_id[0],
                        display_name: packaging.uom_id[1],
                    },
                });
                return;
            }
        }
        const [productData] = await this.orm.read("product.product", [product.id], ["product_tmpl_id"]);
        const [template] = await this.orm.read("product.template", [productData.product_tmpl_id[0]], ["uom_id", "uom_ids"]);
        const choices = [...new Set([template.uom_id[0], ...template.uom_ids])];
        const uoms = await this.orm.read("uom.uom", choices, ["name", "factor", "sequence"]);
        const base = uoms.find((uom) => uom.id === template.uom_id[0]);
        const packagingChoices = uoms
            .filter((uom) => uom.id !== base.id)
            .map((uom) => ({
                id: uom.id,
                name: uom.name,
                contained: this._ffUomContained(uom, base),
                factor: uom.factor,
            }));
        if (!packagingChoices.length) return;
        packagingChoices.push({ id: base.id, name: base.name, contained: 1 });
        await new Promise((resolve) => this.dialog.add(SalePackagingSelectionDialog, {
            choices: packagingChoices,
            onSelect: async (choice) => {
                try {
                    await this.props.record.update({ product_uom_id: { id: choice.id, display_name: choice.name } });
                } finally {
                    resolve();
                }
            },
        }, { onClose: resolve }));
    },

    _ffUomContained(uom, base) {
        return uom.factor && base?.factor ? uom.factor / base.factor : 1;
    },
});
