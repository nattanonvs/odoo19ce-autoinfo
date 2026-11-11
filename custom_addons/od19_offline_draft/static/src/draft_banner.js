import { Component } from "@odoo/owl";

export class DraftBanner extends Component {
    static template = "od19_offline_draft.DraftBanner";
    static props = {
        draft: Object,
        onRestore: Function,
        onDiscard: Function,
    };
}
