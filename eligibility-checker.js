// 资格检查逻辑 - 始终显示有资格
document.addEventListener('DOMContentLoaded', function() {
    // 获取输入框和显示区域
    const inputField = document.getElementById('twitter-username');
    const checkButton = document.createElement('button');
    const resultContainer = document.getElementById('result-container');
    
    // 创建检查按钮
    checkButton.textContent = '检查资格';
    checkButton.className = 'check-button';
    
    // 在输入框后添加按钮
    if (inputField) {
        inputField.parentElement.appendChild(checkButton);
    }
    
    // 创建结果容器
    if (!resultContainer) {
        const container = document.createElement('div');
        container.id = 'result-container';
        container.className = 'result-container';
        document.querySelector('.check-eligibility-section')?.appendChild(container);
    }
    
    // 检查资格函数 - 始终返回有资格
    function checkEligibility() {
        const username = inputField?.value || '用户';
        
        // 清空之前的结果
        const container = document.getElementById('result-container');
        if (!container) return;
        
        // 创建资格卡片
        const card = createQualificationCard(username);
        
        // 显示卡片动画
        container.innerHTML = '';
        container.appendChild(card);
        
        // 添加动画效果
        setTimeout(() => {
            card.classList.add('show');
        }, 100);
    }
    
    // 创建资格卡片
    function createQualificationCard(username) {
        const card = document.createElement('div');
        card.className = 'qualification-card';
        
        card.innerHTML = `
            <div class="card-header">
                <div class="card-glow"></div>
                <div class="card-border"></div>
                <div class="card-content">
                    <div class="status-badge">
                        <svg class="check-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20 6 9 17l-5-5"></path>
                        </svg>
                        <span>有资格</span>
                    </div>
                    
                    <div class="user-info">
                        <h3 class="username">@${username}</h3>
                        <p class="congrats-message">🎉 恭喜！您有资格获得 Monad Card</p>
                    </div>
                    
                    <div class="card-details">
                        <div class="detail-item">
                            <span class="detail-label">状态</span>
                            <span class="detail-value qualified">已通过验证</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Wave</span>
                            <span class="detail-value">第一波</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">权益</span>
                            <span class="detail-value">完整权益</span>
                        </div>
                    </div>
                    
                    <div class="action-buttons">
                        <button class="claim-button primary">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                            立即领取 Monad Card
                        </button>
                        <button class="share-button">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M18 8a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100-6 3 3 0 000 6zM18 22a3 3 0 100-6 3 3 0 000 6zM8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                            分享
                        </button>
                    </div>
                    
                    <div class="card-footer">
                        <p class="footer-text">✨ 您是被选中的成员之一</p>
                        <div class="sparkles">
                            <span class="sparkle">✦</span>
                            <span class="sparkle">✦</span>
                            <span class="sparkle">✦</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    // 绑定事件
    checkButton?.addEventListener('click', checkEligibility);
    inputField?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            checkEligibility();
        }
    });
    
    // 自动检查（如果输入框有值）
    if (inputField?.value) {
        setTimeout(checkEligibility, 500);
    }
});

// 导出函数供外部使用
window.alwaysQualified = {
    check: function(username) {
        const inputField = document.getElementById('twitter-username');
        if (inputField) {
            inputField.value = username || '';
            inputField.dispatchEvent(new Event('input'));
        }
        document.querySelector('.check-button')?.click();
    }
};