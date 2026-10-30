/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { hasApplicablePricelistRule } from "@ff_pos_packaging_sale/app/screens/product_screen";

patch(PosOrder.prototype, {
    _ffHasPackagingPricelistRule(line, quantity) {
        return hasApplicablePricelistRule(
            line.product_id, this.pricelist_id, quantity, line.getPriceExtra(), line
        );
    },

    setLinePriceFromPriceList(line, pricelist) {
        if (!(line.ff_packaging_id || line.ff_packaging_uom_id)) {
            return super.setLinePriceFromPriceList(line, pricelist);
        }
        const quantity = line.getQuantity() * (line.ff_packaging_qty || 1);
        const price = line.product_id.product_tmpl_id.getPrice(
            pricelist,
            quantity,
            line.getPriceExtra(),
            false,
            line.product_id,
            line
        );
        const hasRule = this._ffHasPackagingPricelistRule(line, quantity);
        const fallback = line.ff_packaging_id?.ff_pos_price;
        const contained = line.ff_packaging_qty || 1;
        line.setUnitPrice(hasRule || !fallback ? price * contained : fallback);
    },

});
