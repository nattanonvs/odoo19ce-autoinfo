/**
 * OD19 Offline Draft — client service.
 *
 * เก็บร่างลง IndexedDB ก่อน (ทันที, กันเน็ตหลุด) แล้ว sync ขึ้น `od19.draft`
 * เมื่อออนไลน์ — ทุกฟังก์ชันเป็น fail-safe: ถ้า store เขียนไม่ได้ ต้องไม่ทำให้
 * ฟอร์มหลักพัง
 */
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const DB_NAME = "od19_offline_draft";
const DB_VERSION = 1;
const STORE_DRAFTS = "drafts";
const STORE_ATTACHMENTS = "attachments";
const SCHEMA_VERSION = 1;

function draftKey(model, resId, userId) {
    return `${model}|${resId || 0}|${userId}`;
}

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = window.indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
                const store = db.createObjectStore(STORE_DRAFTS, { keyPath: "key" });
                store.createIndex("byModel", "model");
            }
            if (!db.objectStoreNames.contains(STORE_ATTACHMENTS)) {
                db.createObjectStore(STORE_ATTACHMENTS, { keyPath: "key" });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function runStore(db, storeName, mode, operation) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, mode);
        let request;
        try {
            request = operation(tx.objectStore(storeName));
        } catch (error) {
            reject(error);
            return;
        }
        if (request && "onsuccess" in request) {
            request.onsuccess = () => resolve(request.result);
        } else {
            tx.oncomplete = () => resolve(undefined);
        }
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
    });
}

export const od19DraftService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const config = session.od19_draft || {};
        const enabledModels = new Set(config.enabled_models || []);
        const userId = session.uid;
        let dbPromise = null;

        function isEnabled(model) {
            return Boolean(model) && enabledModels.has(model) && Boolean(userId);
        }

        function getDb() {
            if (!dbPromise) {
                dbPromise = openDatabase().catch((error) => {
                    dbPromise = null;
                    throw error;
                });
            }
            return dbPromise;
        }

        async function save(model, resId, payload) {
            if (!isEnabled(model)) {
                return false;
            }
            const key = draftKey(model, resId, userId);
            try {
                const db = await getDb();
                await runStore(db, STORE_DRAFTS, "readwrite", (store) =>
                    store.put({
                        key,
                        model,
                        resId: resId || 0,
                        userId,
                        payload,
                        schema: SCHEMA_VERSION,
                        dirty: true,
                        updatedAt: Date.now(),
                    })
                );
            } catch (error) {
                return false;
            }
            return true;
        }

        async function load(model, resId) {
            if (!isEnabled(model)) {
                return false;
            }
            try {
                const db = await getDb();
                return (
                    (await runStore(db, STORE_DRAFTS, "readonly", (store) =>
                        store.get(draftKey(model, resId, userId))
                    )) || false
                );
            } catch (error) {
                return false;
            }
        }

        async function clear(model, resId) {
            if (!isEnabled(model)) {
                return false;
            }
            const key = draftKey(model, resId, userId);
            try {
                const db = await getDb();
                await runStore(db, STORE_DRAFTS, "readwrite", (store) => store.delete(key));
                const attachKeys = await runStore(db, STORE_ATTACHMENTS, "readonly", (store) =>
                    store.getAllKeys()
                );
                for (const attachKey of attachKeys || []) {
                    if (String(attachKey).startsWith(`${key}|`)) {
                        await runStore(db, STORE_ATTACHMENTS, "readwrite", (store) =>
                            store.delete(attachKey)
                        );
                    }
                }
            } catch (error) {
                return false;
            }
            return true;
        }

        async function syncNow(model, resId, payload) {
            if (!isEnabled(model)) {
                return false;
            }
            try {
                await orm.call("od19.draft", "upsert_draft", [model, resId || 0, payload]);
                return true;
            } catch (error) {
                return false;
            }
        }

        async function flushPending() {
            try {
                const db = await getDb();
                const records = (
                    (await runStore(db, STORE_DRAFTS, "readonly", (store) => store.getAll())) || []
                ).filter((record) => record.userId === userId);
                for (const record of records) {
                    if (!record.dirty) {
                        continue;
                    }
                    const ok = await syncNow(record.model, record.resId, record.payload);
                    if (ok) {
                        await runStore(db, STORE_DRAFTS, "readwrite", (store) =>
                            store.put({ ...record, dirty: false })
                        );
                    }
                }
            } catch (error) {
                // fail-safe
            }
        }

        window.addEventListener("online", () => {
            flushPending().catch(() => {
                // fail-safe: sync will be retried on the next online event
            });
        });

        return { isEnabled, save, load, clear, syncNow, flushPending, config };
    },
};

registry.category("services").add("od19_draft", od19DraftService);
