/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2OneBarcodeField } from "@web/views/fields/many2one_barcode/many2one_barcode_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { SaleLabelTextField } from "@sale/js/sale_label_text/sale_label_text";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field/sale_product_field";
import { SalePackagingSelectionDialog } from "@ff_pos_packaging_sale/sale/packaging_selection_dialog";

let ffPackagingSearchBarcode = null;

patch(Many2XAutocomplete.prototype, {
    buildRecordSuggestion(request, record) {
        const suggestion = super.buildRecordSuggestion(...arguments);
        const selectRecord = suggestion.onSelect;
        suggestion.onSelect = () => {
            ffPackagingSearchBarcode = /^\d{5,}$/.test(request) ? request : null;
            return selectRecord();
        };
        return suggestion;
    },
});

patch(SaleLabelTextField.prototype, {
    async updateMany2XProduct(record) {
        const barcode = ffPackagingSearchBarcode;
        this._ffPackagingSearchBarcode = /^\d{5,}$/.test(barcode || "") ? barcode : null;
        ffPackagingSearchBarcode = null;
        return super.updateMany2XProduct(...arguments);
    },

    async _onProductTemplateUpdate() {
        await super._onProductTemplateUpdate(...arguments);
        const barcode = this._ffPackagingSearchBarcode;
        this._ffPackagingSearchBarcode = null;
        const template = this.props.record.data.product_template_id;
        if (!barcode || !template?.id) {
            return;
        }
        const [packaging] = await this.orm.searchRead(
            "product.uom",
            [["barcode", "=", barcode], ["product_id.product_tmpl_id", "=", template.id]],
            ["uom_id"],
            { limit: 1 }
        );
        if (packaging?.uom_id?.[0]) {
            await this.props.record.update({
                product_uom_id: {
                    id: packaging.uom_id[0],
                    display_name: packaging.uom_id[1],
                },
            });
        }
    },
});

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

// Support fields that use the many2one_barcode widget when it is present.
patch(Many2OneBarcodeField.prototype, {
    get m2oProps() {
        const props = super.m2oProps;
        const originalUpdate = props.update;
        return {
            ...props,
            update: async (value) => {
                const input = this.el?.querySelector("input");
                const barcode = input?.value?.trim();
                const result = await originalUpdate(value);
                const isSaleProduct =
                    ["product_id", "product_template_id"].includes(this.props.name) &&
                    ["product.template", "product.product"].includes(this.props.relation);
                if (isSaleProduct && value?.id && /^\d{5,}$/.test(barcode || "")) {
                    const relation = this.props.relation;
                    const productDomain = relation === "product.template"
                        ? [["product_id.product_tmpl_id", "=", value.id]]
                        : [["product_id", "=", value.id]];
                    const [packaging] = await this.env.services.orm.searchRead(
                        "product.uom",
                        [["barcode", "=", barcode], ...productDomain],
                        ["uom_id"],
                        { limit: 1 }
                    );
                    if (packaging?.uom_id?.[0]) {
                        await this.props.record.update({
                            product_uom_id: {
                                id: packaging.uom_id[0],
                                display_name: packaging.uom_id[1],
                            },
                        });
                    }
                }
                return result;
            },
        };
    },
});
