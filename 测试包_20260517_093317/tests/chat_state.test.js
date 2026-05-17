const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const chatState = require(path.resolve(__dirname, "..", "chat-state.js"));

test("createFreshChatSession resets message index and order", () => {
  assert.deepEqual(chatState.createFreshChatSession(3), {
    sessionId: 4,
    currentChatOrder: [],
    chatMsgIndex: 0,
  });
});

test("resolveChatOrder falls back when current order is empty", () => {
  assert.deepEqual(
    chatState.resolveChatOrder([], ["铁板", "余墨"]),
    ["铁板", "余墨"],
  );
});

test("getRemainingChatEditors uses the active chat order", () => {
  assert.deepEqual(
    chatState.getRemainingChatEditors(["贴吧哥", "克莱恩", "余墨"], ["铁板", "余墨"], 1),
    ["克莱恩", "余墨"],
  );
});

test("isStaleChatSession marks older aborted sessions as stale", () => {
  assert.equal(chatState.isStaleChatSession(2, 1), true);
  assert.equal(chatState.isStaleChatSession(2, 2), false);
});
