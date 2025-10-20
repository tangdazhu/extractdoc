let currentSelectedMainNavigation = 'docConversion'; // Keep track of main navigation
let currentSelectedMainTab = 'imgToFile'; 
let currentSelectedSubTab = 'imgToWord'; 
let currentSelectedSpeechSubTab = 'speechToText'; // For speech processing
let isConverting = false; // General flag for any background process
const uploadedFiles = [];  // For document conversion multi-file
let uploadedVideoFile = null; // For single video file in video analysis
let uploadedAudioFile = null; // For single audio file in speech processing
let docGenInitialized = false;
let currentSelectedDocGenMode = 'ppt';
const docGenState = {
    useLocalFile: false,
    useUrl: false,
    localFile: null,
    url: '',
    template: 'style_a'
};

// Global flag to prevent multiple TTS initializations
let ttsInitialized = false;

// --- Helper function to disable/enable main navigation buttons ---
function updateMainNavigationButtonStates(disableNonActive) {
    const navButtons = document.querySelectorAll('.sidebar-nav li button');
    navButtons.forEach(button => {
        if (disableNonActive) {
            // Disable if not active OR if it IS the active one (to prevent re-click during processing)
            if (button.id !== `nav${currentSelectedMainNavigation.charAt(0).toUpperCase() + currentSelectedMainNavigation.slice(1)}` || 
                button.id === `nav${currentSelectedMainNavigation.charAt(0).toUpperCase() + currentSelectedMainNavigation.slice(1)}`) {
                button.disabled = true;
                button.style.opacity = button.id === `nav${currentSelectedMainNavigation.charAt(0).toUpperCase() + currentSelectedMainNavigation.slice(1)}` ? '1' : '0.5'; // Keep active full opacity but disabled
                button.style.cursor = 'not-allowed';
            }
        } else {
            // Only re-enable non-programmatically-disabled buttons (those without class 'disabled')
            if (!button.classList.contains('disabled')) { 
                button.disabled = false;
                button.style.opacity = '1';
                button.style.cursor = 'pointer';
            }
        }
    });
}

function initializeDocumentGenerationControls() {
    if (docGenInitialized) return;
    const docGenContainer = document.getElementById('documentGenerationContent');
    if (!docGenContainer) return;
    const tabButtons = docGenContainer.querySelectorAll('.tabs .tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (isConverting) {
                addNotification('当前有任务执行中，暂不可切换模式。', 'warning');
                return;
            }
            switchDocumentGenerationMode(button.dataset.mode);
        });
    });
    const localCheckbox = document.getElementById('docGenUseLocalFile');
    const localFileInput = document.getElementById('docGenLocalFile');
    const urlCheckbox = document.getElementById('docGenUseUrl');
    const urlInput = document.getElementById('docGenUrlInput');
    const startBtn = document.getElementById('docGenStartBtn');
    const templateRadios = document.querySelectorAll('input[name="docGenTemplate"]');
    const urlDebouncedHandler = debounce(() => {
        docGenState.url = urlInput ? urlInput.value.trim() : '';
        updateDocumentGenerationSubmitState();
    }, 300);
    if (localCheckbox && localFileInput) {
        localCheckbox.addEventListener('change', () => {
            docGenState.useLocalFile = localCheckbox.checked;
            if (!localCheckbox.checked) {
                localFileInput.value = '';
                docGenState.localFile = null;
                const nameEl = document.getElementById('docGenLocalFileName');
                if (nameEl) nameEl.textContent = '未选择任何文件';
            }
            localFileInput.disabled = !localCheckbox.checked;
            updateDocumentGenerationSubmitState();
        });
        localFileInput.addEventListener('change', () => {
            const file = localFileInput.files && localFileInput.files[0] ? localFileInput.files[0] : null;
            const nameEl = document.getElementById('docGenLocalFileName');
            if (!file) {
                docGenState.localFile = null;
                if (nameEl) nameEl.textContent = '未选择任何文件';
            } else {
                if (file.size > 500 * 1024 * 1024) {
                    addNotification('本地文件不可超过500MB。', 'error');
                    localFileInput.value = '';
                    docGenState.localFile = null;
                    if (nameEl) nameEl.textContent = '未选择任何文件';
                } else {
                    docGenState.localFile = file;
                    if (nameEl) nameEl.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
                }
            }
            updateDocumentGenerationSubmitState();
        });
    }
    if (urlCheckbox && urlInput) {
        urlCheckbox.addEventListener('change', () => {
            docGenState.useUrl = urlCheckbox.checked;
            if (!urlCheckbox.checked) {
                urlInput.value = '';
                docGenState.url = '';
            }
            urlInput.disabled = !urlCheckbox.checked;
            updateDocumentGenerationSubmitState();
        });
        urlInput.addEventListener('input', urlDebouncedHandler);
    }
    if (templateRadios.length > 0) {
        templateRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    docGenState.template = radio.value;
                }
            });
        });
    }
    if (startBtn) {
        startBtn.addEventListener('click', startDocumentGeneration);
    }
    switchDocumentGenerationMode(currentSelectedDocGenMode);
    docGenInitialized = true;
    updateDocumentGenerationSubmitState();
}

function switchDocumentGenerationMode(mode) {
    if (!mode) return;
    currentSelectedDocGenMode = mode;
    const pptBtn = document.getElementById('docGenTabPpt');
    const wordBtn = document.getElementById('docGenTabWord');
    if (pptBtn && wordBtn) {
        pptBtn.classList.toggle('active', mode === 'ppt');
        wordBtn.classList.toggle('active', mode === 'word');
    }
    const templateSection = document.getElementById('docGenTemplateSection');
    if (templateSection) {
        templateSection.style.display = mode === 'ppt' ? 'block' : 'none';
    }
    updateDocumentGenerationSubmitState();
}

function updateDocumentGenerationSubmitState() {
    const startBtn = document.getElementById('docGenStartBtn');
    if (!startBtn) return;
    const hasLocal = docGenState.useLocalFile && !!docGenState.localFile;
    const hasUrl = docGenState.useUrl && !!docGenState.url;
    const validUrl = !docGenState.useUrl || /^https?:\/\//i.test(docGenState.url);
    const ready = (hasLocal || hasUrl) && validUrl;
    startBtn.disabled = !ready;
    if (!validUrl && docGenState.useUrl) {
        addNotification('请输入有效的URL，需以http或https开头。', 'warning');
    }
}

function startDocumentGeneration() {
    const startBtn = document.getElementById('docGenStartBtn');
    if (!startBtn || startBtn.disabled) {
        return;
    }
    const hasLocal = docGenState.useLocalFile && !!docGenState.localFile;
    const hasUrl = docGenState.useUrl && !!docGenState.url;
    if (!hasLocal && !hasUrl) {
        addNotification('请选择至少一种内容来源。', 'warning');
        return;
    }
    const apiInput = document.getElementById('docGenApiUrl');
    const apiUrl = apiInput ? apiInput.value : '';
    if (!apiUrl) {
        addNotification('未配置文档生成功能的接口地址。', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('mode', currentSelectedDocGenMode);
    if (hasLocal && docGenState.localFile) {
        formData.append('source_file', docGenState.localFile);
    }
    if (hasUrl) {
        formData.append('source_url', docGenState.url);
    }
    if (currentSelectedDocGenMode === 'ppt' && docGenState.template) {
        formData.append('template', docGenState.template);
    }
    const csrfToken = getCookie('csrftoken');
    startBtn.disabled = true;
    if (!startBtn.dataset.originalText) {
        startBtn.dataset.originalText = startBtn.textContent;
    }
    startBtn.textContent = '生成中...';
    isConverting = true;
    updateMainNavigationButtonStates(true);
    updateMainTabButtonsState(true);
    toggleDocumentGenerationLoading(true);
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    }).then(async (response) => {
        const text = await response.text();
        let data;
        try {
            data = text ? JSON.parse(text) : {};
        } catch (error) {
            addNotification('返回数据无法解析。', 'error');
            renderDocumentGenerationResult({ message: '返回数据无法解析。' });
            return;
        }
        if (!response.ok) {
            const message = data && data.message ? data.message : `请求失败，状态码 ${response.status}`;
            addNotification(message, 'error');
            renderDocumentGenerationResult({ message });
            return;
        }
        renderDocumentGenerationResult(data);
        addNotification('文档生成任务已完成。', 'success');
    }).catch(error => {
        console.error('Document generation request failed:', error);
        addNotification('文档生成请求发生异常，请稍后重试。', 'error');
        renderDocumentGenerationResult({ message: '文档生成请求发生异常。' });
    }).finally(() => {
        isConverting = false;
        updateMainNavigationButtonStates(false);
        updateMainTabButtonsState(false);
        toggleDocumentGenerationLoading(false);
        if (startBtn.dataset.originalText) {
            startBtn.textContent = startBtn.dataset.originalText;
        }
        updateDocumentGenerationSubmitState();
    });
}

function toggleDocumentGenerationLoading(isLoading) {
    const startBtn = document.getElementById('docGenStartBtn');
    if (startBtn) {
        startBtn.disabled = isLoading;
    }
    const resultContainer = document.getElementById('docGenResult');
    if (!resultContainer) return;
    if (isLoading) {
        resultContainer.innerHTML = '<div class="doc-gen-message">文档生成中，请稍候...</div>';
    }
}

