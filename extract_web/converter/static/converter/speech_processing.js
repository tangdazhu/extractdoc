// 语音处理相关逻辑
// 依赖 common.js 中的全局变量和工具函数

// 这里只迁移 initializeSpeechTab、showSpeechSubTab、initializeAsrFunctionality、clearAudioFileAndResult 等入口和主逻辑
// 详细实现略，实际迁移时应将 index.js 相关部分整体搬迁

function initializeSpeechTab() {
    const asrSubTabButton = document.querySelector('#speechProcessingContent .sub-tabs button[onclick*="asrContent"]');
    if (asrSubTabButton) {
         showSpeechSubTab('asrContent', asrSubTabButton);
    }
    initializeAsrFunctionality();
    if (typeof initializeTtsFunctionality === 'function') initializeTtsFunctionality();
    if (typeof initializeRealtimeSpeechFunctionality === 'function') initializeRealtimeSpeechFunctionality();
}
window.initializeSpeechTab = initializeSpeechTab;

function showSpeechSubTab(subTabIdToShow, clickedButton) {
    if (window.isConverting) return;
    document.querySelectorAll('#speechProcessingContent .speech-sub-content').forEach(function(subTabDiv) {
        subTabDiv.style.display = 'none';
    });
    document.querySelectorAll('#speechProcessingContent .sub-tabs button').forEach(function(btn) {
        if (!btn.classList.contains('disabled')) {
            btn.classList.remove('active');
        }
    });
    const subTabElementToShow = document.getElementById(subTabIdToShow);
    if (subTabElementToShow) {
        subTabElementToShow.style.display = 'block';
    }
    if (clickedButton && !clickedButton.classList.contains('disabled')) {
        clickedButton.classList.add('active');
    }
    window.currentSelectedSpeechSubTab = subTabIdToShow;
    if (subTabIdToShow === 'ttsContent') {
        setTimeout(() => {
            const startTtsBtn = document.getElementById('startTtsBtn');
            if (startTtsBtn && typeof initializeTtsFunctionality === 'function') {
                initializeTtsFunctionality();
            }
        }, 200);
    } else if (subTabIdToShow === 'realtimeSpeechContent') {
        setTimeout(() => {
            const startRealtimeBtn = document.getElementById('startRealtimeBtn');
            if (startRealtimeBtn && typeof initializeRealtimeSpeechFunctionality === 'function') {
                initializeRealtimeSpeechFunctionality();
            }
        }, 200);
    }
}
window.showSpeechSubTab = showSpeechSubTab;

function clearAudioFileAndResult() {
    const audioUrlInput = document.getElementById('audioUrlInput');
    const asrTranscriptionOutput = document.getElementById('asrTranscriptionOutput');
    const asrErrorOutput = document.getElementById('asrErrorOutput');
    if (audioUrlInput) audioUrlInput.value = '';
    if (asrTranscriptionOutput) asrTranscriptionOutput.textContent = '';
    if (asrErrorOutput) asrErrorOutput.textContent = '';
    const startAsrBtn = document.getElementById('startAsrBtn');
    const clearAsrFieldsBtn = document.getElementById('clearAsrFieldsBtn');
    if(startAsrBtn) startAsrBtn.disabled = false;
    if(clearAsrFieldsBtn) clearAsrFieldsBtn.disabled = false;
    if(audioUrlInput) audioUrlInput.disabled = false;
    const asrLoadingIndicator = document.getElementById('asrLoadingIndicator');
    if(asrLoadingIndicator) asrLoadingIndicator.style.display = 'none';
}
window.clearAudioFileAndResult = clearAudioFileAndResult;

// === 自动搬迁：ASR、TTS、实时语音相关函数 ===

