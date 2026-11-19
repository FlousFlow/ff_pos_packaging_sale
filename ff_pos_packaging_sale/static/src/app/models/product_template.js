/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

patch(ProductTemplate.prototype, {
    get searchString() {
        const packagingBarcodes = this.ff_packaging_barcodes || "";
        return `${super.searchString} ${packagingBarcodes}`.trim();
    },
});
