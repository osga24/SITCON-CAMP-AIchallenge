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
        this.addUserMessage(command);
        this.input.value = '';
        
        
        try {
            const response = await this.sendToChatAPI(command);
            this.hideTypingIndicator();
            this.addAIResponse(response.response);
        } catch (error) {
            this.hideTypingIndicator();
            this.addErrorMessage(`錯誤: ${error.message}`);
        }
    }
      isSystemCommand(command) {
        const systemCommands = ['help', 'clear', 'history', 'about', 'exit', 'config'];
        return systemCommands.includes(command.toLowerCase()) || command.startsWith('config:');
    }
    /*
    handleSystemCommand(command) {
        const cmd = command.toLowerCase();
        
        switch (cmd) {
            case 'help':
                this.addSystemMessage(`
Ubuntu Terminal Simulator Commands:
  help     - 顯示此幫助訊息
  clear    - 清除終端畫面
  history  - 顯示對話歷史
  about    - 關於此終端模擬器
  config   - 顯示配置選項
  exit     - 重新載入頁面
  
Linux Commands:
  ls, cd, pwd, cat, sudo, mkdir, rm, cp, mv, grep, etc.
  
配置命令:
  config:user=username     - 設置用戶名
  config:host=hostname     - 設置主機名
  config:dir=/path         - 設置工作目錄
  config:sudo=true/false   - 啟用/禁用sudo
  config:password=pass     - 設置root密碼
  
直接輸入Linux命令來與終端互動!`);
                break;
                
            case 'clear':
                this.clearTerminal();
                break;
                
            case 'history':
                this.showChatHistory();
                break;
                
            case 'about':
                this.addSystemMessage(`
Ubuntu Terminal Simulator v2.0
模擬真實的Ubuntu Linux終端環境
基於 Google Gemini AI
前端: HTML/CSS/JavaScript
後端: FastAPI + Python
開發者: SITCON CAMP Team

當前配置:
- 用戶: ${this.currentUser}
- 主機: ${this.currentHost}
- 目錄: ${this.currentDir}`);
                break;
                
            case 'config':
                this.showConfigOptions();
                break;
                
            case 'exit':
                this.addSystemMessage('正在重新載入終端...');
                setTimeout(() => location.reload(), 1000);
                break;
                
            default:
                if (command.startsWith('config:')) {
                    this.handleConfigCommand(command);
                }
                break;
        }
    }
    */
    
    handleConfigCommand(command) {
        const configPart = command.substring(7); // 移除 "config:"
        const [key, value] = configPart.split('=');
        
        if (!key || !value) {
            this.addErrorMessage('配置格式錯誤。使用: config:key=value');
            return;
        }
        
        const configData = {
            session_id: this.sessionId,
            hostname: this.currentHost,
            username: this.currentUser,
            working_directory: this.currentDir,
            root_password: "",
            sudo_enabled: true
        };
        
        switch (key) {
            case 'user':
                configData.username = value;
                this.currentUser = value;
                break;
            case 'host':
                configData.hostname = value;
                this.currentHost = value;
                break;
            case 'dir':
                configData.working_directory = value;
                this.currentDir = value;
                break;
            case 'sudo':
                configData.sudo_enabled = value.toLowerCase() === 'true';
                break;
            case 'password':
                configData.root_password = value;
                break;
            default:
                this.addErrorMessage(`未知的配置項: ${key}`);
                return;
        }
        
        this.sendConfigUpdate(configData);
        this.updatePrompt();
    }
    
    async sendConfigUpdate(config) {
        try {
            const response = await fetch('/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                this.addSystemMessage('配置已更新。');
            } else {
                this.addErrorMessage('配置更新失敗。');
            }
        } catch (error) {
            this.addErrorMessage(`配置錯誤: ${error.message}`);
        }
    }
    
    showConfigOptions() {
        this.addSystemMessage(`
當前系統配置:
- 用戶名: ${this.currentUser}
- 主機名: ${this.currentHost}  
- 工作目錄: ${this.currentDir}

配置命令範例:
  config:user=newuser      - 更改用戶名
  config:host=myserver     - 更改主機名
  config:dir=/home/user    - 更改工作目錄
  config:sudo=false        - 禁用sudo
  config:password=secret   - 設置root密碼`);
    }
    
    updatePrompt() {
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
    
    async showChatHistory() {
        try {
            const response = await fetch(`/history/${this.sessionId}`);
            const history = await response.json();
            
            if (history.length === 0) {
                this.addSystemMessage('目前沒有對話歷史。');
                return;
            }
            
            this.addSystemMessage('=== 對話歷史 ===');
            history.forEach((msg, index) => {
                if (msg.role === 'user') {
                    this.addLine(`[${index + 1}] 你: ${msg.content}`, 'user-input');
                } else {
                    this.addLine(`[${index + 1}] AI: ${msg.content}`, 'ai-response');
                }
            });
            this.addSystemMessage('=== 歷史結束 ===');
        } catch (error) {
            this.addErrorMessage(`無法載入歷史: ${error.message}`);
        }
    }
    
    clearTerminal() {
        this.output.innerHTML = '';
        this.addSystemMessage('Terminal cleared.');
    }
      addUserMessage(message) {
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
        div.textContent = text;
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