function renderDocumentGenerationResult(data) {
    const resultContainer = document.getElementById('docGenResult');
    if (!resultContainer) return;
    resultContainer.innerHTML = '';
    if (!data) {
        resultContainer.innerHTML = '<div class="doc-gen-message error">未收到返回结果。</div>';
        return;
    }
    const results = Array.isArray(data.results) ? data.results : [];
    if (results.length === 0) {
        const message = data.message || '文档生成未返回可用结果。';
        resultContainer.innerHTML = `<div class="doc-gen-message error">${escapeHtml(message)}</div>`;
        return;
    }
    const table = document.createElement('table');
    table.className = 'doc-gen-result-table';
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['源名称', '状态', '说明', '下载'].forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    results.forEach(item => {
        const tr = document.createElement('tr');
        const nameTd = document.createElement('td');
        nameTd.textContent = item.original_name || item.generated_name || '-';
        const statusTd = document.createElement('td');
        statusTd.textContent = item.status || '-';
        const messageTd = document.createElement('td');
        messageTd.textContent = item.message || '-';
        const actionTd = document.createElement('td');
        if (item.download_url) {
            const link = document.createElement('a');
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
        tr.appendChild(actionTd);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    resultContainer.appendChild(table);
}

function clearDocumentGenerationInputs() {
    const localCheckbox = document.getElementById('docGenUseLocalFile');
    const localFileInput = document.getElementById('docGenLocalFile');
    const urlCheckbox = document.getElementById('docGenUseUrl');
    const urlInput = document.getElementById('docGenUrlInput');
    const nameEl = document.getElementById('docGenLocalFileName');
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
    const templateRadios = document.querySelectorAll('input[name="docGenTemplate"]');
    templateRadios.forEach(radio => {
        radio.checked = radio.value === 'style_a';
    });
    currentSelectedDocGenMode = 'ppt';
    const pptBtn = document.getElementById('docGenTabPpt');
    const wordBtn = document.getElementById('docGenTabWord');
    if (pptBtn && wordBtn) {
        pptBtn.classList.add('active');
        wordBtn.classList.remove('active');
    }
    const templateSection = document.getElementById('docGenTemplateSection');
    if (templateSection) templateSection.style.display = 'block';
    const resultContainer = document.getElementById('docGenResult');
    if (resultContainer) resultContainer.innerHTML = '';
    updateDocumentGenerationSubmitState();
}

function debounce(fn, delay) {
    let timer = null;
    return function(...args) {
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(() => {
            fn.apply(this, args);
        }, delay);
    };
}

// --- NEW --- Helper function to disable/enable main tab buttons
function updateMainTabButtonsState(disableNonActive) {
    const mainTabButtons = document.querySelectorAll('.tabs .tab-button');
    const subTabButtons = document.querySelectorAll('.sub-tabs .sub-tab-button'); // Get all sub-tab buttons

    mainTabButtons.forEach(button => {
        if (disableNonActive) {
            if (!button.classList.contains('active')) {
                button.disabled = true;
                button.style.opacity = '0.5'; 
                button.style.cursor = 'not-allowed';
            } else {
                button.style.cursor = 'not-allowed'; 
            }
        } else {
            button.disabled = false;
            button.style.opacity = '1';
            button.style.cursor = 'pointer';
        }
    });

    subTabButtons.forEach(button => {
        if (disableNonActive) {
            button.disabled = true;
            button.style.opacity = '0.5';
            button.style.cursor = 'not-allowed';
        } else {
            button.disabled = false;
            button.style.opacity = '1';
            button.style.cursor = 'pointer';
        }
    });
}
// --- END NEW ---

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
        
// --- MODIFIED: Simple Notification Function (now only logs to console) ---
function addNotification(message, type) {
    console.log(`Notification (${type.toUpperCase()}): ${message}`);
    // alert(`[${type.toUpperCase()}] ${message}`); // Alert removed
}
// --- END MODIFIED ---

function updateFileUploadAcceptType() {
    const fileUploadInput = document.getElementById('fileUpload');
    let acceptTypes = '';

    // This function is specific to the 'docConversionContent' section's file input
    if (currentSelectedMainNavigation !== 'docConversion' || !fileUploadInput) {
        return;
    }

    switch (currentSelectedMainTab) {
        case 'imgToFile':
            acceptTypes = '.jpg,.jpeg,.png,.bmp';
            break;
        case 'fileToPdf':
            switch (currentSelectedSubTab) {
                case 'wordToPdf':
                    acceptTypes = '.doc,.docx';
                    break;
                case 'excelToPdf':
                    acceptTypes = '.xls,.xlsx';
                    break;
                case 'pptToPdf':
                    acceptTypes = '.ppt,.pptx';
                    break;
                case 'txtToPdf':
                    acceptTypes = '.txt';
                    break;
                default:
                    acceptTypes = ''; 
                    break;
            }
            break;
        case 'pdfToFile':
            acceptTypes = '.pdf';
            break;
        default:
            acceptTypes = ''; 
            break;
    }
    fileUploadInput.accept = acceptTypes;
    console.log("File input accept types updated to: ", acceptTypes);
}

function showTab(tabId) {
    if (isConverting) {
        console.log("[showTab] Conversion in progress. Tab switch prevented.");
        return;
    }
    
    // This function manages tabs within docConversionContent
    if (currentSelectedMainNavigation !== 'docConversion') return;

    if (currentSelectedMainTab !== tabId) { 
        clearFileList();
        clearConvertedFilesList();
    }

    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
    document.getElementById(tabId + 'Content').classList.remove('hidden');

    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.getElementById('btn' + tabId.charAt(0).toUpperCase() + tabId.slice(1)).classList.add('active');
    
    currentSelectedMainTab = tabId;
    const firstSubTabButton = document.getElementById(tabId + 'Content').querySelector('.sub-tab-button');
    if (firstSubTabButton) {
        const onclickAttr = firstSubTabButton.getAttribute('onclick');
        const match = onclickAttr.match(/selectSubTab\(this, '([^']*)'\)/);
        if (match && match[1]) {
             console.log("[showTab] Auto-selecting first sub-tab: ", match[1]);
             selectSubTab(firstSubTabButton, match[1], false); 
        } else {
            console.warn("[showTab] Could not determine subTabType for default selection in main tab: ", tabId, " from onclick: ", onclickAttr);
            currentSelectedSubTab = null;
        }
    } else {
        console.warn("[showTab] No sub-tab buttons found for main tab: ", tabId);
        currentSelectedSubTab = null;
    }
    updateFileUploadAcceptType(); 
    console.log("[showTab] Current main tab: ", currentSelectedMainTab, "Current sub tab: ", currentSelectedSubTab);
    if (typeof updateImgToPptDirectInsertOption === 'function') updateImgToPptDirectInsertOption();
}

function selectSubTab(buttonElement, subTabType, shouldUpdateAccept = true) {
    console.log("[selectSubTab] Called with subTabType: ", subTabType, "Current is: ", currentSelectedSubTab);
    console.log("[selectSubTab] Button element: ", buttonElement);

    // This function manages sub-tabs within docConversionContent
    if (currentSelectedMainNavigation !== 'docConversion') return;

    if (!buttonElement) {
        console.error("[selectSubTab] Error: buttonElement is null or undefined.");
        return;
    }

    // Clear file list and conversion results when switching sub tabs
    if (currentSelectedSubTab !== subTabType) { 
        console.log("[selectSubTab] Different sub-tab selected. Clearing lists.");
        clearFileList();
        clearConvertedFilesList();
        console.log("[selectSubTab] Lists cleared.");
    } else {
        console.log("[selectSubTab] Same sub-tab clicked or re-selected. Lists not cleared.");
    }

    if (buttonElement.parentElement) {
        console.log("[selectSubTab] Parent element of button: ", buttonElement.parentElement);
        const subTabButtons = buttonElement.parentElement.querySelectorAll('.sub-tab-button');
        console.log("[selectSubTab] Found sub-tab buttons: ", subTabButtons);
        
        subTabButtons.forEach(btn => {
            // console.log("[selectSubTab] Removing 'active' from button: ", btn);
            btn.classList.remove('active');
        });
        console.log("[selectSubTab] 'active' class removed from all siblings.");
        
        buttonElement.classList.add('active');
        console.log("[selectSubTab] 'active' class added to clicked button: ", buttonElement);
    } else {
        console.error("[selectSubTab] Error: buttonElement.parentElement is null. Cannot update active classes.");
    }
    
    currentSelectedSubTab = subTabType;
    console.log("[selectSubTab] currentSelectedSubTab updated to: ", currentSelectedSubTab);

    if (shouldUpdateAccept) {
        console.log("[selectSubTab] Updating file upload accept type.");
        updateFileUploadAcceptType();
    } else {
        console.log("[selectSubTab] Skipping file upload accept type update (shouldUpdateAccept=false).");
    }
    console.log("当前选择的转换类型 (sub-tab): ", currentSelectedSubTab);

    // --- NEW: Show/Hide PDF conversion options ---
    const pdfToWordOptionsDiv = document.getElementById('pdfToWordOptions');
    const pdfToExcelOptionsDiv = document.getElementById('pdfToExcelOptions');
    const pdfToTxtOptionsDiv = document.getElementById('pdfToTxtOptions');
    const pdfToPptOptionsDiv = document.getElementById('pdfToPptOptions');
    const pdfMergeOptionDiv = document.getElementById('pdfMergeOption');
    
    // Hide all PDF options first
    [pdfToWordOptionsDiv, pdfToExcelOptionsDiv, pdfToTxtOptionsDiv, pdfToPptOptionsDiv, pdfMergeOptionDiv].forEach(div => {
        div.classList.add('hidden');
    });
      // Show the appropriate options based on current selection
    if (currentSelectedMainTab === 'pdfToFile') {
        let targetOptionsDiv = null;
        
        switch (currentSelectedSubTab) {
            case 'pdfToWord':
                targetOptionsDiv = pdfToWordOptionsDiv;
                console.log("[selectSubTab] PDF to Word options SHOWN");
                break;
            case 'pdfToExcel':
                targetOptionsDiv = pdfToExcelOptionsDiv;
                console.log("[selectSubTab] PDF to Excel options SHOWN");
                break;
            case 'pdfToTxt':
                targetOptionsDiv = pdfToTxtOptionsDiv;
                console.log("[selectSubTab] PDF to TXT options SHOWN");
                break;
            case 'pdfToPpt':
                targetOptionsDiv = pdfToPptOptionsDiv;
                console.log("[selectSubTab] PDF to PPT options SHOWN");
                break;
        }
        
        if (targetOptionsDiv) {
            targetOptionsDiv.classList.remove('hidden');
            targetOptionsDiv.style.display = 'flex'; // Explicitly set display to flex
        }
        
        // Always show the merge option for PDF conversions
        pdfMergeOptionDiv.classList.remove('hidden');
        pdfMergeOptionDiv.style.display = 'block';
        console.log("[selectSubTab] PDF merge option SHOWN");
    } else if (currentSelectedMainTab === 'imgToFile') {
        // Show merge option for image conversions too
        pdfMergeOptionDiv.classList.remove('hidden');
        pdfMergeOptionDiv.style.display = 'block';
        console.log("[selectSubTab] Image merge option SHOWN");
    } else {
        console.log("[selectSubTab] All PDF options HIDDEN");
    }
    // --- END NEW ---
    if (typeof updateImgToPptDirectInsertOption === 'function') updateImgToPptDirectInsertOption();
}

// Function to add styling to the file list items dynamically
function renderFileList() {
    const fileListUI = document.getElementById('fileList');
    fileListUI.innerHTML = ''; // Clear existing list items
    uploadedFiles.forEach((file, index) => {
        const listItem = document.createElement('li');
        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-file-btn';
        removeBtn.innerHTML = '&times;'; // Multiplication sign as a simple 'x'
        removeBtn.title = '移除文件';
        removeBtn.onclick = function() { 
            uploadedFiles.splice(index, 1); // Remove file from array
            renderFileList(); // Re-render the list
        };
        
        listItem.appendChild(fileNameSpan);
        listItem.appendChild(removeBtn);
        fileListUI.appendChild(listItem);
    });
}

// Modify handleFiles to use renderFileList
function handleFiles(incomingFiles) {
    const fileListUI = document.getElementById('fileList');
    const maxFiles = 10;
    const maxFileSize = 500 * 1024 * 1024; // 500MB

    for (const file of incomingFiles) {
        if (uploadedFiles.length >= maxFiles) {
            alert(`最多只能上传 ${maxFiles} 个文件。`);
            break;
        }
        if (file.size > maxFileSize) {
            alert(`文件 "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)} MB) 超过了500MB的大小限制。`);
            continue;
        }
        // Check for duplicate file names before adding
        if (!uploadedFiles.some(f => f.name === file.name)) {
             uploadedFiles.push(file);
        }
    }
    renderFileList(); // Call the new render function
}

// Modify clearFileList to use renderFileList
function clearFileList() { // Specific to docConversionContent
    uploadedFiles.length = 0; // Empty the array
    renderFileList(); // Re-render (which will show an empty list)
    const fileInput = document.getElementById('fileUpload');
    if (fileInput) fileInput.value = ''; // Reset file input
}

// Drag and Drop functionality for the content-area
const dropZone = document.getElementById('dropZone'); // Specific to docConversionContent

if (dropZone) { // Ensure dropZone exists before adding listeners
    dropZone.addEventListener('dragover', (event) => {
        event.stopPropagation();
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
        dropZone.style.backgroundColor = '#e7f3ff'; // Highlight on drag over
    });

    dropZone.addEventListener('dragleave', (event) => {
        event.stopPropagation();
        event.preventDefault();
        dropZone.style.backgroundColor = '#f8f9faff'; // Revert background
    });

    dropZone.addEventListener('drop', (event) => {
        event.stopPropagation();
        event.preventDefault();
        dropZone.style.backgroundColor = '#f8f9faff'; // Revert background
        const files = event.dataTransfer.files;
        handleFiles(files); // Assumes handleFiles is appropriate for this dropzone
    });
}
    
function clearConvertedFilesList() { // Specific to docConversionContent
    const container = document.getElementById('convertedFilesTableContainer');
    if (container) container.innerHTML = ''; // Clear previous results
}

function startConversion() { // This is the original startConversion for docConversionContent
    console.log("[startConversion - Doc] 函数开始执行。当前的 isConverting 状态:", isConverting);
    if (currentSelectedMainNavigation !== 'docConversion') {
        console.warn("[startConversion - Doc] Called when not in document conversion view. Aborting.");
        return;
    }
    if (uploadedFiles.length === 0) {
        alert("请先添加要转换的文件。");
        return;
    }

    isConverting = true;
    updateMainTabButtonsState(true); // --- NEW --- Disable other tabs
    console.log("[startConversion - Doc] isConverting 已被设置为 true。");
    const conversionBtn = document.getElementById('startConversionBtn');
    conversionBtn.disabled = true;
    conversionBtn.textContent = '等待转换中...';
    conversionBtn.style.backgroundColor = '#ffc107';
    conversionBtn.style.borderColor = '#ffc107';
    console.log("[startConversion - Doc] '开始转换'按钮状态已更新为'等待转换中...' (禁用，黄色背景)。");
    clearConvertedFilesList(); // Clear previous results table

    const formData = new FormData();
    uploadedFiles.forEach(file => {
        formData.append('uploaded_files_info[]', JSON.stringify({
            name: file.name,
            size: file.size,
            type: file.type
            // 可根据后端需要补充其它字段
        }));
        formData.append('images', file); // 兼容后端images字段
    });

    formData.append('main_tab', currentSelectedMainTab);
    formData.append('sub_tab', currentSelectedSubTab);
    formData.append('merge_output', document.getElementById('mergeOutputCheckbox').checked);
    
    let outputFormat = '';
    if (currentSelectedMainTab === 'imgToFile') {
        if (currentSelectedSubTab === 'imgToPdf') {
            outputFormat = 'pdf';
        } else if (currentSelectedSubTab === 'imgToPpt') {
            outputFormat = 'pptx';
            formData.append('direct_image_to_ppt', 'true');
        } else {
            outputFormat = 'docx';
        }
    } else if (currentSelectedMainTab === 'fileToPdf') {
        let mode = '';
        switch (currentSelectedSubTab) {
            case 'wordToPdf':
                mode = 'docx_to_pdf_mode';
                break;
            case 'excelToPdf':
                mode = 'excel_to_pdf_mode';
                break;
            case 'pptToPdf':
                mode = 'ppt_to_pdf_mode';
                break;
            case 'txtToPdf':
                mode = 'txt_to_pdf_mode';
                break;
            default:
                mode = '';
        }
        formData.append('mode', mode);
        outputFormat = 'pdf'; // Always PDF for fileToPdf main tab
    } else if (currentSelectedMainTab === 'pdfToFile') {
        switch (currentSelectedSubTab) {
            case 'pdfToWord': 
                outputFormat = 'docx'; 
                // --- NEW: Add pdf_to_word_mode to formData ---
                const selectedWordMode = document.querySelector('input[name="pdfToWordMode"]:checked');
                if (selectedWordMode) {
                    formData.append('pdf_to_word_mode', selectedWordMode.value);
                    console.log("PDF to Word Mode selected:", selectedWordMode.value);
                } else {
                    formData.append('pdf_to_word_mode', 'pdf2docx'); // Default if somehow none selected
                    console.warn("No PDF to Word Mode selected, defaulting to pdf2docx.");
                }
                break;
            case 'pdfToExcel': 
                outputFormat = 'xlsx'; 
                // --- NEW: Add pdf_to_excel_mode to formData ---
                const selectedExcelMode = document.querySelector('input[name="pdfToExcelMode"]:checked');
                if (selectedExcelMode) {
                    formData.append('pdf_to_excel_mode', selectedExcelMode.value);
                    console.log("PDF to Excel Mode selected:", selectedExcelMode.value);
                } else {
                    formData.append('pdf_to_excel_mode', 'pdfplumber'); // Default if somehow none selected
                    console.warn("No PDF to Excel Mode selected, defaulting to pdfplumber.");
                }
                break;
            case 'pdfToPpt': 
                outputFormat = 'pptx';
                // --- NEW: Add pdf_to_ppt_mode to formData ---
                const selectedPptMode = document.querySelector('input[name="pdfToPptMode"]:checked');
                if (selectedPptMode) {
                    formData.append('pdf_to_ppt_mode', selectedPptMode.value);
                    console.log("PDF to PPT Mode selected:", selectedPptMode.value);
                } else {
                    formData.append('pdf_to_ppt_mode', 'screenshot'); // Default if somehow none selected
                    console.warn("No PDF to PPT Mode selected, defaulting to screenshot.");
                }
                break;
            case 'pdfToTxt': 
                outputFormat = 'txt'; 
                // --- NEW: Add pdf_to_txt_mode to formData ---
                const selectedTxtMode = document.querySelector('input[name="pdfToTxtMode"]:checked');
                if (selectedTxtMode) {
                    formData.append('pdf_to_txt_mode', selectedTxtMode.value);
                    console.log("PDF to TXT Mode selected:", selectedTxtMode.value);
                } else {
                    formData.append('pdf_to_txt_mode', 'pymupdf'); // Default if somehow none selected
                    console.warn("No PDF to TXT Mode selected, defaulting to pymupdf.");
                }
                break;
        }
    }
    formData.append('output_format', outputFormat);

    const csrfToken = getCookie('csrftoken');

    // Determine the correct API endpoint based on the main tab
    let apiUrl = '';
    if (currentSelectedMainTab === 'fileToPdf') {
        apiUrl = '/api/file-to-pdf/';
    } else if (currentSelectedMainTab === 'imgToFile') {
        apiUrl = '/api/img-to-file/';
    } else if (currentSelectedMainTab === 'pdfToFile') {
        apiUrl = '/api/pdf-to-file/';
    } else {
        console.error('Unknown main tab:', currentSelectedMainTab);
        alert('内部错误：无法确定API端点。');
        // Reset button and isConverting state
        isConverting = false;
        updateMainTabButtonsState(false);
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
        return;
    }

    console.log(`[startConversion - Doc] Determined API URL: ${apiUrl}`);

    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        displayConvertedFiles(data);
    })
    .catch(error => {
        console.error('转换出错:', error);
        // Prepare a data-like object for displayConvertedFiles in case of catch
        const errorData = {
            results: [{ original_name: '错误', converted_name: '-', status: 'error', message: '客户端请求错误，详情请查看控制台。' }],
            merge_output: false,
            // duration_seconds might not be available here, so it won't be displayed
        };
        displayConvertedFiles(errorData);
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
    })
    .finally(() => {
        console.log("[finally - Doc] finally 代码块开始执行。重置前的 isConverting 状态:", isConverting);
        isConverting = false;
        updateMainTabButtonsState(false); // --- NEW --- Enable all tabs
        console.log("[finally - Doc] isConverting 已被重置为 false。");
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
        console.log("[finally - Doc] '开始转换'按钮状态已恢复。");
    });
}

function displayConvertedFiles(data) { // Specific to docConversionContent
    const container = document.getElementById('convertedFilesTableContainer');
    if (!container) return;
    container.innerHTML = ''; // Clear previous results

    // ADDED: Display overall duration first if available
    if (data.duration_seconds !== undefined) {
        const overallDurationP = document.createElement('p');
        overallDurationP.className = 'text-muted small mb-2'; // Consistent styling
        overallDurationP.textContent = `总处理时长: ${data.duration_seconds} 秒`;
        container.appendChild(overallDurationP);
    }

    if (data.error) {
        let errorMessage = `<p class="text-danger">处理失败: ${escapeHtml(data.error)}</p>`;
        container.innerHTML += errorMessage; // Append error message after duration
        return;
    }

    if (!data.results || data.results.length === 0) {
        container.innerHTML += '<p class="no-files">没有转换结果。</p>'; // Append after duration
        return;
    }

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
    
// Initial setup: DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing functionality...');
    
    // Initialize the view based on currentSelectedMainNavigation
    selectMainNavigation(currentSelectedMainNavigation, true);
    initializeDocumentGenerationControls();

    // Bind the document conversion button
    const convertBtn = document.getElementById('startConversionBtn');
    if(convertBtn) {
        convertBtn.addEventListener('click', startConversion);
        console.log('Document conversion button event listener bound');
    } else {
        console.error('startConversionBtn not found!');
    }

    // Initialize drag and drop for main file upload
    const dropZone = document.getElementById('dropZone');
    const fileUpload = document.getElementById('fileUpload');
    
    if (dropZone && fileUpload) {
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('border-primary');
        }

        function unhighlight(e) {
            dropZone.classList.remove('border-primary');
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        console.log('Drag and drop functionality initialized');
    }
});

