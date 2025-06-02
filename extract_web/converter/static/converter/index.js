let currentSelectedMainNavigation = 'docConversion'; // Keep track of main navigation
let currentSelectedMainTab = 'imgToFile'; 
let currentSelectedSubTab = 'imgToWord'; 
let currentSelectedSpeechSubTab = 'speechToText'; // For speech processing
let isConverting = false; // General flag for any background process
const uploadedFiles = [];  // For document conversion multi-file
let uploadedVideoFile = null; // For single video file in video analysis
let uploadedAudioFile = null; // For single audio file in speech processing

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
    } else {
        console.log("[selectSubTab] All PDF options HIDDEN");
    }
    // --- END NEW ---
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
    const maxFileSize = 10 * 1024 * 1024; // 10MB

    for (const file of incomingFiles) {
        if (uploadedFiles.length >= maxFiles) {
            alert(`最多只能上传 ${maxFiles} 个文件。`);
            break;
        }
        if (file.size > maxFileSize) {
            alert(`文件 "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)} MB) 超过了10MB的大小限制。`);
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
        formData.append('images', file); // 'images' is the key expected by the backend
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
        } else {
            outputFormat = 'docx';
        }
    } else if (currentSelectedMainTab === 'fileToPdf') {
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
        } else if (result.status === 'error' || result.status.includes('_error')) {
            statusBadge.classList.add('status-error');
        } else {
            statusBadge.classList.add('status-processing'); // Or a default style
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
    // Initialize the view based on currentSelectedMainNavigation
    // Pass true to prevent clearing inputs on initial load if state needs to be preserved (e.g. page refresh with form data)
    selectMainNavigation(currentSelectedMainNavigation, true);

    const convertBtn = document.getElementById('startConversionBtn'); // For doc conversion
    if(convertBtn) {
        convertBtn.addEventListener('click', startConversion);
    }
    // renderFileList(); // Called by selectMainNavigation -> showTab -> selectSubTab which is fine

    // Note: Specific initializations for video and speech tabs are now called within selectMainNavigation
});

