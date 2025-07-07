// Team Input Handler
class TeamInputHandler {
  constructor() {
    this.teamInputScreen = document.getElementById("team-input-screen");
    this.terminalContainer = document.getElementById("terminal-container");
    this.teamNumberInput = document.getElementById("team-number");
    this.teamSubmitButton = document.getElementById("team-submit");
    
    this.setupEventListeners();
    this.teamNumberInput.focus();
  }

  setupEventListeners() {
    // Handle Enter key in team number input
    this.teamNumberInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        this.handleTeamSubmit();
      }
    });

    // Handle submit button click
    this.teamSubmitButton.addEventListener("click", () => {
      this.handleTeamSubmit();
    });
  }

  handleTeamSubmit() {
    const teamNumber = this.teamNumberInput.value.trim();
    
    if (!teamNumber) {
      this.showError("請輸入隊伍編號");
      return;
    }

    // Validate team number - must be a number between 1-10
    const teamNum = parseInt(teamNumber);
    if (isNaN(teamNum) || !Number.isInteger(teamNum) || teamNum < 1 || teamNum > 10) {
      this.showError("隊伍編號必須是 1-10 之間的數字");
      return;
    }

    // Store team number (you can send this to backend if needed)
    sessionStorage.setItem('teamNumber', teamNumber);
    
    // Hide team input screen and show terminal
    this.showTerminal();
  }

  showError(message) {
    // Remove existing error message
    const existingError = document.querySelector('.team-error');
    if (existingError) {
      existingError.remove();
    }

    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'team-error';
    errorDiv.textContent = message;
    this.teamNumberInput.parentNode.appendChild(errorDiv);

    // Clear error after 3 seconds
    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.remove();
      }
    }, 3000);
  }

  showTerminal() {
    this.teamInputScreen.style.display = 'none';
    this.terminalContainer.style.display = 'flex';
    
    // Initialize terminal after showing it
    new Terminal();
  }
}

class Terminal {
  constructor() {
    this.output = document.getElementById("terminal-output");
    this.input = document.getElementById("command-input");
    this.commandHistory = [];
    this.historyIndex = -1;
    this.sessionId = this.getOrCreateSessionId();

    this.setupEventListeners();
    
    // Show welcome message with team number
    const teamNumber = sessionStorage.getItem('teamNumber');
    this.addSystemMessage(
      `歡迎 Team ${teamNumber}! Ubuntu Terminal Simulator ready. Type "help" for available commands.`
    );
  }

  getOrCreateSessionId() {
    // 使用 team number 作為 session ID
    return sessionStorage.getItem('teamNumber') || 'unknown';
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
  new TeamInputHandler();
});