// --- Main Navigation Logic ---
function selectMainNavigation(navId, isInitialLoad = false) {
    console.log(`[selectMainNavigation] Called with navId: ${navId}, isInitialLoad: ${isInitialLoad}`);
    console.log(`[selectMainNavigation] currentSelectedMainNavigation: ${currentSelectedMainNavigation}`);
    
    if (isConverting && !isInitialLoad) {
        console.log("[selectMainNavigation] Processing active. Main navigation switch prevented.");
        return;
    }

    // 如果正在离开语音处理页面，自动停止实时语音识别
    console.log(`[selectMainNavigation] Checking: currentSelectedMainNavigation === 'speechProcessing': ${currentSelectedMainNavigation === 'speechProcessing'}`);
    console.log(`[selectMainNavigation] Checking: navId !== 'speechProcessing': ${navId !== 'speechProcessing'}`);
    
    if (currentSelectedMainNavigation === 'speechProcessing' && navId !== 'speechProcessing') {
        console.log("[selectMainNavigation] ✓ Leaving speech section, checking for active recording");
        console.log("[selectMainNavigation] window.isRealtimeRecording =", window.isRealtimeRecording);
        console.log("[selectMainNavigation] typeof window.stopRealtimeRecognition =", typeof window.stopRealtimeRecognition);
        try {
            // 从window对象获取函数和变量
            if (typeof window.stopRealtimeRecognition === 'function' && window.isRealtimeRecording === true) {
                console.log("[selectMainNavigation] Auto-stopping real-time speech recognition");
                window.stopRealtimeRecognition();
            } else {
                console.log("[selectMainNavigation] No active recording to stop");
            }
        } catch (e) {
            console.error("[selectMainNavigation] Error stopping real-time speech:", e);
        }
    }

    // Hide all main content sections
    document.getElementById('docConversionContent').style.display = 'none';
    document.getElementById('videoAnalysisContent').style.display = 'none';
    document.getElementById('speechProcessingContent').style.display = 'none';
    // Add future main content IDs here: document.getElementById('imageAnalysisContent').style.display = 'none';

    // Deactivate all sidebar buttons
    document.querySelectorAll('.sidebar-nav li button').forEach(btn => btn.classList.remove('active'));

    // Activate the selected one and show its content
    let activeContentDiv = null;
    currentSelectedMainNavigation = navId; // Set this early

    switch (navId) {
        case 'docConversion':
            activeContentDiv = document.getElementById('docConversionContent');
            document.getElementById('navDocConversion').classList.add('active');
            // showTab will be called, which calls selectSubTab, which calls updateFileUploadAcceptType & clearFileList
            showTab(currentSelectedMainTab || 'imgToFile'); 
            break;
        case 'videoAnalysis':
            activeContentDiv = document.getElementById('videoAnalysisContent');
            document.getElementById('navVideoAnalysis').classList.add('active');
            initializeVideoTab(); 
            break;
        case 'speechProcessing':
            activeContentDiv = document.getElementById('speechProcessingContent');
            document.getElementById('navSpeechProcessing').classList.add('active');
            initializeSpeechTab(); // This will also call showSpeechProcessingSubTab
            break;
        case 'documentGeneration':
            activeContentDiv = document.getElementById('documentGenerationContent');
            document.getElementById('navDocumentGeneration').classList.add('active');
            initializeDocumentGenerationControls();
            break;
        case 'imageAnalysis': // Placeholder for when image analysis is enabled
            // activeContentDiv = document.getElementById('imageAnalysisContent');
            // document.getElementById('navImageAnalysis').classList.add('active');
            // initializeImageTab(); 
            console.log("Image Analysis section selected (but not yet fully implemented).");
            break;
    }
    
    if (activeContentDiv) {
        activeContentDiv.style.display = 'block';
    }
    console.log(`[selectMainNavigation] Current main navigation set to: ${currentSelectedMainNavigation}`);
    
    if (!isInitialLoad) { 
        clearAllInputAreas(); // Clear inputs when actively switching main sections
    }
}
    
