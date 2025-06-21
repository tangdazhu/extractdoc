// 通用全局变量
window.currentSelectedMainNavigation = 'docConversion';
window.currentSelectedMainTab = 'imgToFile';
window.currentSelectedSubTab = 'imgToWord';
window.currentSelectedSpeechSubTab = 'speechToText';
window.isConverting = false;
window.uploadedFiles = [];
window.uploadedVideoFile = null;
window.uploadedAudioFile = null;
window.ttsInitialized = false;

// 通用工具函数
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
window.getCookie = getCookie;

function addNotification(message, type) {
    console.log(`Notification (${type.toUpperCase()}): ${message}`);
}
window.addNotification = addNotification;

function escapeHtml(unsafe) {
    if (unsafe === null || typeof unsafe === 'undefined') return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
window.escapeHtml = escapeHtml; 