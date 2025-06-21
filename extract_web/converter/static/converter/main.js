// main.js 入口 glue code
// 依赖 common.js、doc_conversion.js、video_analysis.js、speech_processing.js

document.addEventListener('DOMContentLoaded', function() {
    if (typeof selectMainNavigation === 'function') {
        selectMainNavigation(window.currentSelectedMainNavigation || 'docConversion', true);
    }
    // 绑定文档转换按钮
    const convertBtn = document.getElementById('startConversionBtn');
    if(convertBtn && typeof startConversion === 'function') {
        convertBtn.addEventListener('click', startConversion);
    }
    // 初始化拖拽上传
    const dropZone = document.getElementById('dropZone');
    const fileUpload = document.getElementById('fileUpload');
    if (dropZone && fileUpload) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, function(e) { e.preventDefault(); e.stopPropagation(); }, false);
        });
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, function() { dropZone.classList.add('border-primary'); }, false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, function() { dropZone.classList.remove('border-primary'); }, false);
        });
        dropZone.addEventListener('drop', function(e) {
            handleFiles(e.dataTransfer.files);
        }, false);
    }
});

function selectMainNavigation(navId, isInitialLoad = false) {
    if (window.isConverting && !isInitialLoad) return;
    document.getElementById('docConversionContent').style.display = 'none';
    document.getElementById('videoAnalysisContent').style.display = 'none';
    document.getElementById('speechProcessingContent').style.display = 'none';
    document.querySelectorAll('.sidebar-nav li button').forEach(btn => btn.classList.remove('active'));
    let activeContentDiv = null;
    window.currentSelectedMainNavigation = navId;
    switch (navId) {
        case 'docConversion':
            activeContentDiv = document.getElementById('docConversionContent');
            document.getElementById('navDocConversion').classList.add('active');
            if (typeof showTab === 'function') showTab(window.currentSelectedMainTab || 'imgToFile');
            break;
        case 'videoAnalysis':
            activeContentDiv = document.getElementById('videoAnalysisContent');
            document.getElementById('navVideoAnalysis').classList.add('active');
            if (typeof initializeVideoTab === 'function') initializeVideoTab();
            break;
        case 'speechProcessing':
            activeContentDiv = document.getElementById('speechProcessingContent');
            document.getElementById('navSpeechProcessing').classList.add('active');
            if (typeof initializeSpeechTab === 'function') initializeSpeechTab();
            break;
        case 'imageAnalysis':
            break;
    }
    if (activeContentDiv) {
        activeContentDiv.style.display = 'block';
    }
    if (!isInitialLoad && typeof clearAllInputAreas === 'function') {
        clearAllInputAreas();
    }
}
window.selectMainNavigation = selectMainNavigation;

function clearAllInputAreas() {
    if (typeof clearFileList === 'function') clearFileList();
    if (typeof clearConvertedFilesList === 'function') clearConvertedFilesList();
    if (typeof clearVideoFileAndResults === 'function') clearVideoFileAndResults();
    if (typeof clearAudioFileAndResult === 'function') clearAudioFileAndResult();
}
window.clearAllInputAreas = clearAllInputAreas; 