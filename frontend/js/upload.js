'use strict';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const COMPRESS_THRESHOLD = 4 * 1024 * 1024; // compress if > 4MB
const COMPRESS_MAX_WIDTH = 1920;
const COMPRESS_QUALITY = 0.88;
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp']);

const Upload = (() => {
  let currentFile = null;
  let currentBlob = null;
  let onFileReady = null;

  function init(callback) {
    onFileReady = callback;
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    const changeBtn = document.getElementById('changeBtn');

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') input.click(); });
    input.addEventListener('change', () => handleFiles(input.files));

    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      handleFiles(e.dataTransfer.files);
    });

    changeBtn.addEventListener('click', () => {
      reset();
      input.click();
    });
  }

  function handleFiles(files) {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!ALLOWED_TYPES.has(file.type.toLowerCase())) {
      showError('Unsupported file type. Please use JPEG, PNG, or WEBP.');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      showError('File is too large. Maximum size is 10MB.');
      return;
    }

    currentFile = file;
    showPreview(file);

    if (file.size > COMPRESS_THRESHOLD) {
      compressImage(file).then((blob) => {
        currentBlob = blob;
      });
    } else {
      currentBlob = file;
    }
  }

  function showPreview(file) {
    const preview = document.getElementById('previewArea');
    const img = document.getElementById('previewImg');
    const zone = document.getElementById('uploadZone');

    const url = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(url);
    img.src = url;

    zone.classList.add('hidden');
    preview.classList.remove('hidden');
  }

  function compressImage(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let { width, height } = img;
          if (width > COMPRESS_MAX_WIDTH) {
            height = Math.round((height * COMPRESS_MAX_WIDTH) / width);
            width = COMPRESS_MAX_WIDTH;
          }
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob((blob) => resolve(blob || file), 'image/jpeg', COMPRESS_QUALITY);
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function reset() {
    currentFile = null;
    currentBlob = null;
    const zone = document.getElementById('uploadZone');
    const preview = document.getElementById('previewArea');
    const input = document.getElementById('fileInput');
    zone.classList.remove('hidden');
    preview.classList.add('hidden');
    input.value = '';
  }

  function getBlob() { return currentBlob; }
  function getFile() { return currentFile; }

  function showError(msg) {
    // Delegate to app error handler if available
    if (window.App && window.App.showError) {
      window.App.showError('Invalid File', msg);
    } else {
      alert(msg);
    }
  }

  return { init, reset, getBlob, getFile };
})();
