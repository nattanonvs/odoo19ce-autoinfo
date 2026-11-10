/** @odoo-module **/

import { Component, onPatched, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

/**
 * Client action: a full-page chat UI for the OD19 AI assistant.
 *
 * Layout: conversation history on the left, message thread in the middle,
 * composer at the bottom. Answers are streamed token by token from
 * ``/od19_ai/chat/stream`` (Server-Sent Events over fetch).
 */
export class Od19AiChatAction extends Component {
    static template = "od19_ai_assistant.ChatAction";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.messagesRef = useRef("messages");
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
        });
        onPatched(() => {
            if (this.state.streaming) {
                this.scrollToBottom();
            }
        });
        this.loadChats();
    }

    get hasConversation() {
        return (
            this.state.messages.length > 0 ||
            this.state.streaming ||
            Boolean(this.state.streamText)
        );
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async loadChats() {
        this.state.chats = await rpc("/od19_ai/chat/list", {});
    }

    async loadMessages(chatId) {
        const data = await rpc("/od19_ai/chat/messages", { chat_id: chatId });
        this.state.messages = data.messages;
    }

    async createChat() {
        const [id] = await rpc("/od19_ai/chat/create", {});
        await this.loadChats();
        return id;
    }

    async selectChat(chatId) {
        if (this.state.streaming || chatId === this.state.activeChatId) {
            return;
        }
        this.state.activeChatId = chatId;
        this.state.error = "";
        this.state.streamText = "";
        this.state.toolChips = [];
        this.state.pendingDraft = null;
        await this.loadMessages(chatId);
        this.scrollToBottom();
    }

    async newChat() {
        if (this.state.streaming) {
            return;
        }
        this.state.activeChatId = false;
        this.state.messages = [];
        this.state.streamText = "";
        this.state.toolChips = [];
        this.state.error = "";
        this.state.draft = "";
        this.state.pendingDraft = null;
    }

    async deleteChat(chatId) {
        if (this.state.streaming) {
            return;
        }
        await rpc("/od19_ai/chat/delete", { chat_id: chatId });
        if (chatId === this.state.activeChatId) {
            await this.newChat();
        }
        await this.loadChats();
    }

    // ------------------------------------------------------------------
    // Sending / streaming
    // ------------------------------------------------------------------
    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
    }

    async send() {
        const text = this.state.draft.trim();
        if (!text || this.state.streaming) {
            return;
        }
        let chatId = this.state.activeChatId;
        if (!chatId) {
            chatId = await this.createChat();
            this.state.activeChatId = chatId;
        }
        this.state.draft = "";
        this.state.error = "";
        this.state.streamText = "";
        this.state.toolChips = [];
        this.state.messages.push({ id: -Date.now(), role: "user", content: text });
        this.state.streaming = true;
        this.scrollToBottom();
        try {
            await this.streamChat(chatId, text);
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.streaming = false;
            this.state.streamText = "";
            this.state.toolChips = [];
            await this.loadMessages(chatId);
            await this.loadChats();
            this.scrollToBottom();
        }
    }

    async streamChat(chatId, message) {
        const response = await fetch("/od19_ai/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, message }),
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
                const block = buffer.slice(0, sep);
                buffer = buffer.slice(sep + 2);
                this.handleEventBlock(block);
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
            let payload;
            try {
                payload = JSON.parse(line.slice(5).trim());
            } catch {
                continue;
            }
            this.onStreamEvent(payload);
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

    onStreamEvent(event) {
        switch (event.type) {
            case "delta":
                this.state.streamText += event.content;
                break;
            case "round_end":
                // A tool request was streamed as text: drop it, the answer
                // will arrive in the next round.
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

    scrollToBottom() {
        const el = this.messagesRef.el;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }
}

registry.category("actions").add("od19_ai_assistant.chat", Od19AiChatAction);
