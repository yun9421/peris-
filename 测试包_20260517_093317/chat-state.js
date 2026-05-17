(function (globalScope) {
  function cloneOrder(order) {
    return Array.isArray(order) ? order.slice() : [];
  }

  function createFreshChatSession(activeSessionId) {
    const previousId = Number.isInteger(activeSessionId) ? activeSessionId : 0;
    return {
      sessionId: previousId + 1,
      currentChatOrder: [],
      chatMsgIndex: 0,
    };
  }

  function resolveChatOrder(currentChatOrder, fallbackOrder) {
    const order = cloneOrder(currentChatOrder);
    return order.length > 0 ? order : cloneOrder(fallbackOrder);
  }

  function getRemainingChatEditors(currentChatOrder, fallbackOrder, chatMsgIndex) {
    const order = resolveChatOrder(currentChatOrder, fallbackOrder);
    const safeIndex = Number.isInteger(chatMsgIndex) && chatMsgIndex > 0 ? chatMsgIndex : 0;
    return order.slice(safeIndex);
  }

  function isStaleChatSession(activeSessionId, sessionId) {
    return activeSessionId !== sessionId;
  }

  const api = {
    createFreshChatSession,
    resolveChatOrder,
    getRemainingChatEditors,
    isStaleChatSession,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  globalScope.PierisChatState = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
