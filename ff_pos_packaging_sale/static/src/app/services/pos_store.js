/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { normalize } from "@web/core/l10n/utils";

patch(PosStore.prototype, {
    getProductsBySearchWord(searchWord, products) {
        const matches = super.getProductsBySearchWord(...arguments);
        const query = normalize(searchWord || "");
        if (!query) {
            return matches;
        }

        const matchedProducts = new Set(matches);
        const barcodeMatches = products.filter((product) => {
            if (matchedProducts.has(product)) {
                return false;
            }
            const variants = product.product_variant_ids?.length
                ? product.product_variant_ids
                : [product];
            const variantIds = new Set(variants.map((variant) => variant.id));
            return this.models["product.uom"].getAll().some(
                (packaging) =>
                    packaging.ff_available_in_pos &&
                    variantIds.has(packaging.product_id?.id) &&
                    normalize(packaging.barcode || "").includes(query)
            );
        });

        return [...matches, ...barcodeMatches];
    },

    searchProductsFromDBDomain(searchProductWord) {
        const domain = super.searchProductsFromDBDomain(...arguments);
        return [
            "|",
            ["product_variant_ids.product_uom_ids.barcode", "ilike", searchProductWord],
            ...domain,
        ];
    },
});
