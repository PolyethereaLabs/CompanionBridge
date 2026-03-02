// CompanionBridge JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // File upload form validation
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const conversationsFileInput = document.getElementById('conversations_file');

    if (uploadForm) {
        // File size validation
        function validateFileSize(file, maxSizeMB = 100) {
            const maxSize = maxSizeMB * 1024 * 1024; // Convert to bytes
            return file.size <= maxSize;
        }

        // File type validation
        function validateFileType(file, expectedExtension) {
            return file.name.toLowerCase().endsWith(expectedExtension);
        }

        // Show file information
        function showFileInfo(input, file) {
            const fileInfo = input.parentElement.querySelector('.file-info');
            if (fileInfo) fileInfo.remove();

            const info = document.createElement('div');
            info.className = 'file-info text-muted small mt-1';
            info.innerHTML = `
                <i class="bi bi-file-check me-1"></i>
                ${file.name} (${formatFileSize(file.size)})
            `;
            input.parentElement.appendChild(info);
        }

        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        // Real-time file validation
        function validateFile(input, expectedExtension) {
            const file = input.files[0];
            if (!file) return true;

            // Remove previous error messages
            const existingError = input.parentElement.querySelector('.file-error');
            if (existingError) existingError.remove();

            let isValid = true;
            let errorMessage = '';

            // Check file type
            if (!validateFileType(file, expectedExtension)) {
                isValid = false;
                errorMessage = `Please select a ${expectedExtension} file`;
            }

            // Check file size
            if (isValid && !validateFileSize(file)) {
                isValid = false;
                errorMessage = 'File size must be less than 100MB';
            }

            if (isValid) {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
                showFileInfo(input, file);
            } else {
                input.classList.remove('is-valid');
                input.classList.add('is-invalid');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'file-error text-danger small mt-1';
                errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${errorMessage}`;
                input.parentElement.appendChild(errorDiv);
            }

            updateSubmitButton();
            return isValid;
        }

        // Update submit button state
        function updateSubmitButton() {
            const conversationsValid = conversationsFileInput && conversationsFileInput.files.length > 0 && !conversationsFileInput.classList.contains('is-invalid');
            
            uploadBtn.disabled = !conversationsValid;
        }

        // File input event listeners
        if (conversationsFileInput) {
            conversationsFileInput.addEventListener('change', function() {
                validateFile(this, '.json');
            });
        }

        // Form submission with real progress tracking
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Always prevent default submission
            
            const conversationsFile = conversationsFileInput.files[0];
            
            if (!conversationsFile) {
                alert('Please select a JSON file before uploading.');
                return;
            }

            if (!validateFile(conversationsFileInput, '.json')) {
                alert('Please fix file validation errors before uploading.');
                return;
            }

            // Start real upload with progress tracking
            uploadFileWithProgress(this);
        });

        // Real file upload with progress tracking
        function uploadFileWithProgress(form) {
            // Show progress UI
            showProcessingFeedback();
            
            // Create FormData from the form
            const formData = new FormData(form);
            
            // Create XMLHttpRequest for progress tracking
            const xhr = new XMLHttpRequest();
            
            // Upload progress event listener
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    updateProgressBar(percentComplete);
                }
            });
            
            // Handle upload completion
            xhr.addEventListener('load', function() {
                console.log('Upload completed. Status:', xhr.status);
                console.log('Response text:', xhr.responseText);
                console.log('Response headers:', xhr.getAllResponseHeaders());
                
                if (xhr.status === 200) {
                    // Parse JSON response from Flask
                    try {
                        const response = JSON.parse(xhr.responseText);
                        console.log('Parsed response:', response);
                        
                        if (response.success && response.redirect_url) {
                            // Update status to complete and redirect
                            updateProgressBar(100);
                            setTimeout(() => {
                                window.location.href = response.redirect_url;
                            }, 500);
                        } else {
                            console.log('Response indicates failure:', response);
                            showUploadError(response.message || 'Upload failed. Please try again.');
                        }
                    } catch (e) {
                        console.log('JSON parse error:', e);
                        console.log('Raw response:', xhr.responseText);
                        
                        // Check if it's an HTML redirect response (common in production)
                        if (xhr.responseText.includes('<!DOCTYPE html>') || xhr.responseText.includes('<html')) {
                            // This is likely a successful redirect response from Flask
                            console.log('Detected HTML redirect response');
                            updateProgressBar(100);
                            
                            // Try to extract session ID from form action or use a fallback redirect
                            const formAction = uploadForm.action;
                            const baseUrl = formAction.substring(0, formAction.lastIndexOf('/'));
                            
                            setTimeout(() => {
                                // Try to go to the select page
                                window.location.href = baseUrl.replace('/upload', '/select');
                            }, 500);
                        } else {
                            showUploadError('Upload completed but received unexpected response format.');
                        }
                    }
                } else {
                    console.log('Non-200 status code:', xhr.status);
                    // Handle error response
                    try {
                        const response = JSON.parse(xhr.responseText);
                        showUploadError(response.message || `Upload failed with status ${xhr.status}. Please try again.`);
                    } catch (e) {
                        showUploadError(`Upload failed with status ${xhr.status}. Please try again.`);
                    }
                }
            });
            
            // Handle upload errors
            xhr.addEventListener('error', function() {
                showUploadError('Upload failed. Please check your connection and try again.');
            });
            
            // Send the request with AJAX header
            xhr.open('POST', form.action);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
        }
        
        // Show progress UI
        function showProcessingFeedback() {
            // Hide the upload button
            uploadBtn.style.display = 'none';
            
            // Show the existing progress container
            const progressContainer = document.getElementById('progressContainer');
            progressContainer.style.display = 'block';
            progressContainer.className = 'text-center mt-4';
            progressContainer.innerHTML = `
                <div class="d-flex align-items-center justify-content-center">
                    <div class="spinner-border text-primary me-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div>
                        <h6 class="mb-1">Uploading file...</h6>
                        <small class="text-muted" id="uploadStatus">Starting upload...</small>
                    </div>
                </div>
                <div class="progress mt-3" style="height: 12px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                         role="progressbar" style="width: 0%" id="realProgressBar"></div>
                </div>
            `;
        }
        
        // Update progress bar with real values
        function updateProgressBar(percentComplete) {
            const progressBar = document.getElementById('realProgressBar');
            const statusText = document.getElementById('uploadStatus');
            
            if (progressBar) {
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
            
            if (statusText) {
                if (percentComplete < 100) {
                    statusText.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                } else {
                    statusText.textContent = 'Processing your conversation data...';
                }
            }
        }
        
        // Show upload error
        function showUploadError(message) {
            const progressContainer = document.getElementById('progressContainer');
            progressContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
            
            // Show the upload button again
            uploadBtn.style.display = 'block';
        }
        
        // Reset button to original state
        function resetButtonState() {
            uploadBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Upload & Select Conversations';
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('processing');
        }
        




        // Initialize button state
        updateSubmitButton();
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-info)');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) return;
        
        setTimeout(() => {
            if (alert.parentElement) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentElement) {
                        alert.remove();
                    }
                }, 150);
            }
        }, 5000);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Progress bar animation for processing page
    const progressBar = document.getElementById('progressBar');
    if (progressBar && window.location.pathname.includes('/process/')) {
        // Animate progress bar
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 95) {
                progress = 95;
                clearInterval(interval);
            }
            progressBar.style.width = progress + '%';
        }, 800);
    }

    // Copy session ID functionality
    const sessionIdElements = document.querySelectorAll('code');
    sessionIdElements.forEach(element => {
        if (element.textContent.length > 20) { // Likely a session ID
            element.style.cursor = 'pointer';
            element.title = 'Click to copy';
            element.addEventListener('click', function() {
                navigator.clipboard.writeText(this.textContent).then(() => {
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 1000);
                });
            });
        }
    });

    // Tooltip initialization for Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle download button click tracking
    const downloadBtn = document.querySelector('a[href*="/download/"]');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            // Track download event
            console.log('Identity file download initiated');
            
            // Show success message after a short delay
            setTimeout(() => {
                const alert = document.createElement('div');
                alert.className = 'alert alert-success alert-dismissible fade show mt-3';
                alert.innerHTML = `
                    <i class="bi bi-check-circle me-2"></i>
                    Download started! Your companion identity file is being downloaded.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                
                const cardBody = document.querySelector('.card-body');
                if (cardBody) {
                    cardBody.insertBefore(alert, cardBody.firstChild);
                }
            }, 500);
        });
    }
});

// Utility functions
function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <i class="bi bi-info-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alert, container.firstChild);
        
        // Auto dismiss after 4 seconds
        setTimeout(() => {
            if (alert.parentElement) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentElement) {
                        alert.remove();
                    }
                }, 150);
            }
        }, 4000);
    }
}

// Error handling for AJAX requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showNotification('An unexpected error occurred. Please try again.', 'danger');
});

// Page visibility change handling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible');
        // Refresh any real-time data if needed
    }
});