// --- ASR ---
function initializeAsrFunctionality() {
    console.log("[initializeAsrFunctionality] Setting up ASR event listeners.");
    const startAsrBtn = document.getElementById('startAsrBtn');
    const clearAsrBtn = document.getElementById('clearAsrFieldsBtn');
    const audioUrlInput = document.getElementById('audioUrlInput');
    const asrResultTextarea = document.getElementById('asrTranscriptionOutput');
    const asrErrorOutput = document.getElementById('asrErrorOutput');
    const asrLoadingIndicator = document.getElementById('asrLoadingIndicator');
    const hotwordsContainer = document.getElementById('asrHotwordsContainer');
    if (!startAsrBtn || !clearAsrBtn || !audioUrlInput || 
        !asrResultTextarea || !asrErrorOutput || !asrLoadingIndicator || 
        !hotwordsContainer) {
        console.error("[ASR Init] One or more ASR UI elements not found. Functionality may be impaired.");
        return;
    }
    function addNewHotwordRowBelow(currentRowDiv) {
        const newRow = createHotwordRow();
        if (currentRowDiv && currentRowDiv.parentNode) {
            currentRowDiv.parentNode.insertBefore(newRow, currentRowDiv.nextSibling);
        } else {
            hotwordsContainer.appendChild(newRow);
        }
    }
    function createHotwordRow() {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'hotword-row input-group mb-2';
        const textLabel = document.createElement('span');
        textLabel.className = 'hotword-label';
        textLabel.textContent = '热词：';
        rowDiv.appendChild(textLabel);
        const textInput = document.createElement('input');
        textInput.type = 'text';
        textInput.className = 'form-control hotword-text';
        textInput.placeholder = '热词文本';
        rowDiv.appendChild(textInput);
        const weightLabel = document.createElement('span');
        weightLabel.className = 'hotword-label';
        weightLabel.textContent = '权重：';
        rowDiv.appendChild(weightLabel);
        const weightInput = document.createElement('input');
        weightInput.type = 'number';
        weightInput.className = 'form-control hotword-weight';
        weightInput.placeholder = '权重 (1-5整数)';
        weightInput.title = '取值范围为[1, 5]之间的整数，如果效果不明显可以适当增加权重，但是当权重较大时可能会引起负面效果，导致其他词语识别不准确';
        weightInput.min = '1';
        weightInput.value = '4';
        rowDiv.appendChild(weightInput);
        const langLabel = document.createElement('span');
        langLabel.className = 'hotword-label';
        langLabel.textContent = '语言：';
        rowDiv.appendChild(langLabel);
        const langSelect = document.createElement('select');
        langSelect.className = 'form-select hotword-lang';
        const optZh = document.createElement('option');
        optZh.value = 'zh';
        optZh.textContent = '中文 (zh)';
        langSelect.appendChild(optZh);
        const optEn = document.createElement('option');
        optEn.value = 'en';
        optEn.textContent = '英文 (en)';
        langSelect.appendChild(optEn);
        langSelect.value = 'zh';
        rowDiv.appendChild(langSelect);
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger btn-sm remove-hotword-btn';
        removeBtn.innerHTML = '-';
        removeBtn.title = '移除此热词行';
        removeBtn.onclick = function() {
            const parentContainer = rowDiv.parentNode;
            rowDiv.remove();
            if (parentContainer && parentContainer.children.length === 0) {
                addNewHotwordRowBelow(null);
            }
        };
        rowDiv.appendChild(removeBtn);
        const addInlineBtn = document.createElement('button');
        addInlineBtn.type = 'button';
        addInlineBtn.className = 'btn btn-success btn-sm add-hotword-inline-btn ms-1';
        addInlineBtn.innerHTML = '+';
        addInlineBtn.title = '在此行下方添加新热词行';
        addInlineBtn.onclick = function() {
            addNewHotwordRowBelow(rowDiv);
        };
        rowDiv.appendChild(addInlineBtn);
        return rowDiv;
    }
    addNewHotwordRowBelow(null);
    startAsrBtn.addEventListener('click', async function() {
        const audioUrl = audioUrlInput.value.trim();
        if (!audioUrl) {
            asrErrorOutput.textContent = '请输入有效的音频文件URL。';
            window.addNotification('请输入有效的音频文件URL。', 'error');
            return;
        }
        const hotwordsConfig = [];
        const hotwordRows = hotwordsContainer.querySelectorAll('.hotword-row');
        let hotwordValidationError = false;
        hotwordRows.forEach(row => {
            const text = row.querySelector('.hotword-text').value.trim();
            const weightStr = row.querySelector('.hotword-weight').value.trim();
            const lang = row.querySelector('.hotword-lang').value;
            if (text) {
                const weight = parseInt(weightStr, 10);
                if (isNaN(weight) || weight < 1) {
                    asrErrorOutput.textContent = `热词 \"${text}\" 的权重无效，请输入大于0的整数。`;
                    window.addNotification(`热词 \"${text}\" 的权重无效。`, 'error');
                    hotwordValidationError = true;
                    return;
                }
                hotwordsConfig.push({ text, weight, lang });
            }
        });
        if (hotwordValidationError) return;
        asrResultTextarea.value = '';
        asrErrorOutput.textContent = '';
        asrLoadingIndicator.style.display = 'flex';
        startAsrBtn.disabled = true;
        clearAsrBtn.disabled = true;
        audioUrlInput.disabled = true;
        hotwordRows.forEach(row => {
            row.querySelectorAll('input, select, button').forEach(el => el.disabled = true);
        });
        try {
            const payload = { audio_url: audioUrl };
            if (hotwordsConfig.length > 0) {
                payload.hotwords_config = hotwordsConfig;
            }
            console.log("[ASR] Starting recognition for URL:", audioUrl, "Hotwords Config:", hotwordsConfig);
            const response = await fetch("/api/speech-to-text/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCookie('csrftoken')
                },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            console.log("[ASR] Received response:", result);
            if (response.ok && result.results && result.results.length > 0 && result.results[0].status === 'success') {
                asrResultTextarea.value = result.results[0].transcription || '(未识别到文本)';
                if (result.duration_seconds !== undefined) {
                     console.log(`[ASR] Request ${result.request_id} completed in ${result.duration_seconds}s.`);
                     window.addNotification(`语音识别成功 (用时 ${result.duration_seconds}s)`, 'success');
                } else {
                    window.addNotification('语音识别成功!', 'success');
                }
            } else {
                const errorMsg = (result.results && result.results.length > 0 && result.results[0].message) || result.message || '语音识别失败，请检查URL或稍后再试。';
                asrErrorOutput.textContent = errorMsg;
                window.addNotification(`语音识别失败: ${errorMsg}`, 'error');
                if (result.duration_seconds !== undefined) {
                    console.error(`[ASR] Request ${result.request_id} failed in ${result.duration_seconds}s. Message: ${result.message}`);
                }
            }
        } catch (error) {
            console.error('[ASR] API call failed:', error);
            const networkErrorMsg = '调用语音识别服务时发生网络或未知错误。请查看控制台获取详情。';
            asrErrorOutput.textContent = networkErrorMsg;
            window.addNotification(networkErrorMsg, 'error');
        } finally {
            asrLoadingIndicator.style.display = 'none';
            startAsrBtn.disabled = false;
            clearAsrBtn.disabled = false;
            audioUrlInput.disabled = false;
            hotwordRows.forEach(row => {
                 row.querySelectorAll('input, select, button').forEach(el => el.disabled = false);
            });
        }
    });
    if (clearAsrBtn) {
        clearAsrBtn.addEventListener('click', function() {
            audioUrlInput.value = '';
            hotwordsContainer.innerHTML = '';
            addNewHotwordRowBelow(null);
            asrResultTextarea.value = '';
            asrErrorOutput.textContent = '';
            asrLoadingIndicator.style.display = 'none';
            startAsrBtn.disabled = false;
            clearAsrBtn.disabled = false;
            audioUrlInput.disabled = false;
            console.log("[ASR] Fields cleared.");
            window.addNotification('ASR输入和结果已清空。', 'info');
        });
    } else {
        console.error("clearAsrFieldsBtn not found during ASR initialization.");
    }
}
window.initializeAsrFunctionality = initializeAsrFunctionality;

