/** @odoo-module **/

import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SalePackagingSelectionDialog extends Component {
    static template = "ff_pos_packaging_sale.SalePackagingSelectionDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        choices: t.array(),
        onSelect: t.function(),
    });

    select(choice) {
        this.props.onSelect(choice);
        this.props.close();
    }
}
