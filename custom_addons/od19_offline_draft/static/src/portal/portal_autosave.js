/**
 * OD19 Offline Draft — portal autosave.
 *
 * หน้า portal เป็น QWeb POST ปกติ (ไม่ใช่ OWL) จึงเก็บค่าฟอร์มลง localStorage
 * เป็นระยะ และกู้คืนเมื่อโหลดหน้าเดิม — fail-safe ทุกเส้นทาง
 */
import { session } from "@web/session";

(function () {
    const config = session.od19_draft || {};
    if (!config.enabled_models) {
        return;
    }
    const debounceMs = config.debounce_ms || 2000;
    const userId = session.uid;

    function storageKey(form) {
        const action = form.getAttribute("action") || window.location.pathname;
        return `od19_draft:portal:${action}:${userId}`;
    }

    function collect(form) {
        const data = {};
        for (const element of form.elements) {
            if (!element.name) {
                continue;
            }
            if (element.type === "password" || element.type === "file") {
                continue;
            }
            if (element.type === "checkbox" || element.type === "radio") {
                if (element.checked) {
                    data[element.name] = element.value;
                }
            } else {
                data[element.name] = element.value;
            }
        }
        return data;
    }

    function restore(form) {
        let saved;
        try {
            const raw = window.localStorage.getItem(storageKey(form));
            saved = raw ? JSON.parse(raw) : null;
        } catch (error) {
            return;
        }
        if (!saved || !saved.data) {
            return;
        }
        for (const [name, value] of Object.entries(saved.data)) {
            const element = form.elements[name];
            if (!element) {
                continue;
            }
            if (element.type === "checkbox" || element.type === "radio") {
                element.checked = element.value === value;
            } else {
                element.value = value;
            }
        }
        form.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function attach(form) {
        restore(form);
        let timer = null;
        const flush = () => {
            try {
                window.localStorage.setItem(
                    storageKey(form),
                    JSON.stringify({ data: collect(form), updatedAt: Date.now() })
                );
            } catch (error) {
                // fail-safe
            }
        };
        form.addEventListener("input", () => {
            clearTimeout(timer);
            timer = setTimeout(flush, debounceMs);
        });
        form.addEventListener("change", () => {
            clearTimeout(timer);
            timer = setTimeout(flush, debounceMs);
        });
        form.addEventListener("submit", () => {
            clearTimeout(timer);
            try {
                window.localStorage.removeItem(storageKey(form));
            } catch (error) {
                // fail-safe
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        for (const form of document.querySelectorAll("form.od19-portal-draft, form[data-od19-draft]")) {
            attach(form);
        }
    });
})();
