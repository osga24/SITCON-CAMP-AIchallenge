class Terminal {
  constructor() {
    this.output = document.getElementById("terminal-output");
    this.input = document.getElementById("command-input");
    this.commandHistory = [];
    this.historyIndex = -1;
    this.sessionId = this.getOrCreateSessionId();

    this.setupEventListeners();
    this.addSystemMessage(
      'Ubuntu Terminal Simulator ready. Type "help" for available commands.'
    );
  }

  getOrCreateSessionId() {
    // 每次都生成新的 session ID
    return this.generateUUID();
  }

  generateUUID() {
    // 簡單的 UUID v4 生成器
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }



  setupEventListeners() {
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        this.handleCommand();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.navigateHistory(1);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        this.navigateHistory(-1);
      }
    });

    // 保持輸入框聚焦
    document.addEventListener("click", () => {
      this.input.focus();
    });

    this.input.focus();
  }

  navigateHistory(direction) {
    if (this.commandHistory.length === 0) return;

    this.historyIndex += direction;

    if (this.historyIndex < 0) {
      this.historyIndex = -1;
      this.input.value = "";
    } else if (this.historyIndex >= this.commandHistory.length) {
      this.historyIndex = this.commandHistory.length - 1;
    }

    if (this.historyIndex >= 0) {
      this.input.value = this.commandHistory[this.historyIndex];
    }
  }

  async handleCommand() {
    const command = this.input.value.trim();
    if (!command) return;

    // 處理本地命令
    if (command === "clear") {
      this.clearTerminal();
      return;
    }

    // 添加到歷史
    this.commandHistory.push(command);
    this.historyIndex = -1;
    this.input.value = "";

    // 顯示加載指示器
    this.showTypingIndicator();

    try {
      const response = await this.sendToChatAPI(command);
      this.hideTypingIndicator();
      this.addAIResponse(response.response);
    } catch (error) {
      this.hideTypingIndicator();
      this.addErrorMessage(`錯誤: ${error.message}`);
    }
  }

  async sendToChatAPI(message) {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message,
        session_id: this.sessionId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  }

  clearTerminal() {
    this.output.innerHTML = "";
    this.commandHistory = []; // 清空指令歷史
    this.addSystemMessage("Terminal cleared.");
  }

  addAIResponse(response) {
    this.addLine(response, "ai-response");
  }

  addSystemMessage(message) {
    this.addLine(`System: ${message}`, "system-message");
  }

  addErrorMessage(message) {
    this.addLine(`Error: ${message}`, "error-message");
  }
  addLine(text, className = "") {
    const div = document.createElement("div");
    div.className = `command-line ${className}`;
    div.textContent = text.replace("```", "");
    this.output.appendChild(div);
    this.scrollToBottom();
  }

  showTypingIndicator() {
    const div = document.createElement("div");
    div.id = "typing-indicator";
    div.className = "command-line typing";
    div.textContent = "Processing...";
    this.output.appendChild(div);
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) {
      indicator.remove();
    }
  }

  scrollToBottom() {
    this.output.scrollTop = this.output.scrollHeight;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new Terminal();
});