function clearAllInputAreas() {
    console.log("[clearAllInputAreas] Clearing all relevant input areas.");
    
    // 如果有正在进行的实时语音识别，先停止
    if (typeof window.stopRealtimeRecognition === 'function' && window.isRealtimeRecording === true) {
        console.log("[clearAllInputAreas] Stopping active real-time speech recognition");
        window.stopRealtimeRecognition();
    }
    
    // Document Conversion
    clearFileList(); // Clears uploadedFiles array and UI for doc conversion
    clearConvertedFilesList(); // Clears results table for doc conversion
    
    // Video Analysis
    clearVideoFileAndResults(); // Clears video file selection and results

    // Speech Processing
    clearAudioFileAndResult(); // Clears audio file selection and results

    // Document Generation
    clearDocumentGenerationInputs();
}

// --- Speech Processing Section JS ---
function initializeSpeechTab() {
    console.log("[initializeSpeechTab] Initializing speech tab.");
    // Ensure this is called to set up the default sub-tab view
    const asrSubTabButton = document.querySelector('#speechProcessingContent .sub-tabs button[onclick*="asrContent"]');
    if (asrSubTabButton) {
         showSpeechSubTab('asrContent', asrSubTabButton); // Show ASR by default
    } else {
        console.error("ASR sub-tab button not found for default initialization.");
    }
    // Initialize all speech processing functionalities
    initializeAsrFunctionality();
    initializeTtsFunctionality(); // Add TTS initialization
    initializeRealtimeSpeechFunctionality(); // Add real-time speech recognition initialization
}

