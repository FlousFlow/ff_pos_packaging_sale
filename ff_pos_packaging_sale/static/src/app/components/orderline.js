/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

/**
 * Add the commercial packaging label to the line values rendered on the
 * POS screen, the customer display and the receipt: "2 Carton".
 */
patch(Orderline.prototype, {
    get lineScreenValues() {
        const vals = super.lineScreenValues;
        const label = this.line.ffPackagingLabel;
        return {
            ...vals,
            packagingName: label || "",
        };
    },
});
