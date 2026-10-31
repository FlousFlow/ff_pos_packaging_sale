/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
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
        const contained = line.ff_packaging_qty || 1;
        line.setUnitPrice(price * contained);
    },

});