// Renamed from showSpeechProcessingSubTab for clarity if it's only for main speech tab
function showSpeechSubTab(subTabIdToShow, clickedButton) {
    console.log(`[showSpeechSubTab] Switching to: ${subTabIdToShow}`);
    if (isConverting) {
        console.log("[showSpeechSubTab] Processing active. Sub-tab switch prevented.");
        return;
    }

    // Hide all speech sub-content sections
    document.querySelectorAll('#speechProcessingContent .speech-sub-content').forEach(function(subTabDiv) {
        subTabDiv.style.display = 'none';
    });
    // Deactivate all speech sub-tab buttons
    document.querySelectorAll('#speechProcessingContent .sub-tabs button').forEach(function(btn) {
        if (!btn.classList.contains('disabled')) { // Only affect non-disabled buttons
            btn.classList.remove('active');
        }
    });

    // Show the selected sub-tab content
    const subTabElementToShow = document.getElementById(subTabIdToShow);
    if (subTabElementToShow) {
        subTabElementToShow.style.display = 'block';
    } else {
        console.error(`[showSpeechSubTab] Element with ID ${subTabIdToShow} not found.`);
    }
    // Activate the clicked button (if it's not disabled)
    if (clickedButton && !clickedButton.classList.contains('disabled')) {
        clickedButton.classList.add('active');
    }
    currentSelectedSpeechSubTab = subTabIdToShow; // Update global state
    
    // Initialize specific functionality based on the selected sub-tab
    if (subTabIdToShow === 'ttsContent') {
        console.log("[showSpeechSubTab] Initializing TTS functionality for TTS tab");
        // Ensure TTS functionality is initialized when TTS tab is shown
        // Use a longer delay to ensure DOM elements are fully visible and accessible
        setTimeout(() => {
            const startTtsBtn = document.getElementById('startTtsBtn');
            if (startTtsBtn) {
                console.log("[showSpeechSubTab] TTS button found, initializing...");
                initializeTtsFunctionality();
            } else {
                console.error("[showSpeechSubTab] TTS button not found, cannot initialize TTS functionality");
            }
        }, 200); // Increased delay
    } else if (subTabIdToShow === 'realtimeSpeechContent') {
        console.log("[showSpeechSubTab] Initializing real-time speech functionality");
        // Ensure real-time speech functionality is initialized when the tab is shown
        setTimeout(() => {
            const startRealtimeBtn = document.getElementById('startRealtimeBtn');
            if (startRealtimeBtn) {
                console.log("[showSpeechSubTab] Real-time speech button found, initializing...");
                initializeRealtimeSpeechFunctionality();
            } else {
                console.error("[showSpeechSubTab] Real-time speech button not found, cannot initialize functionality");
            }
        }, 200);
    }
    
    console.log(`[showSpeechSubTab] Current active speech sub-tab: ${currentSelectedSpeechSubTab}`);
}

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
        const newRow = createHotwordRow(); // createHotwordRow now returns the new row
        if (currentRowDiv && currentRowDiv.parentNode) {
            // Insert the new row after the current row
            currentRowDiv.parentNode.insertBefore(newRow, currentRowDiv.nextSibling);
        } else {
            // Fallback if currentRowDiv is null (e.g., initial call or after clearing all)
            hotwordsContainer.appendChild(newRow);
        }
    }

    function createHotwordRow() {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'hotword-row input-group mb-2';

        // Label for Hotword Text
        const textLabel = document.createElement('span');
        textLabel.className = 'hotword-label';
        textLabel.textContent = '热词：';
        rowDiv.appendChild(textLabel);

        // Input for Hotword Text
        const textInput = document.createElement('input');
        textInput.type = 'text';
        textInput.className = 'form-control hotword-text';
        textInput.placeholder = '热词文本';
        rowDiv.appendChild(textInput);

        // Label for Weight
        const weightLabel = document.createElement('span');
        weightLabel.className = 'hotword-label';
        weightLabel.textContent = '权重：';
        rowDiv.appendChild(weightLabel);

        // Input for Weight
        const weightInput = document.createElement('input');
        weightInput.type = 'number';
        weightInput.className = 'form-control hotword-weight';
        weightInput.placeholder = '权重 (1-5整数)';
        weightInput.title = '取值范围为[1, 5]之间的整数，如果效果不明显可以适当增加权重，但是当权重较大时可能会引起负面效果，导致其他词语识别不准确';
        weightInput.min = '1';
        weightInput.value = '4';
        rowDiv.appendChild(weightInput);

        // Label for Language
        const langLabel = document.createElement('span');
        langLabel.className = 'hotword-label';
        langLabel.textContent = '语言：';
        rowDiv.appendChild(langLabel);

        // Select for Language
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
        removeBtn.className = 'btn btn-danger btn-sm remove-hotword-btn'; // Bootstrap classes for styling
        removeBtn.innerHTML = '-';
        removeBtn.title = '移除此热词行';
        removeBtn.onclick = function() {
            const parentContainer = rowDiv.parentNode;
            rowDiv.remove();
            // If it was the last row and now container is empty, add a new initial row
            if (parentContainer && parentContainer.children.length === 0) {
                addNewHotwordRowBelow(null); // Adds a new row to the container
            }
        };
        rowDiv.appendChild(removeBtn);

        // NEW: Inline Add button for this row
        const addInlineBtn = document.createElement('button');
        addInlineBtn.type = 'button';
        addInlineBtn.className = 'btn btn-success btn-sm add-hotword-inline-btn ms-1'; // Added ms-1 for a little space
        addInlineBtn.innerHTML = '+';
        addInlineBtn.title = '在此行下方添加新热词行';
        addInlineBtn.onclick = function() {
            addNewHotwordRowBelow(rowDiv); 
        };
        rowDiv.appendChild(addInlineBtn);
        
        return rowDiv; // Return the created row
    }

    // Initial setup: Add one hotword row when the ASR functionality is initialized
    addNewHotwordRowBelow(null); // Add the first row to the container

    startAsrBtn.addEventListener('click', async function() {
        const audioUrl = audioUrlInput.value.trim();

        // 文件大小校验（仅本地文件上传时可用，OSS URL无法前端校验）
        // if (audioFileInput.files[0] && audioFileInput.files[0].size > 500 * 1024 * 1024) {
        //     asrErrorOutput.textContent = '音频文件不能超过500MB';
        //     addNotification('音频文件不能超过500MB', 'error');
        //     return;
        // }
        // 对于OSS URL，无法前端校验文件大小，需后端校验。

        if (!audioUrl) {
            asrErrorOutput.textContent = '请输入有效的音频文件URL。';
            addNotification('请输入有效的音频文件URL。', 'error');
            return;
        }

        // NEW: Collect hotwords from dynamic rows
        const hotwordsConfig = [];
        const hotwordRows = hotwordsContainer.querySelectorAll('.hotword-row');
        let hotwordValidationError = false;
        hotwordRows.forEach(row => {
            const text = row.querySelector('.hotword-text').value.trim();
            const weightStr = row.querySelector('.hotword-weight').value.trim();
            const lang = row.querySelector('.hotword-lang').value;

            if (text) { // Only include if text is provided
                const weight = parseInt(weightStr, 10);
                if (isNaN(weight) || weight < 1) {
                    asrErrorOutput.textContent = `热词 \"${text}\" 的权重无效，请输入大于0的整数。`;
                    addNotification(`热词 \"${text}\" 的权重无效。`, 'error');
                    hotwordValidationError = true;
                    return; // Stop processing this row
                }
                hotwordsConfig.push({ text, weight, lang });
            }
        });

        if (hotwordValidationError) return; // Stop if validation failed

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
                payload.hotwords_config = hotwordsConfig; // Use new key
            }
            console.log("[ASR] Starting recognition for URL:", audioUrl, "Hotwords Config:", hotwordsConfig);

            const response = await fetch("/api/speech-to-text/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            console.log("[ASR] Received response:", result);

            if (response.ok && result.results && result.results.length > 0 && result.results[0].status === 'success') {
                asrResultTextarea.value = result.results[0].transcription || '(未识别到文本)';
                if (result.duration_seconds !== undefined) {
                     console.log(`[ASR] Request ${result.request_id} completed in ${result.duration_seconds}s.`);
                     addNotification(`语音识别成功 (用时 ${result.duration_seconds}s)`, 'success');
                } else {
                    addNotification('语音识别成功!', 'success');
                }
            } else {
                const errorMsg = (result.results && result.results.length > 0 && result.results[0].message) || result.message || '语音识别失败，请检查URL或稍后再试。';
                asrErrorOutput.textContent = errorMsg;
                addNotification(`语音识别失败: ${errorMsg}`, 'error');
                if (result.duration_seconds !== undefined) {
                    console.error(`[ASR] Request ${result.request_id} failed in ${result.duration_seconds}s. Message: ${result.message}`);
                }
            }
        } catch (error) {
            console.error('[ASR] API call failed:', error);
            const networkErrorMsg = '调用语音识别服务时发生网络或未知错误。请查看控制台获取详情。';
            asrErrorOutput.textContent = networkErrorMsg;
            addNotification(networkErrorMsg, 'error');
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
            hotwordsContainer.innerHTML = ''; // Clear all dynamic hotword rows
            addNewHotwordRowBelow(null); // Add back one initial empty row

            asrResultTextarea.value = '';
            asrErrorOutput.textContent = '';
            asrLoadingIndicator.style.display = 'none';
            startAsrBtn.disabled = false;
            clearAsrBtn.disabled = false;
            audioUrlInput.disabled = false;
            console.log("[ASR] Fields cleared.");
            addNotification('ASR输入和结果已清空。', 'info');
        });
    } else {
        console.error("clearAsrFieldsBtn not found during ASR initialization.");
    }
}
    
