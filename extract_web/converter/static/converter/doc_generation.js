// 文档生成模块逻辑（ES5 语法以兼容现有代码结构）

(function() {
    if (window.docGenerationModuleInitialized) {
        return;
    }

    let docGenInitialized = false;
    let currentSelectedDocGenMode = 'ppt';
    const docGenState = {
        useLocalFile: false,
        useUrl: false,
        localFile: null,
        url: '',  // 保留用于单URL兼容
        urls: [],  // 新增：多URL数组
        template: 'style_a'
    };

    function debounce(fn, delay) {
        var timer = null;
        return function() {
            var args = arguments;
            if (timer) {
                clearTimeout(timer);
            }
            timer = setTimeout(function() {
                fn.apply(null, args);
            }, delay);
        };
    }

    function switchDocumentGenerationMode(mode) {
        if (!mode) return;
        currentSelectedDocGenMode = mode;
        var pptBtn = document.getElementById('docGenTabPpt');
        var wordBtn = document.getElementById('docGenTabWord');
        if (pptBtn && wordBtn) {
            if (mode === 'ppt') {
                pptBtn.classList.add('active');
                wordBtn.classList.remove('active');
            } else {
                pptBtn.classList.remove('active');
                wordBtn.classList.add('active');
            }
        }
        var templateSection = document.getElementById('docGenTemplateSection');
        if (templateSection) {
            templateSection.style.display = mode === 'ppt' ? 'block' : 'none';
        }
        updateDocumentGenerationSubmitState();
    }

    function collectAllUrls() {
        var urlInputs = document.querySelectorAll('.doc-gen-url-input');
        var urls = [];
        Array.prototype.forEach.call(urlInputs, function(input) {
            var url = input.value.trim();
            if (url && /^https?:\/\//i.test(url)) {
                urls.push(url);
            }
        });
        return urls;
    }

    function updateDocumentGenerationSubmitState() {
        var startBtn = document.getElementById('docGenStartBtn');
        if (!startBtn) return;
        var hasLocal = docGenState.useLocalFile && !!docGenState.localFile;
        
        // 收集所有URL
        var urls = collectAllUrls();
        docGenState.urls = urls;
        docGenState.url = urls.length > 0 ? urls[0] : '';  // 兼容旧代码
        
        var hasUrl = docGenState.useUrl && urls.length > 0;
        var ready = (hasLocal || hasUrl);
        startBtn.disabled = !ready;
    }

    function initializeMultiUrlInputs() {
        var container = document.getElementById('docGenUrlContainer');
        if (!container) return;

        // 添加URL输入框
        container.addEventListener('click', function(e) {
            if (e.target.classList.contains('doc-gen-url-add-btn')) {
                var newGroup = document.createElement('div');
                newGroup.className = 'doc-gen-url-group';
                newGroup.style.display = 'flex';
                newGroup.style.gap = '8px';
                newGroup.style.marginBottom = '8px';
                
                var urlCheckbox = document.getElementById('docGenUseUrl');
                var isEnabled = urlCheckbox && urlCheckbox.checked;
                
                newGroup.innerHTML = 
                    '<input type="url" class="doc-gen-url-input doc-gen-input" ' +
                    'placeholder="例如：https://mp.weixin.qq.com/s/xxxxx" ' +
                    (isEnabled ? '' : 'disabled') + ' style="flex: 1;">' +
                    '<button type="button" class="doc-gen-url-remove-btn" title="删除此URL">-</button>';
                
                container.appendChild(newGroup);
                
                // 为新输入框添加事件监听
                var newInput = newGroup.querySelector('.doc-gen-url-input');
                if (newInput) {
                    newInput.addEventListener('input', debounce(function() {
                        updateDocumentGenerationSubmitState();
                    }, 300));
                }
            }
            
            // 删除URL输入框
            if (e.target.classList.contains('doc-gen-url-remove-btn')) {
                var groups = container.querySelectorAll('.doc-gen-url-group');
                if (groups.length > 1) {
                    e.target.closest('.doc-gen-url-group').remove();
                    updateDocumentGenerationSubmitState();
                } else {
                    if (typeof window.addNotification === 'function') {
                        window.addNotification('至少需要保留一个URL输入框', 'warning');
                    }
                }
            }
        });

        // 为初始输入框添加事件监听
        var initialInput = container.querySelector('.doc-gen-url-input');
        if (initialInput) {
            initialInput.addEventListener('input', debounce(function() {
                updateDocumentGenerationSubmitState();
            }, 300));
        }
    }

    function toggleDocumentGenerationLoading(isLoading) {
        var startBtn = document.getElementById('docGenStartBtn');
        if (startBtn) {
            startBtn.disabled = isLoading;
            if (isLoading) {
                if (!startBtn.dataset.originalText) {
                    startBtn.dataset.originalText = startBtn.textContent;
                }
                startBtn.textContent = '生成中...';
            } else {
                startBtn.textContent = startBtn.dataset.originalText || '开始生成';
            }
        }
        var resultContainer = document.getElementById('docGenResult');
        if (resultContainer) {
            if (isLoading) {
                resultContainer.innerHTML = '<div class="doc-gen-message">文档生成中，请稍候...</div>';
            }
        }
    }

    function renderDocumentGenerationResult(data) {
        var resultContainer = document.getElementById('docGenResult');
        if (!resultContainer) return;
        resultContainer.innerHTML = '';
        if (!data) {
            resultContainer.innerHTML = '<div class="doc-gen-message error">未收到返回结果。</div>';
            return;
        }
        var results = Array.isArray(data.results) ? data.results : [];
        if (results.length === 0) {
            var message = data.message || '文档生成未返回可用结果。';
            resultContainer.innerHTML = '<div class="doc-gen-message error">' + (window.escapeHtml ? window.escapeHtml(message) : message) + '</div>';
            return;
        }
        var table = document.createElement('table');
        table.className = 'doc-gen-result-table';
        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        ['源名称', '状态', '说明', 'Token', '下载'].forEach(function(text) {
            var th = document.createElement('th');
            th.textContent = text;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        results.forEach(function(item) {
            var tr = document.createElement('tr');
            var nameTd = document.createElement('td');
            nameTd.textContent = item.original_name || item.generated_name || '-';
            var statusTd = document.createElement('td');
            statusTd.textContent = item.status || '-';
            var messageTd = document.createElement('td');
            messageTd.textContent = item.message || '-';
            
            // Token列
            var tokenTd = document.createElement('td');
            if (item.token_usage && item.token_usage.description) {
                // 使用详细描述
                tokenTd.textContent = item.token_usage.description;
            } else if (item.token_usage && item.token_usage.total) {
                // 兼容旧格式：只显示总数
                var total = item.token_usage.total.total || 0;
                if (total === 0) {
                    tokenTd.textContent = '0（缓存）';
                } else {
                    tokenTd.textContent = total.toString();
                }
            } else {
                tokenTd.textContent = '-';
            }
            
            var actionTd = document.createElement('td');
            if (item.download_url) {
                var link = document.createElement('a');
                link.href = item.download_url;
                link.textContent = '下载';
                link.className = 'doc-gen-download-link';
                link.target = '_blank';
                actionTd.appendChild(link);
            } else {
                actionTd.textContent = '-';
            }
            tr.appendChild(nameTd);
            tr.appendChild(statusTd);
            tr.appendChild(messageTd);
            tr.appendChild(tokenTd);
            tr.appendChild(actionTd);
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        resultContainer.appendChild(table);
    }

    function clearDocumentGenerationInputs() {
        var localCheckbox = document.getElementById('docGenUseLocalFile');
        var localFileInput = document.getElementById('docGenLocalFile');
        var urlCheckbox = document.getElementById('docGenUseUrl');
        var urlInput = document.getElementById('docGenUrlInput');
        var nameEl = document.getElementById('docGenLocalFileName');
        if (localCheckbox) localCheckbox.checked = false;
        if (localFileInput) {
            localFileInput.value = '';
            localFileInput.disabled = true;
        }
        if (urlCheckbox) urlCheckbox.checked = false;
        if (urlInput) {
            urlInput.value = '';
            urlInput.disabled = true;
        }
        if (nameEl) nameEl.textContent = '未选择任何文件';
        docGenState.useLocalFile = false;
        docGenState.useUrl = false;
        docGenState.localFile = null;
        docGenState.url = '';
        docGenState.template = 'style_a';
        var templateRadios = document.querySelectorAll('input[name="docGenTemplate"]');
        templateRadios.forEach(function(radio) {
            radio.checked = radio.value === 'style_a';
        });
        currentSelectedDocGenMode = 'ppt';
        var pptBtn = document.getElementById('docGenTabPpt');
        var wordBtn = document.getElementById('docGenTabWord');
        if (pptBtn && wordBtn) {
            pptBtn.classList.add('active');
            wordBtn.classList.remove('active');
        }
        var templateSection = document.getElementById('docGenTemplateSection');
        if (templateSection) {
            templateSection.style.display = 'block';
        }
        var resultContainer = document.getElementById('docGenResult');
        if (resultContainer) {
            resultContainer.innerHTML = '';
        }
        updateDocumentGenerationSubmitState();
    }

    function startDocumentGeneration() {
        var startBtn = document.getElementById('docGenStartBtn');
        if (!startBtn || startBtn.disabled) {
            return;
        }
        var hasLocal = docGenState.useLocalFile && !!docGenState.localFile;
        var hasUrl = docGenState.useUrl && !!docGenState.url;
        if (!hasLocal && !hasUrl) {
            if (typeof window.addNotification === 'function') {
                window.addNotification('请选择至少一种内容来源。', 'warning');
            }
            return;
        }
        var apiInput = document.getElementById('docGenApiUrl');
        var apiUrl = apiInput ? apiInput.value : '';
        if (!apiUrl) {
            if (typeof window.addNotification === 'function') {
                window.addNotification('未配置文档生成功能的接口地址。', 'error');
            }
            return;
        }

        var formData = new FormData();
        formData.append('mode', currentSelectedDocGenMode);
        if (hasLocal && docGenState.localFile) {
            formData.append('source_file', docGenState.localFile);
        }
        if (hasUrl) {
            // 支持多URL：如果有多个URL，发送JSON数组；单个URL保持兼容
            var urls = collectAllUrls();
            if (urls.length > 1) {
                formData.append('source_url', JSON.stringify(urls));
            } else if (urls.length === 1) {
                formData.append('source_url', urls[0]);
            }
            
            // 添加缓存选项
            var useCacheCheckbox = document.getElementById('docGenUseCache');
            var useCache = useCacheCheckbox ? useCacheCheckbox.checked : true;
            formData.append('use_cache', useCache ? 'true' : 'false');
        }
        if (currentSelectedDocGenMode === 'ppt' && docGenState.template) {
            formData.append('template', docGenState.template);
        }

        var csrfToken = typeof window.getCookie === 'function' ? window.getCookie('csrftoken') : null;
        startBtn.disabled = true;
        if (!startBtn.dataset.originalText) {
            startBtn.dataset.originalText = startBtn.textContent;
        }
        startBtn.textContent = '生成中...';
        window.isConverting = true;
        if (typeof window.updateMainNavigationButtonStates === 'function') {
            window.updateMainNavigationButtonStates(true);
        }
        if (typeof window.updateMainTabButtonsState === 'function') {
            window.updateMainTabButtonsState(true);
        }
        toggleDocumentGenerationLoading(true);

        fetch(apiUrl, {
            method: 'POST',
            headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
            body: formData
        }).then(function(response) {
            return response.text().then(function(text) {
                var data = {};
                try {
                    data = text ? JSON.parse(text) : {};
                } catch (error) {
                    if (typeof window.addNotification === 'function') {
                        window.addNotification('返回数据无法解析。', 'error');
                    }
                    renderDocumentGenerationResult({ message: '返回数据无法解析。' });
                    throw error;
                }
                if (!response.ok) {
                    var message = data && data.message ? data.message : ('请求失败，状态码 ' + response.status);
                    if (typeof window.addNotification === 'function') {
                        window.addNotification(message, 'error');
                    }
                    renderDocumentGenerationResult({ message: message });
                    throw new Error(message);
                }
                renderDocumentGenerationResult(data);
                if (typeof window.addNotification === 'function') {
                    window.addNotification('文档生成任务已完成。', 'success');
                }
            });
        }).catch(function(error) {
            console.error('Document generation request failed:', error);
            if (typeof window.addNotification === 'function') {
                window.addNotification('文档生成请求发生异常，请稍后重试。', 'error');
            }
            renderDocumentGenerationResult({ message: '文档生成请求发生异常。' });
        }).finally(function() {
            window.isConverting = false;
            if (typeof window.updateMainNavigationButtonStates === 'function') {
                window.updateMainNavigationButtonStates(false);
            }
            if (typeof window.updateMainTabButtonsState === 'function') {
                window.updateMainTabButtonsState(false);
            }
            toggleDocumentGenerationLoading(false);
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.textContent = startBtn.dataset.originalText || '开始生成';
            }
        });
    }

    function initializeDocumentGenerationControls() {
        if (docGenInitialized) {
            return;
        }
        var docGenContainer = document.getElementById('documentGenerationContent');
        if (!docGenContainer) {
            return;
        }
        var tabButtons = docGenContainer.querySelectorAll('.tabs .tab-button');
        Array.prototype.forEach.call(tabButtons, function(button) {
            button.addEventListener('click', function() {
                if (window.isConverting) {
                    if (typeof window.addNotification === 'function') {
                        window.addNotification('当前有任务执行中，暂不可切换模式。', 'warning');
                    }
                    return;
                }
                switchDocumentGenerationMode(button.getAttribute('data-mode'));
            });
        });

        var localCheckbox = document.getElementById('docGenUseLocalFile');
        var localFileInput = document.getElementById('docGenLocalFile');
        var urlCheckbox = document.getElementById('docGenUseUrl');
        var urlInput = document.getElementById('docGenUrlInput');
        var startBtn = document.getElementById('docGenStartBtn');
        var templateRadios = document.querySelectorAll('input[name="docGenTemplate"]');
        var urlDebouncedHandler = debounce(function() {
            docGenState.url = urlInput ? urlInput.value.trim() : '';
            updateDocumentGenerationSubmitState();
        }, 300);

        if (localCheckbox && localFileInput) {
            localCheckbox.addEventListener('change', function() {
                docGenState.useLocalFile = localCheckbox.checked;
                if (!localCheckbox.checked) {
                    localFileInput.value = '';
                    docGenState.localFile = null;
                    var nameEl = document.getElementById('docGenLocalFileName');
                    if (nameEl) nameEl.textContent = '未选择任何文件';
                }
                localFileInput.disabled = !localCheckbox.checked;
                updateDocumentGenerationSubmitState();
            });
            localFileInput.addEventListener('change', function() {
                var file = localFileInput.files && localFileInput.files[0] ? localFileInput.files[0] : null;
                var nameEl = document.getElementById('docGenLocalFileName');
                if (!file) {
                    docGenState.localFile = null;
                    if (nameEl) nameEl.textContent = '未选择任何文件';
                } else {
                    if (file.size > 500 * 1024 * 1024) {
                        if (typeof window.addNotification === 'function') {
                            window.addNotification('本地文件不可超过500MB。', 'error');
                        }
                        localFileInput.value = '';
                        docGenState.localFile = null;
                        if (nameEl) nameEl.textContent = '未选择任何文件';
                    } else {
                        docGenState.localFile = file;
                        if (nameEl) nameEl.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
                    }
                }
                updateDocumentGenerationSubmitState();
            });
        }

        if (urlCheckbox) {
            urlCheckbox.addEventListener('change', function() {
                docGenState.useUrl = urlCheckbox.checked;
                var urlInputs = document.querySelectorAll('.doc-gen-url-input');
                var addBtn = document.querySelector('.doc-gen-url-add-btn');
                
                Array.prototype.forEach.call(urlInputs, function(input) {
                    input.disabled = !urlCheckbox.checked;
                    if (!urlCheckbox.checked) {
                        input.value = '';
                    }
                });
                
                if (addBtn) {
                    addBtn.disabled = !urlCheckbox.checked;
                }
                
                if (!urlCheckbox.checked) {
                    docGenState.urls = [];
                    docGenState.url = '';
                }
                
                updateDocumentGenerationSubmitState();
            });
        }

        // 多URL输入框管理
        initializeMultiUrlInputs();

        Array.prototype.forEach.call(templateRadios, function(radio) {
            radio.addEventListener('change', function() {
                if (radio.checked) {
                    docGenState.template = radio.value;
                }
            });
        });

        if (startBtn) {
            startBtn.addEventListener('click', startDocumentGeneration);
        }

        switchDocumentGenerationMode(currentSelectedDocGenMode);
        docGenInitialized = true;
        updateDocumentGenerationSubmitState();
    }

    window.initializeDocumentGenerationControls = initializeDocumentGenerationControls;
    window.switchDocumentGenerationMode = switchDocumentGenerationMode;
    window.updateDocumentGenerationSubmitState = updateDocumentGenerationSubmitState;
    window.startDocumentGeneration = startDocumentGeneration;
    window.clearDocumentGenerationInputs = clearDocumentGenerationInputs;

    window.docGenerationModuleInitialized = true;
})();
