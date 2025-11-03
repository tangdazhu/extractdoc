// 视频分析相关逻辑
// 依赖 common.js 中的全局变量和工具函数

function initializeVideoTab() {
    const videoInput = document.getElementById('videoFileForAnalysisInput');
    if (videoInput) {
        videoInput.addEventListener('change', handleVideoFileSelect);
    }
    clearVideoFileAndResults();
}
window.initializeVideoTab = initializeVideoTab;

function handleVideoFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        window.uploadedVideoFile = file;
        const fileListUI = document.getElementById('videoFileList');
        if (fileListUI) {
            fileListUI.innerHTML = `<li>${window.escapeHtml(file.name)} (${(file.size / 1024 / 1024).toFixed(2)} MB)</li>`;
        }
    } else {
        window.uploadedVideoFile = null;
        const fileListUI = document.getElementById('videoFileList');
        if (fileListUI) {
            fileListUI.innerHTML = '';
        }
    }
}
window.handleVideoFileSelect = handleVideoFileSelect;

function clearVideoFileAndResults() {
    const videoInput = document.getElementById('videoFileForAnalysisInput');
    if (videoInput) videoInput.value = '';
    window.uploadedVideoFile = null;
    const fileListUI = document.getElementById('videoFileList');
    if (fileListUI) fileListUI.innerHTML = '';
    const resultsContainer = document.getElementById('videoProcessingResultsTableContainer');
    if (resultsContainer) resultsContainer.innerHTML = '';
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
    const processBtn = document.querySelector('#videoAnalysisContent button[onclick="processVideo()"]');
    if (processBtn) processBtn.disabled = false;
}
window.clearVideoFileAndResults = clearVideoFileAndResults;

async function processVideo() {
    if (!window.uploadedVideoFile) {
        window.addNotification('请先选择一个视频文件。', 'warning');
        return;
    }
    const sceneDetectionThreshold = document.getElementById('sceneDetectionThreshold').value;
    const similarityThreshold = document.getElementById('similarityThreshold').value;
    const minGroupInterval = document.getElementById('minGroupInterval').value;
    
    if (!sceneDetectionThreshold || parseFloat(sceneDetectionThreshold) <= 0) {
        window.addNotification('请输入有效的场景检测阈值。', 'warning');
        return;
    }
    if (!similarityThreshold || parseInt(similarityThreshold) < 1) {
        window.addNotification('请输入有效的相似度阈值 (至少为1)。', 'warning');
        return;
    }
    if (!minGroupInterval || parseInt(minGroupInterval) < 1) {
        window.addNotification('请输入有效的最小场景间隔 (至少为1)。', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('video_file', window.uploadedVideoFile);
    formData.append('scene_detection_threshold', sceneDetectionThreshold);
    formData.append('similarity_threshold', similarityThreshold);
    formData.append('min_group_interval', minGroupInterval);
    const csrfToken = window.getCookie('csrftoken');
    const processBtn = document.querySelector('#videoAnalysisContent button[onclick="processVideo()"]');
    const spinner = document.getElementById('videoProcessingSpinner');
    const progressBarContainer = document.getElementById('videoProgressBarContainer');
    const progressBar = document.getElementById('videoProgressBar');
    const progressListContainer = document.getElementById('videoProgressListContainer');
    const progressList = document.getElementById('videoProgressList');
    const resultsContainer = document.getElementById('videoProcessingResultsTableContainer');
    processBtn.disabled = true;
    if(spinner) spinner.style.display = 'block';
    if(progressBarContainer) progressBarContainer.style.display = 'none';
    if(progressListContainer) progressListContainer.style.display = 'none';
    if(progressList) progressList.innerHTML = '';
    if(resultsContainer) resultsContainer.innerHTML = '';
    window.isConverting = true;
    if (typeof window.updateMainNavigationButtonStates === 'function') window.updateMainNavigationButtonStates(true);
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
            } catch (e) {}
            window.addNotification(`视频处理失败: ${errorData.message || response.statusText}`, 'error');
            displayVideoProcessingResults({ error: errorData.message || response.statusText });
            return;
        }
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
            buffer = lines.pop();
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'progress') {
                            if(progressBar && typeof data.percent === 'number') {
                                progressBar.style.width = data.percent + '%';
                                progressBar.textContent = data.percent + '%';
                            }
                        } else if (data.type === 'info') {
                            if(progressList) {
                                const li = document.createElement('li');
                                li.textContent = data.message;
                                progressList.appendChild(li);
                                progressList.scrollTop = progressList.scrollHeight;
                            }
                        } else if (data.type === 'result') {
                            displayVideoProcessingResults({ results: data.results });
                        } else if (data.type === 'error') {
                            displayVideoProcessingResults({ error: data.message });
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (error) {
        window.addNotification('调用视频处理服务时发生网络或未知错误。详情请查看控制台。', 'error');
        displayVideoProcessingResults({ error: '网络或客户端错误，无法连接到服务器。' });
    } finally {
        window.isConverting = false;
        if (typeof window.updateMainNavigationButtonStates === 'function') window.updateMainNavigationButtonStates(false);
        if(processBtn) processBtn.disabled = false;
        if(spinner) spinner.style.display = 'none';
    }
}
window.processVideo = processVideo;

function displayVideoProcessingResults(data) {
    const container = document.getElementById('videoProcessingResultsTableContainer');
    if (!container) return;
    container.innerHTML = '';
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
    if (data.error) {
        container.innerHTML = `<p class="text-danger">处理失败: ${window.escapeHtml(data.error)}</p>`;
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
    if (data.processed_video_filename && data.download_url) {
        const row = tbody.insertRow();
        row.insertCell().textContent = data.output_type === 'ppt' ? 'PPT 文稿' : '处理后视频';
        row.insertCell().textContent = data.processed_video_filename;
        const actionCell = row.insertCell();
        const downloadLink = document.createElement('a');
        downloadLink.href = data.download_url;
        downloadLink.textContent = '下载 ' + (data.output_type === 'ppt' ? 'PPT' : '视频');
        downloadLink.className = 'download-link';
        downloadLink.target = '_blank';
        actionCell.appendChild(downloadLink);
    }
    if (data.output_files && data.output_files.length > 0) {
        data.output_files.forEach(fileInfo => {
            const row = tbody.insertRow();
            row.insertCell().textContent = '截图帧';
            row.insertCell().textContent = fileInfo.name;
            const actionCell = row.insertCell();
            if (fileInfo.url) {
                const downloadLink = document.createElement('a');
                downloadLink.href = fileInfo.url;
                downloadLink.textContent = '下载图片';
                downloadLink.className = 'download-link';
                downloadLink.target = '_blank';
                actionCell.appendChild(downloadLink);
            } else {
                actionCell.textContent = '-';
            }
        });
    }
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
    if (data.message) {
         const successMsgP = document.createElement('p');
         successMsgP.className = 'text-success mt-2';
         successMsgP.textContent = data.message;
         container.insertBefore(successMsgP, table);
    }
    if (data.duration_seconds !== undefined) {
        const durationP = document.createElement('p');
        durationP.className = 'text-muted small mt-2';
        durationP.textContent = `视频处理总用时: ${data.duration_seconds.toFixed(2)} 秒`;
        container.appendChild(durationP);
    }
}
window.displayVideoProcessingResults = displayVideoProcessingResults; 