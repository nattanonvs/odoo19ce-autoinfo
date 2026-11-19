/** @odoo-module **/

import { Component, onPatched, reactive, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useBus, useService } from "@web/core/utils/hooks";
import { getPageContext } from "./ai_context";

/** Shared open/close state (systray button and the panel both read it). */
export const aiPanelState = reactive({ open: false });

export function toggleAiPanel() {
    aiPanelState.open = !aiPanelState.open;
}

/**
 * The single chat panel reused by every surface.
 *
 * It reads the current page context on open/send so the assistant already
 * knows which document the user is looking at, and streams the answer from
 * ``/od19_ai/chat/stream`` (the same route the full-page chat uses).
 */
export class AiPanel extends Component {
    static template = "od19_ai_assistant.AiPanel";
    static props = {};

    setup() {
        this.notification = useService("notification");
        this.messagesRef = useRef("messages");
        // Read the shared module-level reactive through useState so this
        // component subscribes to its changes (a direct read would not).
        this.panelState = useState(aiPanelState);
        this.state = useState({
            chats: [],
            activeChatId: false,
            messages: [],
            draft: "",
            streaming: false,
            streamText: "",
            toolChips: [],
            error: "",
            pendingDraft: null,
            chips: [],
        });
        this._wasOpen = false;
        onPatched(() => {
            if (this.panelState.open !== this._wasOpen) {
                this._wasOpen = this.panelState.open;
                if (this.panelState.open) {
                    // Load the model-aware chips when the panel becomes visible;
                    // the current page context is guaranteed to be ready then.
                    this.loadChips();
                }
            }
            if (this.state.streaming) {
                this.scrollToBottom();
            }
        });
        useBus(this.env.bus, "ACTION_MANAGER:UPDATE", () => {
            // This event fires before the action service exposes the new
            // controller, so defer the read until the page context settles.
            setTimeout(() => this.loadChips(), 50);
        });
    }

    get pageContext() {
        return getPageContext(this.env);
    }

    get isDocked() {
        const ctx = this.pageContext;
        return Boolean(ctx && ctx.view_type === "form" && ctx.res_id);
    }

    get panelClass() {
        return this.isDocked ? "o_od19_ai_panel o_od19_ai_docked" : "o_od19_ai_panel";
    }

    get isOpen() {
        return this.panelState.open;
    }

    async loadChips() {
        const ctx = getPageContext(this.env);
        try {
            const data = await rpc("/od19_ai/suggest", ctx || {});
            this.state.chips = data.chips || [];
        } catch {
            this.state.chips = [];
        }
    }

    close() {
        aiPanelState.open = false;
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
    }

    useChip(chip) {
        this.state.draft = chip;
        this.send();
    }

    async ensureChat() {
        if (this.state.activeChatId) {
            return this.state.activeChatId;
        }
        const [id] = await rpc("/od19_ai/chat/create", {});
        this.state.activeChatId = id;
        return id;
    }

    async send() {
        const text = this.state.draft.trim();
        if (!text || this.state.streaming) {
            return;
        }
        const chatId = await this.ensureChat();
        const ctx = getPageContext(this.env);
        this.state.draft = "";
        this.state.error = "";
        this.state.streamText = "";
        this.state.toolChips = [];
        this.state.messages.push({ id: -Date.now(), role: "user", content: text });
        this.state.streaming = true;
        this.scrollToBottom();
        try {
            await this.streamChat(chatId, text, ctx);
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.streaming = false;
            this.state.streamText = "";
            this.state.toolChips = [];
            await this.loadMessages(chatId);
        }
    }

    async loadMessages(chatId) {
        const data = await rpc("/od19_ai/chat/messages", { chat_id: chatId });
        this.state.messages = data.messages;
        this.scrollToBottom();
    }

    async streamChat(chatId, message, ctx) {
        const body = { chat_id: chatId, message };
        if (ctx) {
            body.model = ctx.model;
            body.res_id = ctx.res_id;
            body.view_type = ctx.view_type;
        }
        const response = await fetch("/od19_ai/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!response.ok || !response.body) {
            throw new Error("เชื่อมต่อผู้ช่วย AI ไม่สำเร็จ (HTTP " + response.status + ")");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            let sep;
            while ((sep = buffer.indexOf("\n\n")) >= 0) {
                this.handleEventBlock(buffer.slice(0, sep));
                buffer = buffer.slice(sep + 2);
            }
        }
        if (buffer.trim()) {
            this.handleEventBlock(buffer);
        }
    }

    handleEventBlock(block) {
        for (const line of block.split("\n")) {
            if (!line.startsWith("data:")) {
                continue;
            }
            try {
                this.onStreamEvent(JSON.parse(line.slice(5).trim()));
            } catch {
                continue;
            }
        }
    }

    onStreamEvent(event) {
        switch (event.type) {
            case "delta":
                this.state.streamText += event.content;
                break;
            case "round_end":
                if (event.kind === "tool") {
                    this.state.streamText = "";
                }
                break;
            case "tool":
                if (event.status === "done") {
                    this.state.toolChips.push(event.name);
                }
                break;
            case "draft":
                this.state.pendingDraft = event.draft;
                this.state.streamText = "";
                break;
            case "error":
                this.state.error = event.message;
                this.state.streamText = "";
                break;
        }
    }

    async confirmDraft() {
        const pending = this.state.pendingDraft;
        if (!pending) {
            return;
        }
        try {
            const result = await rpc("/od19_ai/draft/confirm", {
                model: pending.model,
                values: pending.values,
            });
            this.notification.add(
                `สร้างเอกสารร่างแล้ว: ${result.name}`,
                { type: "success" }
            );
            this.state.pendingDraft = null;
        } catch (error) {
            this.state.error = error.message || "ยืนยันร่างไม่สำเร็จ";
        }
    }

    cancelDraft() {
        this.state.pendingDraft = null;
    }

    scrollToBottom() {
        const el = this.messagesRef.el;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }
}

registry.category("main_components").add("od19_ai_assistant.AiPanel", {
    Component: AiPanel,
});
