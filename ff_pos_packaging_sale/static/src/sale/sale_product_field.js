/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field/sale_product_field";
import { SalePackagingSelectionDialog } from "@ff_pos_packaging_sale/sale/packaging_selection_dialog";

patch(SaleOrderLineProductField.prototype, {
    async _onProductUpdate() {
        await super._onProductUpdate(...arguments);
        const product = this.props.record.data.product_id;
        if (!product?.id) return;
        if (this.props.record.data.is_downpayment || this.props.record.data.display_type) return;
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
