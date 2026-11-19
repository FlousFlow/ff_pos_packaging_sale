/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    getProductsBySearchWord(searchWord, products) {
        const matches = super.getProductsBySearchWord(...arguments);
        const query = searchWord.trim().toLowerCase();
        if (!query) {
            return matches;
        }
        const matchedIds = new Set(matches.map((product) => product.id));
        const packagingMatches = products.filter((product) =>
            !matchedIds.has(product.id) &&
            (product.ff_packaging_barcodes || '').toLowerCase().split(/\\s+/).includes(query)
        );
        return [...matches, ...packagingMatches];
    },
});