// --- Main Navigation Logic ---
function selectMainNavigation(navId, isInitialLoad = false) {
    console.log(`[selectMainNavigation] Called with navId: ${navId}, isInitialLoad: ${isInitialLoad}`);
    if (isConverting && !isInitialLoad) {
        console.log("[selectMainNavigation] Processing active. Main navigation switch prevented.");
        return;
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
    // Document Conversion
    clearFileList(); // Clears uploadedFiles array and UI for doc conversion
    clearConvertedFilesList(); // Clears results table for doc conversion
    
    // Video Analysis
    clearVideoFileAndResults(); // Clears video file selection and results

    // Speech Processing
    clearAudioFileAndResult(); // Clears audio file selection and results
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
    // Logic for ASR specific elements (URL input, buttons, etc.)
    initializeAsrFunctionality();
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
    console.log(`[showSpeechSubTab] Current active speech sub-tab: ${currentSelectedSpeechSubTab}`);
}

function initializeAsrFunctionality() {
    console.log("[initializeAsrFunctionality] Setting up ASR event listeners.");
    const audioUrlInput = document.getElementById('audioUrlInput');
    const startAsrBtn = document.getElementById('startAsrBtn');
    const clearAsrFieldsBtn = document.getElementById('clearAsrFieldsBtn');
    const asrLoadingIndicator = document.getElementById('asrLoadingIndicator');
    const asrTranscriptionOutput = document.getElementById('asrTranscriptionOutput');
    const asrErrorOutput = document.getElementById('asrErrorOutput');

    if (startAsrBtn) {
        startAsrBtn.addEventListener('click', async function() {
            const audioUrl = audioUrlInput.value.trim();
            if (!audioUrl) {
                asrErrorOutput.textContent = '请输入有效的音频文件URL。';
                asrTranscriptionOutput.textContent = '';
                audioUrlInput.focus();
                return;
            }
            try {
                new URL(audioUrl);
            } catch (_) {
                asrErrorOutput.textContent = '请输入一个格式正确的URL。';
                asrTranscriptionOutput.textContent = '';
                audioUrlInput.focus();
                return;
            }

            asrLoadingIndicator.style.display = 'block';
            startAsrBtn.disabled = true;
            clearAsrFieldsBtn.disabled = true;
            audioUrlInput.disabled = true;
            asrTranscriptionOutput.textContent = '';
            asrErrorOutput.textContent = '';
            console.log("[ASR] Starting recognition for URL:", audioUrl);

            try {
                const response = await fetch("/api/speech-to-text/", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ audio_url: audioUrl })
                });

                const result = await response.json();
                console.log("[ASR] Received response:", result);

                if (response.ok && result.status === 'success') {
                    asrTranscriptionOutput.textContent = result.transcription || '(未识别到文本)';
                    if (result.duration_seconds !== undefined) {
                         console.log(`[ASR] Request ${result.request_id} completed in ${result.duration_seconds}s.`);
                         addNotification(`语音识别成功 (用时 ${result.duration_seconds}s)`, 'success');
                    } else {
                        addNotification('语音识别成功!', 'success');
                    }
                } else {
                    const errorMsg = result.message || '语音识别失败，请检查URL或稍后再试。';
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
                clearAsrFieldsBtn.disabled = false;
                audioUrlInput.disabled = false;
                console.log("[ASR] Recognition process finished.");
            }
        });
    } else {
        console.error("startAsrBtn not found during ASR initialization.");
    }

    if (clearAsrFieldsBtn) {
        clearAsrFieldsBtn.addEventListener('click', function() {
            if (audioUrlInput) audioUrlInput.value = '';
            if (asrTranscriptionOutput) asrTranscriptionOutput.textContent = '';
            if (asrErrorOutput) asrErrorOutput.textContent = '';
            if (audioUrlInput) audioUrlInput.focus();
            console.log("[ASR] Fields cleared.");
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
        const response = await fetch("{% url 'converter:api_process_video' %}", {
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

        const result = await response.json();
        console.log("[processVideo] Received response:", result);

        if (result.task_id) {
            addNotification('视频处理任务已启动，ID: ' + result.task_id, 'info');
            if(progressBarContainer) progressBarContainer.style.display = 'block';
            if(progressListContainer) progressListContainer.style.display = 'block';
            if(spinner) spinner.style.display = 'none'; // Hide spinner, show progress bar
            pollVideoTaskStatus(result.task_id);
        } else if (result.error) {
             addNotification('视频处理启动失败: ' + result.error, 'error');
             displayVideoProcessingResults({ error: result.error });
        } else {
            // Handle direct result if not using tasks (though task_id is expected)
            displayVideoProcessingResults(result);
        }

    } catch (error) {
        console.error('[processVideo] API call failed:', error);
        addNotification('调用视频处理服务时发生网络或未知错误。详情请查看控制台。', 'error');
        displayVideoProcessingResults({ error: '网络或客户端错误，无法连接到服务器。' });
    } finally {
        // isConverting and button states will be reset by pollVideoTaskStatus or if an error occurs before polling
        // If no task_id, means direct error or direct result, so we can re-enable here.
        if (!document.getElementById('videoProgressBarContainer').style.display || document.getElementById('videoProgressBarContainer').style.display === 'none') {
            isConverting = false;
            updateMainNavigationButtonStates(false);
            if(processBtn) processBtn.disabled = false;
            if(spinner) spinner.style.display = 'none';
        }
    }
}

async function pollVideoTaskStatus(taskId) {
    console.log(`[pollVideoTaskStatus] Starting to poll for task ID: ${taskId}`);
    const progressBar = document.getElementById('videoProgressBar');
    const progressList = document.getElementById('videoProgressList');
    const resultsContainer = document.getElementById('videoProcessingResultsTableContainer');
    const processBtn = document.querySelector('#videoAnalysisContent button[onclick="processVideo()"]');

    let intervalId = setInterval(async () => {
        try {
            const response = await fetch(`/api/task_status/${taskId}/`);
            if (!response.ok) {
                console.error(`[pollVideoTaskStatus] Error fetching status for ${taskId}: ${response.status}`);
                // Potentially stop polling on certain client/server errors like 404 Not Found for task
                if (response.status === 404) {
                    clearInterval(intervalId);
                    addNotification(`任务 ${taskId} 未找到或已过期。`, 'error');
                    displayVideoProcessingResults({ error: `任务 ${taskId} 未找到。` });
                    resetVideoProcessingUI(processBtn);
                }
                return; 
            }
            const data = await response.json();
            console.log(`[pollVideoTaskStatus] Status for ${taskId}:`, data);

            if (progressBar) {
                progressBar.style.width = data.progress + '%';
                progressBar.textContent = data.progress + '%';
            }
            if (progressList && data.current_step) {
                const newItem = document.createElement('li');
                newItem.textContent = `[${new Date().toLocaleTimeString()}] ${data.current_step}`;
                progressList.appendChild(newItem);
                progressList.scrollTop = progressList.scrollHeight; // Auto-scroll
            }

            if (data.state === 'SUCCESS') {
                clearInterval(intervalId);
                addNotification('视频处理完成!', 'success');
                if (data.result && data.result.message) { // For direct messages from task
                     addNotification(data.result.message, 'info');
                }
                displayVideoProcessingResults(data.result || {}); 
                resetVideoProcessingUI(processBtn);
            } else if (data.state === 'FAILURE') {
                clearInterval(intervalId);
                const errorDetail = data.result && data.result.error ? data.result.error : '未知错误';
                addNotification(`视频处理失败: ${errorDetail}`, 'error');
                displayVideoProcessingResults({ error: errorDetail, details: data.result });
                resetVideoProcessingUI(processBtn);
            } else if (data.state === 'PENDING' || data.state === 'PROGRESS' || data.state === 'STARTED') {
                // Continue polling
                console.log(`[pollVideoTaskStatus] Task ${taskId} is ${data.state}. Progress: ${data.progress}%.`);
            } else {
                // Unknown state or task disappeared
                clearInterval(intervalId);
                addNotification(`任务 ${taskId} 状态未知或已中断。`, 'warning');
                displayVideoProcessingResults({ error: `任务 ${taskId} 状态未知或已中断。` });
                resetVideoProcessingUI(processBtn);
            }
        } catch (error) {
            console.error('[pollVideoTaskStatus] Error polling task status:', error);
            // Don't clear interval on network error, allow it to retry
        }
    }, 3000); // Poll every 3 seconds
}
    
function resetVideoProcessingUI(processBtn) {
    isConverting = false;
    updateMainNavigationButtonStates(false);
    if (processBtn) processBtn.disabled = false;
    const spinner = document.getElementById('videoProcessingSpinner');
    if (spinner) spinner.style.display = 'none';
    // Keep progress bar visible with final status
}

function displayVideoProcessingResults(data) {
    const container = document.getElementById('videoProcessingResultsTableContainer');
    if (!container) return;
    container.innerHTML = ''; // Clear previous results

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

