/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SalePackagingSelectionDialog extends Component {
    static template = "ff_pos_packaging_sale.SalePackagingSelectionDialog";
    static components = { Dialog };
    static props = ["close", "choices", "onSelect"];

    select(choice) {
        this.props.onSelect(choice);
        this.props.close();
    }
}
