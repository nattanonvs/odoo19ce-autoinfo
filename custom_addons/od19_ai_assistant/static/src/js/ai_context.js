/** @odoo-module **/

/**
 * Read the page context of the currently open view.
 *
 * This is the ONLY place bound to the web-client internals: if Odoo changes
 * `env.services.action.currentController` in the future, fixing this file is
 * enough. Always returns a plain object or null — never throws.
 */
export function getPageContext(env) {
    try {
        const controller = env.services.action.currentController;
        const props = controller && controller.props;
        if (!props || !props.resModel) {
            return null;
        }
        const viewType = props.type;
        if (viewType !== "form" && viewType !== "list") {
            return null;
        }
        let resId = props.resId;
        if (!resId && controller.model && controller.model.root) {
            resId = controller.model.root.resId;
        }
        return {
            model: props.resModel,
            res_id: resId || false,
            view_type: viewType,
        };
    } catch {
        return null;
    }
}