// --- Video Analysis Section JS ---
function initializeVideoTab() {
    console.log("[initializeVideoTab] Initializing video tab.");
    // Add event listener for video file input
    const videoInput = document.getElementById('videoFileForAnalysisInput');
    if (videoInput) {
        videoInput.addEventListener('change', handleVideoFileSelect);
    } else {
        console.error("Video file input not found.");
    }
    // Clear any previous results if needed
    clearVideoFileAndResults();
}

function handleVideoFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        uploadedVideoFile = file; // Store the file
        console.log('[handleVideoFileSelect] Video file selected:', file.name);
        
        // Display the selected file name (optional UI update)
        const fileListUI = document.getElementById('videoFileList');
        if (fileListUI) {
            fileListUI.innerHTML = `<li>${escapeHtml(file.name)} (${(file.size / 1024 / 1024).toFixed(2)} MB)</li>`;
        }
    } else {
        uploadedVideoFile = null;
         const fileListUI = document.getElementById('videoFileList');
        if (fileListUI) {
            fileListUI.innerHTML = ''; // Clear list if no file selected
        }
    }
}

function clearVideoFileAndResults() {
    console.log("[clearVideoFileAndResults] Clearing video file and results.");
    const videoInput = document.getElementById('videoFileForAnalysisInput');
    if (videoInput) videoInput.value = ''; // Clear the file input
    uploadedVideoFile = null;

    const fileListUI = document.getElementById('videoFileList');
    if (fileListUI) fileListUI.innerHTML = ''; // Clear displayed file name

    const resultsContainer = document.getElementById('videoProcessingResultsTableContainer');
    if (resultsContainer) resultsContainer.innerHTML = ''; // Clear results table

    const progressContainer = document.getElementById('videoProgressBarContainer');
    if (progressContainer) progressContainer.style.display = 'none';
    const progressBar = document.getElementById('videoProgressBar');
    if (progressBar) progressBar.style.width = '0%'; progressBar.textContent = '0%';

    const progressListContainer = document.getElementById('videoProgressListContainer');
    if (progressListContainer) {
        progressListContainer.style.display = 'none';
        const progressList = document.getElementById('videoProgressList');
        if (progressList) progressList.innerHTML = '';
    }
    const spinner = document.getElementById('videoProcessingSpinner');
    if (spinner) spinner.style.display = 'none';
    
    // Re-enable process button if it was disabled
    const processBtn = document.querySelector('#videoAnalysisContent button[onclick="processVideo()"]');
    if (processBtn) processBtn.disabled = false;
}

