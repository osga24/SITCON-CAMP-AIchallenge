class Terminal {
    constructor() {
        this.output = document.getElementById('terminal-output');
        this.input = document.getElementById('command-input');
        this.sessionId = 'session_' + Date.now();
        this.commandHistory = [];
        this.historyIndex = -1;
        this.currentUser = 'sitcon';
        this.currentHost = 'ubuntu';
        this.currentDir = '/home/sitcon';
        
        this.setupEventListeners();
        this.addSystemMessage('Ubuntu Terminal Simulator ready. Type "help" for available commands.');
        this.updatePrompt();
    }
    
    setupEventListeners() {
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.handleCommand();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory(-1);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory(1);
            }
        });
        
        // 保持輸入框聚焦
        document.addEventListener('click', () => {
            this.input.focus();
        });
        
        this.input.focus();
    }
    
    navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;
        
        this.historyIndex += direction;
        
        if (this.historyIndex < 0) {
            this.historyIndex = -1;
            this.input.value = '';
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
        
        // 添加到歷史
        this.commandHistory.push(command);
        this.historyIndex = -1;
        
        // 顯示用戶輸入
        this.addUserMessage(command);        this.input.value = '';
        
        try {
            const response = await this.sendToChatAPI(command);
            this.hideTypingIndicator();
            this.addAIResponse(response.response);
        } catch (error) {
            this.hideTypingIndicator();
            this.addErrorMessage(`錯誤: ${error.message}`);
        }
    }
    
    
    updatePrompt() {
        return;
        const promptElement = document.querySelector('.prompt');
        if (promptElement) {
            promptElement.textContent = `${this.currentUser}@${this.currentHost}:${this.currentDir}$ `;
        }
    }
    
    async sendToChatAPI(message) {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    clearTerminal() {
        this.output.innerHTML = '';
        this.addSystemMessage('Terminal cleared.');
    }
      addUserMessage(message) {
        this.addLine(` `, 'user-input');

        return;
        this.addLine(`${this.currentUser}@${this.currentHost}:${this.currentDir}$ ${message}`, 'user-input');
    }
    
    addAIResponse(response) {
        this.addLine(response, 'ai-response');
    }
    
    addSystemMessage(message) {
        this.addLine(`System: ${message}`, 'system-message');
    }
    
    addErrorMessage(message) {
        this.addLine(`Error: ${message}`, 'error-message');
    }    
    addLine(text, className = '') {
        const div = document.createElement('div');
        div.className = `command-line ${className}`;
        div.textContent = text.replace("```","");
        this.output.appendChild(div);
        this.scrollToBottom();
    }
    
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    scrollToBottom() {
        this.output.scrollTop = this.output.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Terminal();
});