// --- TTS ---
function initializeTtsFunctionality() {
    // Prevent multiple initializations
    if (window.ttsInitialized) {
        console.log("[initializeTtsFunctionality] TTS already initialized, skipping.");
        return;
    }
    console.log("[initializeTtsFunctionality] Initializing TTS functionality.");
    const startTtsBtn = document.getElementById('startTtsBtn');
    const clearTtsBtn = document.getElementById('clearTtsBtn');
    const ttsVoiceSelection = document.getElementById('ttsVoiceSelection');
    if (!startTtsBtn || !clearTtsBtn || !ttsVoiceSelection) {
        console.error("[initializeTtsFunctionality] Essential TTS elements not found, aborting initialization.");
        return;
    }
    const ttsTextContainer = document.getElementById('ttsTextContainer');
    const ttsFileContainer = document.getElementById('ttsFileContainer');
    const radioText = document.getElementById('ttsInputTypeText');
    const radioFile = document.getElementById('ttsInputTypeFile');
    const ttsInputText = document.getElementById('ttsInputText');
    const ttsTextCharCount = document.getElementById('ttsTextCharCount');
    const ttsTextWarning = document.getElementById('ttsTextWarning');
    const ttsDropZone = document.getElementById('ttsDropZone');
    const ttsFileInput = document.getElementById('ttsFileInput');
    const ttsFileListUI = document.getElementById('ttsFileList');
    const ttsClearListBtn = document.getElementById('ttsClearListBtn');
    const ttsFileCharCount = document.getElementById('ttsFileCharCount');
    const ttsFileWarning = document.getElementById('ttsFileWarning');
    let ttsUploadedFiles = [];
    let totalFileCharCount = 0;
    const ttsResultContainer = document.getElementById('ttsResultContainer');
    const ttsProgressContainer = document.getElementById('ttsProgressContainer');
    const ttsProgressBar = document.getElementById('ttsProgressBar');
    const ttsProgressText = document.getElementById('ttsProgressText');
    const ttsErrorOutput = document.getElementById('ttsErrorOutput');
    const ttsResultsTableContainer = document.getElementById('ttsResultsTableContainer');
    const updateTextCharCount = () => {
        const text = ttsInputText.value;
        const charCount = text.length;
        ttsTextCharCount.textContent = `字数: ${charCount}`;
        if (charCount > 5000) {
            ttsTextWarning.style.display = 'inline';
            ttsTextWarning.style.color = '#dc3545';
            ttsTextWarning.style.fontWeight = 'bold';
            ttsTextCharCount.className = 'text-danger small';
            ttsTextCharCount.style.color = '#dc3545';
            if (startTtsBtn) {
                startTtsBtn.disabled = true;
                startTtsBtn.style.backgroundColor = '#6c757d';
                startTtsBtn.style.borderColor = '#6c757d';
                startTtsBtn.style.cursor = 'not-allowed';
            }
        } else {
            ttsTextWarning.style.display = 'none';
            ttsTextCharCount.className = 'text-muted small';
            ttsTextCharCount.style.color = '';
            if (startTtsBtn && radioText.checked) {
                startTtsBtn.disabled = false;
                startTtsBtn.style.backgroundColor = '#007bff';
                startTtsBtn.style.borderColor = '#007bff';
                startTtsBtn.style.cursor = 'pointer';
            }
        }
    };
    const updateFileCharCount = () => {
        ttsFileCharCount.textContent = `字数: ${totalFileCharCount}`;
        if (totalFileCharCount > 5000) {
            ttsFileWarning.style.display = 'inline';
            ttsFileWarning.style.color = '#dc3545';
            ttsFileWarning.style.fontWeight = 'bold';
            ttsFileCharCount.className = 'text-danger small';
            ttsFileCharCount.style.color = '#dc3545';
            if (startTtsBtn) {
                startTtsBtn.disabled = true;
                startTtsBtn.style.backgroundColor = '#6c757d';
                startTtsBtn.style.borderColor = '#6c757d';
                startTtsBtn.style.cursor = 'not-allowed';
            }
        } else {
            ttsFileWarning.style.display = 'none';
            ttsFileCharCount.className = 'text-muted small';
            ttsFileCharCount.style.color = '';
            if (startTtsBtn && radioFile.checked) {
                startTtsBtn.disabled = false;
                startTtsBtn.style.backgroundColor = '#007bff';
                startTtsBtn.style.borderColor = '#007bff';
                startTtsBtn.style.cursor = 'pointer';
            }
        }
    };
    if (ttsInputText) {
        ttsInputText.addEventListener('input', updateTextCharCount);
        ttsInputText.addEventListener('paste', () => {
            setTimeout(updateTextCharCount, 10);
        });
        updateTextCharCount();
    }
    const handleTtsInputSwitch = () => {
        if (radioText.checked) {
            ttsTextContainer.style.display = 'block';
            ttsFileContainer.style.display = 'none';
            updateTextCharCount();
        } else {
            ttsTextContainer.style.display = 'none';
            ttsFileContainer.style.display = 'block';
            updateFileCharCount();
        }
    };
    radioText.addEventListener('change', handleTtsInputSwitch);
    radioFile.addEventListener('change', handleTtsInputSwitch);
    const handleTtsFiles = (files) => {
        [...files].forEach(file => {
            if ([
                'text/plain',
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ].includes(file.type) || 
                file.name.endsWith('.txt') || file.name.endsWith('.pdf') || file.name.endsWith('.docx')) {
                ttsUploadedFiles.push(file);
                let estimatedChars = 0;
                if (file.name.endsWith('.txt') || file.type === 'text/plain') {
                    estimatedChars = file.size;
                } else if (file.name.endsWith('.pdf')) {
                    estimatedChars = Math.floor(file.size / 2);
                } else if (file.name.endsWith('.docx')) {
                    estimatedChars = Math.floor(file.size / 3);
                }
                totalFileCharCount += estimatedChars;
            } else {
                window.addNotification(`不支持的文件类型: ${file.name}`, 'warning');
            }
        });
        updateTtsFileList();
        updateFileCharCount();
    };
    const updateTtsFileList = () => {
        ttsFileListUI.innerHTML = '';
        ttsUploadedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.innerHTML = `<span>${window.escapeHtml(file.name)}</span>`;
            ttsFileListUI.appendChild(li);
        });
    };
    ttsDropZone.addEventListener('click', () => ttsFileInput.click());
    ttsFileInput.addEventListener('change', (e) => handleTtsFiles(e.target.files));
    ['dragover', 'drop'].forEach(eventName => {
        ttsDropZone.addEventListener(eventName, e => e.preventDefault());
    });
    ttsDropZone.addEventListener('dragenter', () => ttsDropZone.classList.add('border-primary'));
    ttsDropZone.addEventListener('dragleave', () => ttsDropZone.classList.remove('border-primary'));
    ttsDropZone.addEventListener('drop', (e) => {
        ttsDropZone.classList.remove('border-primary');
        handleTtsFiles(e.dataTransfer.files);
    });
    ttsClearListBtn.addEventListener('click', () => {
        ttsUploadedFiles = [];
        totalFileCharCount = 0;
        ttsFileInput.value = '';
        updateTtsFileList();
        updateFileCharCount();
    });
    if (startTtsBtn) {
        startTtsBtn.addEventListener('click', async function() {
            const inputType = radioText.checked ? 'text' : 'file';
            const text = ttsInputText.value.trim();
            const voice = ttsVoiceSelection.value;
            if (inputType === 'text' && !text) {
                window.addNotification('请输入要转换的文本。', 'warning');
                return;
            }
            if (inputType === 'file' && ttsUploadedFiles.length === 0) {
                window.addNotification('请至少上传一个文件。', 'warning');
                return;
            }
            const resultsTableBody = document.getElementById('ttsResultsTableBody');
            if (resultsTableBody) {
                resultsTableBody.innerHTML = '';
            } else {
                ttsResultsTableContainer.innerHTML = '';
            }
            ttsResultContainer.style.display = 'block';
            ttsProgressContainer.style.display = 'block';
            ttsErrorOutput.style.display = 'none';
            updateProgressBar('10%', '正在准备转换...');
            const formData = new FormData();
            formData.append('voice_model', voice);
            if (inputType === 'text') {
                formData.append('text_input', text);
            } else {
                ttsUploadedFiles.forEach(file => formData.append('file_input', file));
            }
            try {
                setTimeout(() => updateProgressBar('40%', '正在上传和提取文本...'), 500);
                const response = await fetch('/api/tts/', {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-CSRFToken': window.getCookie('csrftoken') },
                })
                updateProgressBar('75%', '服务器正在合成音频...');
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ message: '服务器返回了非JSON格式的错误响应。' }));
                    throw new Error(errorData.message || `服务器错误，状态码: ${response.status}`);
                }
                const result = await response.json();
                updateProgressBar('100%', '处理完成！');
                setTimeout(() => {
                    ttsProgressContainer.style.display = 'none';
                    displayTtsResults(result);
                }, 500);
            } catch (error) {
                console.error('TTS Error:', error);
                ttsProgressContainer.style.display = 'none';
                ttsErrorOutput.textContent = `转换失败: ${error.message}`;
                ttsErrorOutput.style.display = 'block';
                window.addNotification(`转换失败: ${error.message}`, 'error');
            }
        });
    }
    if (clearTtsBtn) {
        clearTtsBtn.addEventListener('click', function() {
            ttsInputText.value = '';
            ttsUploadedFiles = [];
            totalFileCharCount = 0;
            ttsFileInput.value = '';
            updateTtsFileList();
            updateTextCharCount();
            updateFileCharCount();
            ttsResultContainer.style.display = 'none';
            ttsErrorOutput.style.display = 'none';
            ttsResultsTableContainer.innerHTML = '';
            if (startTtsBtn) {
                startTtsBtn.disabled = false;
                startTtsBtn.style.backgroundColor = '#007bff';
                startTtsBtn.style.borderColor = '#007bff';
                startTtsBtn.style.cursor = 'pointer';
            }
        });
    }
    function updateProgressBar(percentage, text) {
        const progressBar = document.getElementById('ttsProgressBar');
        const progressText = document.getElementById('ttsProgressText');
        if(progressBar && progressText) {
            progressBar.style.width = percentage;
            progressBar.setAttribute('aria-valuenow', percentage.replace('%', ''));
            progressText.textContent = text;
        }
    }
    function displayTtsResults(data) {
        console.log("[displayTtsResults] Rendering data:", data);
        const container = document.getElementById('ttsResultsTableContainer');
        if (!container) {
            console.error('TTS Results container not found!');
            window.addNotification('发生UI错误：无法找到结果显示区域。', 'error');
            return;
        }
        container.innerHTML = '';
        if (data.duration_seconds !== undefined) {
            const overallDurationP = document.createElement('p');
            overallDurationP.className = 'text-muted small mb-2';
            overallDurationP.textContent = `总处理时长: ${data.duration_seconds} 秒`;
            container.appendChild(overallDurationP);
        }
        if (data.error) {
            let errorMessage = `<p class="text-danger">处理失败: ${window.escapeHtml(data.error)}</p>`;
            container.innerHTML += errorMessage;
            return;
        }
        if (!data.results || data.results.length === 0) {
            container.innerHTML += '<p class="no-files">没有转换结果。</p>';
            return;
        }
        container.className = 'converted-files-container';
        const table = document.createElement('table');
        table.className = 'table table-striped table-bordered';
        table.style.borderCollapse = 'collapse';
        const thead = document.createElement('thead');
        thead.innerHTML = '<tr>' +
                            '<th>原始文件名</th>' +
                            '<th>转换后文件名</th>' +
                            '<th>状态</th>' +
                            '<th>消息/下载</th>' +
                        '</tr>';
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        data.results.forEach(result => {
            const row = tbody.insertRow();
            row.insertCell().textContent = result.original_name || 'N/A';
            row.insertCell().textContent = result.converted_name || 'N/A';
            const statusCell = row.insertCell();
            const statusBadge = document.createElement('span');
            statusBadge.classList.add('status-badge');
            statusBadge.textContent = result.status;
            if (result.status === 'success' || result.status === 'success_fallback') {
                statusBadge.classList.add('status-success');
            } else if (result.status === 'error' || (typeof result.status === 'string' && result.status.includes('_error'))) {
                statusBadge.classList.add('status-error');
            } else {
                statusBadge.classList.add('status-processing');
            }
            statusCell.appendChild(statusBadge);
            const actionCell = row.insertCell();
            if (result.status === 'success' || result.status === 'success_fallback') {
                if (result.download_url) {
                    const downloadLink = document.createElement('a');
                    downloadLink.href = result.download_url;
                    downloadLink.textContent = '下载';
                    downloadLink.className = 'download-link';
                    downloadLink.target = '_blank';
                    actionCell.appendChild(downloadLink);
                } else {
                    actionCell.textContent = result.message || '-';
                }
            } else {
                actionCell.textContent = result.message || '未知错误';
            }
        });
        table.appendChild(tbody);
        container.appendChild(table);
    }
    window.ttsInitialized = true;
    console.log("[initializeTtsFunctionality] TTS functionality initialized successfully.");
}
window.initializeTtsFunctionality = initializeTtsFunctionality;