async function processVideo() {
    console.log("[processVideo] Starting video processing.");
    if (!uploadedVideoFile) {
        addNotification('请先选择一个视频文件。', 'warning');
        return;
    }

    const sceneDetectionThreshold = document.getElementById('sceneDetectionThreshold').value;
    const deduplicationGroupSize = document.getElementById('deduplicationGroupSize').value;

    if (!sceneDetectionThreshold || parseFloat(sceneDetectionThreshold) <= 0) {
        addNotification('请输入有效的场景检测阈值。', 'warning');
        return;
    }
    if (!deduplicationGroupSize || parseInt(deduplicationGroupSize) < 1) {
        addNotification('请输入有效的去重分组大小 (至少为1)。', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('video_file', uploadedVideoFile);
    formData.append('scene_detection_threshold', sceneDetectionThreshold);
    formData.append('deduplication_group_size', deduplicationGroupSize);
    
    const csrfToken = getCookie('csrftoken');
    const processBtn = document.querySelector('#videoAnalysisContent button[onclick="processVideo()"]');
    const spinner = document.getElementById('videoProcessingSpinner');
    const progressBarContainer = document.getElementById('videoProgressBarContainer');
    const progressBar = document.getElementById('videoProgressBar');
    const progressListContainer = document.getElementById('videoProgressListContainer');
    const progressList = document.getElementById('videoProgressList');
    const resultsContainer = document.getElementById('videoProcessingResultsTableContainer');

    processBtn.disabled = true;
    if(spinner) spinner.style.display = 'block';
    if(progressBarContainer) progressBarContainer.style.display = 'none'; // Hide initially, show on progress
    if(progressListContainer) progressListContainer.style.display = 'none';
    if(progressList) progressList.innerHTML = '';
    if(resultsContainer) resultsContainer.innerHTML = ''; // Clear previous results
    isConverting = true; // Use the global flag
    updateMainNavigationButtonStates(true); // Disable main navigation

    try {
        const processVideoUrl = document.getElementById('processVideoUrl').value;
        const response = await fetch(processVideoUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        
        if (!response.ok) {
            let errorData = { message: `HTTP error! status: ${response.status}` };
            try {
                errorData = await response.json();
            } catch (e) {
                console.warn("Could not parse error response as JSON:", e);
            }
            console.error('Video processing error:', errorData.message);
            addNotification(`视频处理失败: ${errorData.message || response.statusText}`, 'error');
            displayVideoProcessingResults({ error: errorData.message || response.statusText }); // Display error in table
            return;
        }

        // --- 新增：流式解析 SSE ---
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        if(progressBarContainer) progressBarContainer.style.display = 'block';
        if(progressListContainer) progressListContainer.style.display = 'block';
        if(spinner) spinner.style.display = 'none';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n');
            buffer = lines.pop(); // 最后一行可能不完整
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'progress') {
                            // 更新进度条
                            if(progressBar && typeof data.percent === 'number') {
                                progressBar.style.width = data.percent + '%';
                                progressBar.textContent = data.percent + '%';
                            }
                        } else if (data.type === 'info') {
                            // 显示日志
                            if(progressList) {
                                const li = document.createElement('li');
                                li.textContent = data.message;
                                progressList.appendChild(li);
                                progressList.scrollTop = progressList.scrollHeight;
                            }
                        } else if (data.type === 'result') {
                            // 显示最终下载链接
                            displayVideoProcessingResults({ results: data.results });
                        } else if (data.type === 'error') {
                            displayVideoProcessingResults({ error: data.message });
                        }
                    } catch (e) {
                        console.warn('解析SSE行失败:', line, e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('[processVideo] API call failed:', error);
        addNotification('调用视频处理服务时发生网络或未知错误。详情请查看控制台。', 'error');
        displayVideoProcessingResults({ error: '网络或客户端错误，无法连接到服务器。' });
    } finally {
        isConverting = false;
        updateMainNavigationButtonStates(false);
        if(processBtn) processBtn.disabled = false;
        if(spinner) spinner.style.display = 'none';
    }
}

function displayVideoProcessingResults(data) {
    const container = document.getElementById('videoProcessingResultsTableContainer');
    if (!container) return;
    container.innerHTML = ''; // Clear previous results

    // 兼容 results 数组，风格与图片转文件一致
    if (Array.isArray(data.results) && data.results.length > 0) {
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
        return;
    }

    // 原有单文件/错误逻辑
    if (data.error) {
        container.innerHTML = `<p class="text-danger">处理失败: ${escapeHtml(data.error)}</p>`;
        if (data.details && data.details.traceback) {
            const pre = document.createElement('pre');
            pre.style.whiteSpace = 'pre-wrap';
            pre.style.wordBreak = 'break-all';
            pre.style.maxHeight = '200px';
            pre.style.overflowY = 'auto';
            pre.style.backgroundColor = '#f8f9fa';
            pre.style.border = '1px solid #dee2e6';
            pre.style.padding = '10px';
            pre.textContent = data.details.traceback;
            container.appendChild(document.createElement('hr'));
            container.appendChild(pre);
        }
        return;
    }

    if (!data.processed_video_filename && (!data.output_files || data.output_files.length === 0)) {
        container.innerHTML = '<p class="no-files">没有生成任何文件或结果。</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table table-striped table-bordered';
    table.style.borderCollapse = 'collapse';

    const thead = document.createElement('thead');
    thead.innerHTML = '<tr>' +
                        '<th>类型</th>' +
                        '<th>文件名/信息</th>' +
                        '<th>下载/查看</th>' +
                    '</tr>';
    table.appendChild(thead);
    const tbody = document.createElement('tbody');

    // Display the main processed video/PPT if available
    if (data.processed_video_filename && data.download_url) {
        const row = tbody.insertRow();
        row.insertCell().textContent = data.output_type === 'ppt' ? 'PPT 文稿' : '处理后视频';
        row.insertCell().textContent = data.processed_video_filename;
        const actionCell = row.insertCell();
        const downloadLink = document.createElement('a');
        downloadLink.href = data.download_url;
        downloadLink.textContent = '下载 ' + (data.output_type === 'ppt' ? 'PPT' : '视频');
        downloadLink.className = 'download-link'; // Reuse class from doc conversion
        downloadLink.target = '_blank';
        actionCell.appendChild(downloadLink);
    }

    // Display individual extracted images if available
    if (data.output_files && data.output_files.length > 0) {
        data.output_files.forEach(fileInfo => {
            const row = tbody.insertRow();
            row.insertCell().textContent = '截图帧'; // Assuming these are image frames
            row.insertCell().textContent = fileInfo.name;
            const actionCell = row.insertCell();
            if (fileInfo.url) {
                const downloadLink = document.createElement('a');
                downloadLink.href = fileInfo.url;
                downloadLink.textContent = '下载图片';
                downloadLink.className = 'download-link'; // Reuse class
                downloadLink.target = '_blank';
                actionCell.appendChild(downloadLink);
            } else {
                actionCell.textContent = '-';
            }
        });
    }
    
    // Display analysis_summary.txt if available
    if (data.analysis_summary_url && data.analysis_summary_filename) {
        const row = tbody.insertRow();
        row.insertCell().textContent = '分析摘要';
        row.insertCell().textContent = data.analysis_summary_filename;
        const actionCell = row.insertCell();
        const downloadLink = document.createElement('a');
        downloadLink.href = data.analysis_summary_url;
        downloadLink.textContent = '下载摘要';
        downloadLink.className = 'download-link';
        downloadLink.target = '_blank';
        actionCell.appendChild(downloadLink);
    }

    table.appendChild(tbody);
    container.appendChild(table);

    if (data.message) { // Display any general success message
         const successMsgP = document.createElement('p');
         successMsgP.className = 'text-success mt-2';
         successMsgP.textContent = data.message;
         container.insertBefore(successMsgP, table); // Insert before table
    }
     // Display processing duration
    if (data.duration_seconds !== undefined) {
        const durationP = document.createElement('p');
        durationP.className = 'text-muted small mt-2';
        durationP.textContent = `视频处理总用时: ${data.duration_seconds.toFixed(2)} 秒`;
        container.appendChild(durationP); // Append after table
    }
}
    
// Helper to escape HTML for safe insertion
function escapeHtml(unsafe) {
    if (unsafe === null || typeof unsafe === 'undefined') return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Function to clear audio URL and result for Speech Processing tab
function clearAudioFileAndResult() {
    console.log("[clearAudioFileAndResult] Clearing audio URL and result for ASR.");
    const audioUrlInput = document.getElementById('audioUrlInput');
    const asrTranscriptionOutput = document.getElementById('asrTranscriptionOutput');
    const asrErrorOutput = document.getElementById('asrErrorOutput');
    
    if (audioUrlInput) audioUrlInput.value = '';
    if (asrTranscriptionOutput) asrTranscriptionOutput.textContent = '';
    if (asrErrorOutput) asrErrorOutput.textContent = '';
    
    // Potentially re-enable buttons if they were disabled by a process
    const startAsrBtn = document.getElementById('startAsrBtn');
    const clearAsrFieldsBtn = document.getElementById('clearAsrFieldsBtn');
    if(startAsrBtn) startAsrBtn.disabled = false;
    if(clearAsrFieldsBtn) clearAsrFieldsBtn.disabled = false;
    if(audioUrlInput) audioUrlInput.disabled = false; // Re-enable input field
    
    const asrLoadingIndicator = document.getElementById('asrLoadingIndicator');
    if(asrLoadingIndicator) asrLoadingIndicator.style.display = 'none';
}

// === 强制修复图片转PPT复选框显示 ===
window.currentSelectedMainTab = 'imgToFile';
window.currentSelectedSubTab = 'imgToWord';

// 监听主tab点击
const btnImgToFile = document.getElementById('btnImgToFile');
if (btnImgToFile) {
    btnImgToFile.addEventListener('click', function() {
        window.currentSelectedMainTab = 'imgToFile';
        setTimeout(function() {
            if (typeof updateImgToPptDirectInsertOption === 'function') updateImgToPptDirectInsertOption();
        }, 100);
    });
}

// 监听子tab点击
const subTabButtons = document.querySelectorAll('.sub-tab-button');
subTabButtons.forEach(function(btn) {
    btn.addEventListener('click', function() {
        if (btn.textContent.includes('图片转PPT')) {
            window.currentSelectedSubTab = 'imgToPpt';
        } else if (btn.textContent.includes('图片转Word')) {
            window.currentSelectedSubTab = 'imgToWord';
        } else if (btn.textContent.includes('图片转PDF')) {
            window.currentSelectedSubTab = 'imgToPdf';
        }
        setTimeout(function() {
            if (typeof updateImgToPptDirectInsertOption === 'function') updateImgToPptDirectInsertOption();
        }, 100);
    });
});

// 页面初始刷新
setTimeout(function() {
    if (typeof updateImgToPptDirectInsertOption === 'function') updateImgToPptDirectInsertOption();
}, 200);
// === END ===

function initializeTtsFunctionality() {
    // Prevent multiple initializations
    if (ttsInitialized) {
        console.log("[initializeTtsFunctionality] TTS already initialized, skipping.");
        return;
    }
    
    console.log("[initializeTtsFunctionality] Initializing TTS functionality.");
    
    // --- Top Level Elements ---
    const startTtsBtn = document.getElementById('startTtsBtn');
    const clearTtsBtn = document.getElementById('clearTtsBtn');
    const ttsVoiceSelection = document.getElementById('ttsVoiceSelection');
    
    // Check if essential elements exist
    if (!startTtsBtn || !clearTtsBtn || !ttsVoiceSelection) {
        console.error("[initializeTtsFunctionality] Essential TTS elements not found, aborting initialization.");
        return;
    }
    
    // --- Input Containers and Radios ---
    const ttsTextContainer = document.getElementById('ttsTextContainer');
    const ttsFileContainer = document.getElementById('ttsFileContainer');
    const radioText = document.getElementById('ttsInputTypeText');
    const radioFile = document.getElementById('ttsInputTypeFile');
    
    // --- Text Input ---
    const ttsInputText = document.getElementById('ttsInputText');
    const ttsTextCharCount = document.getElementById('ttsTextCharCount');
    const ttsTextWarning = document.getElementById('ttsTextWarning');

    // --- File Upload Elements ---
    const ttsDropZone = document.getElementById('ttsDropZone');
    const ttsFileInput = document.getElementById('ttsFileInput');
    const ttsFileListUI = document.getElementById('ttsFileList');
    const ttsClearListBtn = document.getElementById('ttsClearListBtn');
    const ttsFileCharCount = document.getElementById('ttsFileCharCount');
    const ttsFileWarning = document.getElementById('ttsFileWarning');
    let ttsUploadedFiles = []; // Array to hold file objects
    let totalFileCharCount = 0; // Track total character count from files

    // --- Result Display Elements ---
    const ttsResultContainer = document.getElementById('ttsResultContainer');
    const ttsProgressContainer = document.getElementById('ttsProgressContainer');
    const ttsProgressBar = document.getElementById('ttsProgressBar');
    const ttsProgressText = document.getElementById('ttsProgressText');
    const ttsErrorOutput = document.getElementById('ttsErrorOutput');
    const ttsResultsTableContainer = document.getElementById('ttsResultsTableContainer');

    // --- LOGIC ---

    // 0. Character Count Functions
    const updateTextCharCount = () => {
        const text = ttsInputText.value;
        const charCount = text.length;
        ttsTextCharCount.textContent = `字数: ${charCount}`;
        
        if (charCount > 5000) {
            ttsTextWarning.style.display = 'inline';
            ttsTextWarning.style.color = '#dc3545'; // Force red color for warning
            ttsTextWarning.style.fontWeight = 'bold'; // Make warning bold
            ttsTextCharCount.className = 'text-danger small';
            ttsTextCharCount.style.color = '#dc3545'; // Force red color
            // Disable start button when text exceeds limit
            if (startTtsBtn) {
                startTtsBtn.disabled = true;
                startTtsBtn.style.backgroundColor = '#6c757d';
                startTtsBtn.style.borderColor = '#6c757d';
                startTtsBtn.style.cursor = 'not-allowed';
            }
        } else {
            ttsTextWarning.style.display = 'none';
            ttsTextCharCount.className = 'text-muted small';
            ttsTextCharCount.style.color = ''; // Reset to default
            // Re-enable start button when text is within limit
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
            ttsFileWarning.style.color = '#dc3545'; // Force red color for warning
            ttsFileWarning.style.fontWeight = 'bold'; // Make warning bold
            ttsFileCharCount.className = 'text-danger small';
            ttsFileCharCount.style.color = '#dc3545'; // Force red color
            // Disable start button when file content exceeds limit
            if (startTtsBtn) {
                startTtsBtn.disabled = true;
                startTtsBtn.style.backgroundColor = '#6c757d';
                startTtsBtn.style.borderColor = '#6c757d';
                startTtsBtn.style.cursor = 'not-allowed';
            }
        } else {
            ttsFileWarning.style.display = 'none';
            ttsFileCharCount.className = 'text-muted small';
            ttsFileCharCount.style.color = ''; // Reset to default
            // Re-enable start button when file content is within limit
            if (startTtsBtn && radioFile.checked) {
                startTtsBtn.disabled = false;
                startTtsBtn.style.backgroundColor = '#007bff';
                startTtsBtn.style.borderColor = '#007bff';
                startTtsBtn.style.cursor = 'pointer';
            }
        }
    };

    // Add real-time character counting for text input
    if (ttsInputText) {
        ttsInputText.addEventListener('input', updateTextCharCount);
        ttsInputText.addEventListener('paste', () => {
            setTimeout(updateTextCharCount, 10); // Delay to allow paste to complete
        });
        // Initial count
        updateTextCharCount();
    }

    // 1. Input Mode Switching
    const handleTtsInputSwitch = () => {
        if (radioText.checked) {
            ttsTextContainer.style.display = 'block';
            ttsFileContainer.style.display = 'none';
            // Check text character count and update button state
            updateTextCharCount();
        } else {
            ttsTextContainer.style.display = 'none';
            ttsFileContainer.style.display = 'block';
            // Check file character count and update button state
            updateFileCharCount();
        }
    };
    radioText.addEventListener('change', handleTtsInputSwitch);
    radioFile.addEventListener('change', handleTtsInputSwitch);

    // 2. File Handling Logic
    const handleTtsFiles = (files) => {
        [...files].forEach(file => {
            // Basic validation for supported types
            if (['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(file.type) || 
                file.name.endsWith('.txt') || file.name.endsWith('.pdf') || file.name.endsWith('.docx')) {
                ttsUploadedFiles.push(file);
                
                // Estimate character count based on file type and size
                let estimatedChars = 0;
                if (file.name.endsWith('.txt') || file.type === 'text/plain') {
                    // For text files, assume 1 byte ≈ 1 character (rough estimate)
                    estimatedChars = file.size;
                } else if (file.name.endsWith('.pdf')) {
                    // For PDF, estimate roughly 1 character per 2 bytes (very rough)
                    estimatedChars = Math.floor(file.size / 2);
                } else if (file.name.endsWith('.docx')) {
                    // For DOCX, estimate roughly 1 character per 3 bytes (very rough)
                    estimatedChars = Math.floor(file.size / 3);
                }
                
                totalFileCharCount += estimatedChars;
            } else {
                addNotification(`不支持的文件类型: ${file.name}`, 'warning');
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
            li.innerHTML = `<span>${escapeHtml(file.name)}</span>`;
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
        ttsFileInput.value = ''; // Reset file input
        updateTtsFileList();
        updateFileCharCount();
    });

    // 3. Main Action Buttons
    if (startTtsBtn) {
        startTtsBtn.addEventListener('click', async function() {
            const inputType = radioText.checked ? 'text' : 'file';
            const text = ttsInputText.value.trim();
            const voice = ttsVoiceSelection.value;

            if (inputType === 'text' && !text) {
                addNotification('请输入要转换的文本。', 'warning');
                return;
            }
            if (inputType === 'file' && ttsUploadedFiles.length === 0) {
                addNotification('请至少上传一个文件。', 'warning');
                return;
            }

            // --- FIX START ---
            // Clear previous results but preserve the table structure
            const resultsTableBody = document.getElementById('ttsResultsTableBody');
            if (resultsTableBody) {
                resultsTableBody.innerHTML = '';
            } else {
                 // If the table body isn't there, clear the whole container to be safe
                ttsResultsTableContainer.innerHTML = '';
            }
            ttsResultContainer.style.display = 'block';
            ttsProgressContainer.style.display = 'block';
            ttsErrorOutput.style.display = 'none';
            // --- FIX END ---
            
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
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
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
                addNotification(`转换失败: ${error.message}`, 'error');
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
            
            // Ensure button is re-enabled after clearing
            if (startTtsBtn) {
                startTtsBtn.disabled = false;
                startTtsBtn.style.backgroundColor = '#007bff';
                startTtsBtn.style.borderColor = '#007bff';
                startTtsBtn.style.cursor = 'pointer';
            }
        });
    }

    // Helper for progress bar
    function updateProgressBar(percentage, text) {
        const progressBar = document.getElementById('ttsProgressBar');
        const progressText = document.getElementById('ttsProgressText');
        if(progressBar && progressText) {
            progressBar.style.width = percentage;
            progressBar.setAttribute('aria-valuenow', percentage.replace('%', ''));
            progressText.textContent = text;
        }
    }

    // NEW FUNCTION: Replicates the style and structure of displayConvertedFiles for TTS
    function displayTtsResults(data) {
        console.log("[displayTtsResults] Rendering data:", data);
        
        const container = document.getElementById('ttsResultsTableContainer');
        if (!container) {
            console.error('TTS Results container not found!');
            addNotification('发生UI错误：无法找到结果显示区域。', 'error');
            return;
        }
        container.innerHTML = ''; // Clear previous results

        // ADDED: Display overall duration first if available
        if (data.duration_seconds !== undefined) {
            const overallDurationP = document.createElement('p');
            overallDurationP.className = 'text-muted small mb-2'; // Consistent styling
            overallDurationP.textContent = `总处理时长: ${data.duration_seconds} 秒`;
            container.appendChild(overallDurationP);
        }

        if (data.error) {
            let errorMessage = `<p class="text-danger">处理失败: ${escapeHtml(data.error)}</p>`;
            container.innerHTML += errorMessage; // Append error message after duration
            return;
        }

        if (!data.results || data.results.length === 0) {
            container.innerHTML += '<p class="no-files">没有转换结果。</p>'; // Append after duration
            return;
        }

        // Add the same container class as document conversion for consistent styling
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
    
    // Mark TTS as initialized
    ttsInitialized = true;
    console.log("[initializeTtsFunctionality] TTS functionality initialized successfully.");
}

// --- Real-time Speech Recognition Functionality ---
let realtimeSpeechSession = null;
let audioChunks = [];
let audioContext = null;
let analyser = null;
let microphone = null;
let isRealtimeRecording = false;
let recognitionResults = [];
let pollingInterval = null;
let scriptProcessor = null; // 新增

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
        // 新增：ScriptProcessorNode 采集 PCM
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
        // 启动识别会话
        updateRealtimeStatus('正在启动识别服务...', true);
        const sessionResponse = await fetch('/api/realtime-speech/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
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
        // 断开 ScriptProcessorNode
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
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
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
                'X-CSRFToken': getCookie('csrftoken'),
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
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                // 新增详细 polled data 日志
                console.log('[startResultPolling] polled data:', data);
                // 兼容后端返回的 results 或 final_results 字段
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
    }, 200); // Poll every 200ms
}

function processRecognitionResults(results) {
    const outputDiv = document.getElementById('realtimeTranscriptionOutput');
    const intermediateDiv = document.getElementById('realtimeIntermediateResults');
    console.log('[processRecognitionResults] called, results:', results, 'isRealtimeRecording:', isRealtimeRecording);
    console.log('[processRecognitionResults] outputDiv:', outputDiv);
    console.log('[processRecognitionResults] intermediateDiv:', intermediateDiv);

    if (isRealtimeRecording) {
        // 录音过程中：处理临时和最终结果
        let startIdx = recognitionResults.length;
        let latestIntermediate = '';
        for (let i = startIdx; i < results.length; i++) {
            const result = results[i];
            console.log('[processRecognitionResults] result:', result);
            if ((result.type === 'result' || result.type === undefined) && result.text) {
                if (result.is_final) {
                    recognitionResults.push(result.text);
                    console.log('[processRecognitionResults] push final:', result.text);
                } else {
                    latestIntermediate = result.text;
                    console.log('[processRecognitionResults] latest intermediate:', latestIntermediate);
                }
            }
        }
        updateRealtimeOutput();
        // 实时显示临时识别结果
        if (latestIntermediate) {
            intermediateDiv.innerHTML = `<div class="text-info">${escapeHtml(latestIntermediate)}</div>`;
            console.log('[processRecognitionResults] intermediateDiv updated:', latestIntermediate);
        } else {
            intermediateDiv.innerHTML = '';
            console.log('[processRecognitionResults] intermediateDiv cleared');
        }
    } else {
        // 停止时的最终结果：全部加入 recognitionResults，清空 intermediate
        results.forEach(result => {
            if ((result.type === 'result' || result.type === undefined) && result.text) {
                recognitionResults.push(result.text);
                console.log('[processRecognitionResults] push final (stopped):', result.text);
            }
        });
        updateRealtimeOutput();
        intermediateDiv.innerHTML = '';
        console.log('[processRecognitionResults] intermediateDiv cleared (stopped)');
    }
}

function updateRealtimeOutput() {
    const outputDiv = document.getElementById('realtimeTranscriptionOutput');
    const text = recognitionResults.join('\n');
    
    if (text.trim()) {
        outputDiv.innerHTML = text.split('\n').map(line => 
            `<div style="margin-bottom: 8px; padding: 4px 0;">${escapeHtml(line)}</div>`
        ).join('');
    } else {
        outputDiv.innerHTML = '<div class="text-muted">实时识别的文本将显示在这里...</div>';
    }
    
    // Auto-scroll to bottom
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
    
    // Calculate average volume
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    const level = (average / 255) * 100;
    
    // Update audio level bar
    const levelBar = document.getElementById('audioLevelBar');
    if (levelBar) {
        levelBar.style.width = level + '%';
        
        // Change color based on level
        if (level > 70) {
            levelBar.className = 'progress-bar bg-danger';
        } else if (level > 30) {
            levelBar.className = 'progress-bar bg-success';
        } else {
            levelBar.className = 'progress-bar bg-info';
        }
    }
    
    // Continue monitoring
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
        errorDiv.innerHTML = `<div class="alert alert-danger">${escapeHtml(message)}</div>`;
    }
    console.error('Real-time speech error:', message);
    
    // Hide status if showing error
    updateRealtimeStatus('', false);
}

