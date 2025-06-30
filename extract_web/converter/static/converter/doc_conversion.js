// 文档转换相关逻辑
// 依赖 common.js 中的全局变量和工具函数

function updateMainTabButtonsState(disableNonActive) {
    const mainTabButtons = document.querySelectorAll('.tabs .tab-button');
    const subTabButtons = document.querySelectorAll('.sub-tabs .sub-tab-button');
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
window.updateMainTabButtonsState = updateMainTabButtonsState;

function updateFileUploadAcceptType() {
    const fileUploadInput = document.getElementById('fileUpload');
    let acceptTypes = '';
    if (window.currentSelectedMainNavigation !== 'docConversion' || !fileUploadInput) {
        return;
    }
    switch (window.currentSelectedMainTab) {
        case 'imgToFile':
            acceptTypes = '.jpg,.jpeg,.png,.bmp';
            break;
        case 'fileToPdf':
            switch (window.currentSelectedSubTab) {
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
    console.log('File input accept types updated to: ', acceptTypes);
}
window.updateFileUploadAcceptType = updateFileUploadAcceptType;

function showTab(tabId) {
    if (window.isConverting) {
        console.log('[showTab] Conversion in progress. Tab switch prevented.');
        return;
    }
    if (window.currentSelectedMainNavigation !== 'docConversion') return;
    if (window.currentSelectedMainTab !== tabId) {
        clearFileList();
        clearConvertedFilesList();
    }
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
    document.getElementById(tabId + 'Content').classList.remove('hidden');
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.getElementById('btn' + tabId.charAt(0).toUpperCase() + tabId.slice(1)).classList.add('active');
    window.currentSelectedMainTab = tabId;
    const firstSubTabButton = document.getElementById(tabId + 'Content').querySelector('.sub-tab-button');
    if (firstSubTabButton) {
        const onclickAttr = firstSubTabButton.getAttribute('onclick');
        const match = onclickAttr.match(/selectSubTab\(this, '([^']*)'\)/);
        if (match && match[1]) {
            selectSubTab(firstSubTabButton, match[1], false);
        } else {
            window.currentSelectedSubTab = null;
        }
    } else {
        window.currentSelectedSubTab = null;
    }
    updateFileUploadAcceptType();
    if (typeof window.updateImgToPptDirectInsertOption === 'function') window.updateImgToPptDirectInsertOption();
}
window.showTab = showTab;

function selectSubTab(buttonElement, subTabType, shouldUpdateAccept = true) {
    if (window.currentSelectedMainNavigation !== 'docConversion') return;
    if (!buttonElement) return;
    if (window.currentSelectedSubTab !== subTabType) {
        clearFileList();
        clearConvertedFilesList();
    }
    if (buttonElement.parentElement) {
        const subTabButtons = buttonElement.parentElement.querySelectorAll('.sub-tab-button');
        subTabButtons.forEach(btn => btn.classList.remove('active'));
        buttonElement.classList.add('active');
    }
    window.currentSelectedSubTab = subTabType;
    if (shouldUpdateAccept) updateFileUploadAcceptType();
    // PDF/图片选项显示逻辑略
    if (typeof window.updateImgToPptDirectInsertOption === 'function') window.updateImgToPptDirectInsertOption();
}
window.selectSubTab = selectSubTab;

function renderFileList() {
    const fileListUI = document.getElementById('fileList');
    fileListUI.innerHTML = '';
    window.uploadedFiles.forEach((file, index) => {
        const listItem = document.createElement('li');
        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-file-btn';
        removeBtn.innerHTML = '&times;';
        removeBtn.title = '移除文件';
        removeBtn.onclick = function() {
            window.uploadedFiles.splice(index, 1);
            renderFileList();
        };
        listItem.appendChild(fileNameSpan);
        listItem.appendChild(removeBtn);
        fileListUI.appendChild(listItem);
    });
}
window.renderFileList = renderFileList;

function handleFiles(incomingFiles) {
    const maxFiles = 10;
    const maxFileSize = 500 * 1024 * 1024;
    for (const file of incomingFiles) {
        if (window.uploadedFiles.length >= maxFiles) {
            alert(`最多只能上传 ${maxFiles} 个文件。`);
            break;
        }
        if (file.size > maxFileSize) {
            alert(`文件 "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)} MB) 超过了500MB的大小限制。`);
            continue;
        }
        if (!window.uploadedFiles.some(f => f.name === file.name)) {
            window.uploadedFiles.push(file);
        }
    }
    renderFileList();
}
window.handleFiles = handleFiles;

function clearFileList() {
    window.uploadedFiles.length = 0;
    renderFileList();
    const fileInput = document.getElementById('fileUpload');
    if (fileInput) fileInput.value = '';
}
window.clearFileList = clearFileList;

function clearConvertedFilesList() {
    const container = document.getElementById('convertedFilesTableContainer');
    if (container) container.innerHTML = '';
}
window.clearConvertedFilesList = clearConvertedFilesList;

function startConversion() {
    if (window.currentSelectedMainNavigation !== 'docConversion') return;
    if (window.uploadedFiles.length === 0) {
        alert('请先添加要转换的文件。');
        return;
    }
    window.isConverting = true;
    updateMainTabButtonsState(true);
    const conversionBtn = document.getElementById('startConversionBtn');
    conversionBtn.disabled = true;
    conversionBtn.textContent = '等待转换中...';
    conversionBtn.style.backgroundColor = '#ffc107';
    conversionBtn.style.borderColor = '#ffc107';
    clearConvertedFilesList();
    const formData = new FormData();
    window.uploadedFiles.forEach(file => {
        formData.append('uploaded_files_info[]', JSON.stringify({
            name: file.name,
            size: file.size,
            type: file.type
        }));
        formData.append('images', file);
    });
    formData.append('main_tab', window.currentSelectedMainTab);
    formData.append('sub_tab', window.currentSelectedSubTab);
    formData.append('merge_output', document.getElementById('mergeOutputCheckbox').checked);
    let outputFormat = '';
    if (window.currentSelectedMainTab === 'imgToFile') {
        if (window.currentSelectedSubTab === 'imgToPdf') {
            outputFormat = 'pdf';
        } else if (window.currentSelectedSubTab === 'imgToPpt') {
            outputFormat = 'pptx';
            formData.append('direct_image_to_ppt', 'true');
        } else {
            outputFormat = 'docx';
        }
    } else if (window.currentSelectedMainTab === 'fileToPdf') {
        let mode = '';
        switch (window.currentSelectedSubTab) {
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
        outputFormat = 'pdf';
    } else if (window.currentSelectedMainTab === 'pdfToFile') {
        switch (window.currentSelectedSubTab) {
            case 'pdfToWord':
                outputFormat = 'docx';
                const selectedWordMode = document.querySelector('input[name="pdfToWordMode"]:checked');
                if (selectedWordMode) {
                    formData.append('pdf_to_word_mode', selectedWordMode.value);
                } else {
                    formData.append('pdf_to_word_mode', 'pdf2docx');
                }
                break;
            case 'pdfToExcel':
                outputFormat = 'xlsx';
                const selectedExcelMode = document.querySelector('input[name="pdfToExcelMode"]:checked');
                if (selectedExcelMode) {
                    formData.append('pdf_to_excel_mode', selectedExcelMode.value);
                } else {
                    formData.append('pdf_to_excel_mode', 'pdfplumber');
                }
                break;
            case 'pdfToPpt':
                outputFormat = 'pptx';
                const selectedPptMode = document.querySelector('input[name="pdfToPptMode"]:checked');
                if (selectedPptMode) {
                    formData.append('pdf_to_ppt_mode', selectedPptMode.value);
                } else {
                    formData.append('pdf_to_ppt_mode', 'screenshot');
                }
                break;
            case 'pdfToTxt':
                outputFormat = 'txt';
                const selectedTxtMode = document.querySelector('input[name="pdfToTxtMode"]:checked');
                if (selectedTxtMode) {
                    formData.append('pdf_to_txt_mode', selectedTxtMode.value);
                } else {
                    formData.append('pdf_to_txt_mode', 'pymupdf');
                }
                break;
        }
    }
    formData.append('output_format', outputFormat);
    const csrfToken = window.getCookie('csrftoken');
    let apiUrl = '';
    if (window.currentSelectedMainTab === 'fileToPdf') {
        apiUrl = '/api/file-to-pdf/';
    } else if (window.currentSelectedMainTab === 'imgToFile') {
        apiUrl = '/api/img-to-file/';
    } else if (window.currentSelectedMainTab === 'pdfToFile') {
        apiUrl = '/api/pdf-to-file/';
    } else {
        window.isConverting = false;
        updateMainTabButtonsState(false);
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
        return;
    }
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
        const errorData = {
            results: [{ original_name: '错误', converted_name: '-', status: 'error', message: '客户端请求错误，详情请查看控制台。' }],
            merge_output: false,
        };
        displayConvertedFiles(errorData);
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
    })
    .finally(() => {
        window.isConverting = false;
        updateMainTabButtonsState(false);
        const btn = document.getElementById('startConversionBtn');
        btn.disabled = false;
        btn.textContent = '开始转换';
        btn.style.backgroundColor = '#007bff';
        btn.style.borderColor = '#007bff';
    });
}
window.startConversion = startConversion;

function displayConvertedFiles(data) {
    const container = document.getElementById('convertedFilesTableContainer');
    if (!container) return;
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
window.displayConvertedFiles = displayConvertedFiles; 