// --- 实时语音 ---
let realtimeSpeechSession = null;
let audioChunks = [];
let audioContext = null;
let analyser = null;
let microphone = null;
let isRealtimeRecording = false;
let recognitionResults = [];
let pollingInterval = null;
let scriptProcessor = null;
function initializeRealtimeSpeechFunctionality() {
    console.log('Initializing real-time speech recognition functionality');
    const startBtn = document.getElementById('startRealtimeBtn');
    const stopBtn = document.getElementById('stopRealtimeBtn');
    const clearBtn = document.getElementById('clearRealtimeBtn');
    if (!startBtn || !stopBtn || !clearBtn) {
        console.error('Real-time speech buttons not found');
        return;
    }
    startBtn.addEventListener('click', startRealtimeRecognition);
    stopBtn.addEventListener('click', stopRealtimeRecognition);
    clearBtn.addEventListener('click', clearRealtimeResults);
    console.log('Real-time speech recognition functionality initialized');
}
window.initializeRealtimeSpeechFunctionality = initializeRealtimeSpeechFunctionality;
async function startRealtimeRecognition() {
    console.log('Starting real-time speech recognition');
    try {
        if (isRealtimeRecording) {
            console.log('Already recording');
            return;
        }
        const languageHints = getSelectedLanguages();
        if (languageHints.length === 0) {
            showRealtimeError('请至少选择一种识别语言');
            return;
        }
        updateRealtimeStatus('正在获取麦克风权限...', true);
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            } 
        });
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        analyser = audioContext.createAnalyser();
        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        microphone.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);
        scriptProcessor.onaudioprocess = function(e) {
            if (!isRealtimeRecording) return;
            const input = e.inputBuffer.getChannelData(0);
            let pcm = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                let s = Math.max(-1, Math.min(1, input[i]));
                pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            sendAudioData(pcm.buffer);
        };
        updateRealtimeStatus('正在启动识别服务...', true);
        const sessionResponse = await fetch('/api/realtime-speech/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCookie('csrftoken')
            },
            body: JSON.stringify({ language_hints: languageHints })
        });
        if (!sessionResponse.ok) {
            throw new Error(`HTTP error! status: ${sessionResponse.status}`);
        }
        const sessionData = await sessionResponse.json();
        if (sessionData.status !== 'success') {
            throw new Error(sessionData.error || 'Failed to start recognition session');
        }
        realtimeSpeechSession = sessionData.session_id;
        isRealtimeRecording = true;
        document.getElementById('startRealtimeBtn').style.display = 'none';
        document.getElementById('stopRealtimeBtn').style.display = 'inline-block';
        document.getElementById('audioLevelContainer').style.display = 'block';
        updateRealtimeStatus('正在录音中...', true);
        clearRealtimeResults();
        monitorAudioLevel(dataArray);
        startResultPolling();
        console.log('Real-time recognition started successfully');
    } catch (error) {
        console.error('Error starting real-time recognition:', error);
        showRealtimeError('启动实时识别失败: ' + error.message);
        stopRealtimeRecognition();
    }
}
async function stopRealtimeRecognition() {
    console.log('Stopping real-time speech recognition');
    try {
        isRealtimeRecording = false;
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        if (scriptProcessor) {
            scriptProcessor.disconnect();
            scriptProcessor.onaudioprocess = null;
            scriptProcessor = null;
        }
        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }
        if (realtimeSpeechSession) {
            updateRealtimeStatus('正在停止识别服务...', true);
            try {
                const response = await fetch(`/api/realtime-speech/stop/${realtimeSpeechSession}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': window.getCookie('csrftoken') }
                });
                if (response.ok) {
                    const data = await response.json();
                    console.log('Recognition session stopped successfully', data);
                    if (data.status === 'success' && data.final_results && data.final_results.length > 0) {
                        processRecognitionResults(data.final_results);
                    }
                } else {
                    console.error('Failed to stop recognition session');
                }
            } catch (error) {
                console.error('Error stopping recognition session:', error);
            }
            realtimeSpeechSession = null;
        }
        document.getElementById('startRealtimeBtn').style.display = 'inline-block';
        document.getElementById('stopRealtimeBtn').style.display = 'none';
        document.getElementById('audioLevelContainer').style.display = 'none';
        document.getElementById('realtimeStatus').style.display = 'none';
        console.log('Real-time recognition stopped');
    } catch (error) {
        console.error('Error stopping real-time recognition:', error);
        showRealtimeError('停止实时识别时出错: ' + error.message);
    }
}
function getSelectedLanguages() {
    const languages = [];
    if (document.getElementById('langZh').checked) languages.push('zh');
    if (document.getElementById('langEn').checked) languages.push('en');
    return languages;
}
async function sendAudioData(arrayBuffer) {
    if (!realtimeSpeechSession || !isRealtimeRecording) {
        return;
    }
    try {
        const response = await fetch(`/api/realtime-speech/audio/${realtimeSpeechSession}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': window.getCookie('csrftoken'),
                'Content-Type': 'application/octet-stream'
            },
            body: arrayBuffer
        });
        if (!response.ok) {
            console.error('Failed to send audio data:', response.status);
        }
    } catch (error) {
        console.error('Error sending audio data:', error);
    }
}
function startResultPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    pollingInterval = setInterval(async () => {
        if (!realtimeSpeechSession || !isRealtimeRecording) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            return;
        }
        try {
            const response = await fetch(`/api/realtime-speech/results/${realtimeSpeechSession}/`, {
                headers: {
                    'X-CSRFToken': window.getCookie('csrftoken')
                }
            });
            if (response.ok) {
                const data = await response.json();
                let results = [];
                if (Array.isArray(data.results) && data.results.length > 0) {
                    results = data.results;
                } else if (Array.isArray(data.final_results) && data.final_results.length > 0) {
                    results = data.final_results;
                }
                if (data.status === 'success' && results.length > 0) {
                    processRecognitionResults(results);
                }
            }
        } catch (error) {
            console.error('Error polling results:', error);
        }
    }, 200);
}
function processRecognitionResults(results) {
    const outputDiv = document.getElementById('realtimeTranscriptionOutput');
    const intermediateDiv = document.getElementById('realtimeIntermediateResults');
    let latestIntermediate = '';
    results.forEach(result => {
        if ((result.type === 'result' || result.type === undefined) && result.text) {
            if (result.is_final) {
                const cleanText = result.text.trim();
                if (cleanText && !recognitionResults.some(r => r.text === cleanText)) {
                    recognitionResults.push({
                        text: cleanText,
                        translation: result.translation || ''
                    });
                }
            } else {
                latestIntermediate = result.text;
            }
        }
    });
    // 只拼接非空内容
    const filtered = recognitionResults.filter(r => r.text && r.text.trim() !== '');
    outputDiv.innerHTML = filtered.map(r =>
        `<span>${window.escapeHtml(r.text)}</span>${r.translation ? `<br><span style='color: #007bff;'>${window.escapeHtml(r.translation)}</span>` : ''}`
    ).join('<br>');
    if (latestIntermediate && latestIntermediate.trim() !== '') {
        intermediateDiv.innerHTML = `<div class="text-info" style="color: #888; font-style: italic;">${window.escapeHtml(latestIntermediate.trim())}</div>`;
    } else {
        intermediateDiv.innerHTML = '';
    }
    outputDiv.scrollTop = outputDiv.scrollHeight;
}
function updateRealtimeOutput() {
    const outputDiv = document.getElementById('realtimeTranscriptionOutput');
    const filtered = recognitionResults.filter(r => r.text && r.text.trim() !== '');
    outputDiv.innerHTML = filtered.map(r =>
        `<span>${window.escapeHtml(r.text)}</span>${r.translation ? `<br><span style='color: #007bff;'>${window.escapeHtml(r.translation)}</span>` : ''}`
    ).join('<br>');
    outputDiv.scrollTop = outputDiv.scrollHeight;
}
function clearRealtimeResults() {
    recognitionResults = [];
    updateRealtimeOutput();
    document.getElementById('realtimeIntermediateResults').innerHTML = '';
    document.getElementById('realtimeErrorOutput').innerHTML = '';
}
function monitorAudioLevel(dataArray) {
    if (!analyser || !isRealtimeRecording) {
        return;
    }
    analyser.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    const level = (average / 255) * 100;
    const levelBar = document.getElementById('audioLevelBar');
    if (levelBar) {
        levelBar.style.width = level + '%';
        if (level > 70) {
            levelBar.className = 'progress-bar bg-danger';
        } else if (level > 30) {
            levelBar.className = 'progress-bar bg-success';
        } else {
            levelBar.className = 'progress-bar bg-info';
        }
    }
    if (isRealtimeRecording) {
        requestAnimationFrame(() => monitorAudioLevel(dataArray));
    }
}
function updateRealtimeStatus(message, show = true) {
    const statusDiv = document.getElementById('realtimeStatus');
    const statusText = document.getElementById('realtimeStatusText');
    if (statusDiv && statusText) {
        statusText.textContent = message;
        statusDiv.style.display = show ? 'block' : 'none';
    }
}
function showRealtimeError(message) {
    const errorDiv = document.getElementById('realtimeErrorOutput');
    if (errorDiv) {
        errorDiv.innerHTML = `<div class="alert alert-danger">${window.escapeHtml(message)}</div>`;
    }
    console.error('Real-time speech error:', message);
    updateRealtimeStatus('', false);
}
// 其余如 initializeAsrFunctionality、initializeTtsFunctionality、initializeRealtimeSpeechFunctionality 及相关事件、全局变量等也应整体迁移
// ...（略） 