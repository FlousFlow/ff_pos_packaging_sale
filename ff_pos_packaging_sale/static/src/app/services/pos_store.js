/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    searchProductsFromDBDomain(searchProductWord) {
        const domain = super.searchProductsFromDBDomain(...arguments);
        return [
            "|",
            ["product_variant_ids.product_uom_ids.barcode", "ilike", searchProductWord],
            ...domain,
        ];
    },
});
