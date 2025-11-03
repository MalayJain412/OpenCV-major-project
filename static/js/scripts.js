// Global state
let currentStep = 'landing';
let selectedMode = null;
let selectedService = null;
let isConnected = false;
let sessionStartTime = null;
let statsInterval = null;

// Step management
const steps = ['landing', 'mode', 'service', 'demo'];
const stepElements = {
    landing: document.getElementById('step-landing'),
    mode: document.getElementById('step-mode'),
    service: document.getElementById('step-service'),
    demo: document.getElementById('step-demo')
};

// Service configurations
const serviceConfig = {
    fitness: {
        icon: 'fa-dumbbell',
        title: 'Fitness Tracking',
        services: {
            squat: { name: 'Squats', api: 'squat' },
            pushup: { name: 'Push-ups', api: 'pushup' },
            bicep: { name: 'Bicep Curls', api: 'bicep_curl' }
        }
    },
    surveillance: {
        icon: 'fa-shield-alt',
        title: 'Surveillance Monitoring',
        services: {
            'zone-detection': { name: 'Zone Detection', api: 'zone_detection' },
            'rapid-movement': { name: 'Rapid Movement', api: 'rapid_movement' },
            'fall-detection': { name: 'Fall Detection', api: 'fall_detection' }
        }
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function () {
    setupEventListeners();
    showStep('landing');
});

function setupEventListeners() {
    // Navigation buttons
    document.getElementById('start-demo-btn')?.addEventListener('click', () => navigateToStep('mode'));
    document.getElementById('back-to-landing')?.addEventListener('click', () => navigateToStep('landing'));
    document.getElementById('back-to-modes')?.addEventListener('click', () => navigateToStep('mode'));
    document.getElementById('back-to-services')?.addEventListener('click', () => navigateToStep('service'));

    // Back to mode buttons (using class selector)
    document.querySelectorAll('.back-to-mode').forEach(button => {
        button.addEventListener('click', () => navigateToStep('mode'));
    });

    // Mode selection
    document.getElementById('mode-fitness')?.addEventListener('click', () => selectMode('fitness'));
    document.getElementById('mode-surveillance')?.addEventListener('click', () => selectMode('surveillance'));

    // Service selection for fitness
    document.getElementById('service-squat')?.addEventListener('click', () => selectService('squat'));
    document.getElementById('service-pushup')?.addEventListener('click', () => selectService('pushup'));
    document.getElementById('service-bicep')?.addEventListener('click', () => selectService('bicep_curl'));

    // Service selection for surveillance  
    document.getElementById('service-zone-detection')?.addEventListener('click', () => selectService('zone_detection'));
    document.getElementById('service-rapid-movement')?.addEventListener('click', () => selectService('rapid_movement'));
    document.getElementById('service-fall-detection')?.addEventListener('click', () => selectService('fall_detection'));

    // Demo controls (only called in demo step)
    document.getElementById('start-btn')?.addEventListener('click', startDemo);
    document.getElementById('stop-btn')?.addEventListener('click', stopDemo);
    document.getElementById('reset-btn')?.addEventListener('click', resetDemo);
    document.getElementById('save-btn')?.addEventListener('click', saveSession);
    document.getElementById('audio-toggle-btn')?.addEventListener('click', toggleAudio);
    document.getElementById('refresh-logs')?.addEventListener('click', loadLogs);

    // Video feed error handling
    const videoFeed = document.getElementById('video-feed');
    if (videoFeed) {
        videoFeed.addEventListener('load', () => updateConnectionStatus(true));
        videoFeed.addEventListener('error', () => updateConnectionStatus(false));
    }
}

// Step navigation
function navigateToStep(step) {
    if (steps.includes(step)) {
        currentStep = step;
        showStep(step);
        updateProgressBar(step);
    }
}

function showStep(step) {
    console.log(`Showing step: ${step}, selectedMode: ${selectedMode}`); // Debug log

    // Hide all steps
    Object.values(stepElements).forEach(element => {
        if (element) element.classList.add('hidden');
    });

    // Show current step
    if (stepElements[step]) {
        stepElements[step].classList.remove('hidden');
    }

    // Handle service step visibility based on selected mode
    if (step === 'service') {
        // Ensure we have a selected mode when showing service step
        if (!selectedMode) {
            console.warn('No mode selected, redirecting to mode step');
            setTimeout(() => navigateToStep('mode'), 100);
            return;
        }
        showServiceSelection(selectedMode);
    } else {
        // Hide all service selections when not on service step
        document.getElementById('fitness-services')?.classList.add('hidden');
        document.getElementById('surveillance-services')?.classList.add('hidden');
    }

    // Update step indicator
    updateStepIndicators(step);
}

function updateStepIndicators(currentStep) {
    const stepNames = ['landing', 'mode', 'service', 'demo'];

    stepNames.forEach((step, index) => {
        const indicator = document.getElementById(`step-${index + 1}`);

        if (indicator) {
            const stepIndex = stepNames.indexOf(currentStep);

            // Remove all classes
            indicator.classList.remove('step-active', 'step-completed', 'step-upcoming');

            if (index < stepIndex) {
                // Completed step
                indicator.classList.add('step-completed');
            } else if (index === stepIndex) {
                // Current step
                indicator.classList.add('step-active');
            } else {
                // Future step
                indicator.classList.add('step-upcoming');
            }
        }
    });
}

function updateProgressBar(step) {
    const progress = document.getElementById('progress-bar');
    if (progress) {
        const stepIndex = steps.indexOf(step);
        const progressPercent = ((stepIndex + 1) / steps.length) * 100;
        progress.style.width = progressPercent + '%';
    }
}

// Mode selection
function selectMode(mode) {
    selectedMode = mode;

    // Update UI to show selected mode
    document.querySelectorAll('.mode-option').forEach(option => {
        option.classList.remove('ring-4', 'ring-blue-200', 'transform', 'scale-105');
    });

    const selectedOption = document.getElementById(`mode-${mode}`);
    if (selectedOption) {
        selectedOption.classList.add('ring-4', 'ring-blue-200', 'transform', 'scale-105');
    }

    // Auto-navigate to service selection after a brief delay only if on mode step
    if (currentStep === 'mode') {
        setTimeout(() => {
            navigateToStep('service');
        }, 800);
    }
}

function showServiceSelection(mode) {
    // Always hide all service selections first
    document.getElementById('fitness-services')?.classList.add('hidden');
    document.getElementById('surveillance-services')?.classList.add('hidden');

    // Only show services if we have a selected mode and are on service step
    if (mode && currentStep === 'service') {
        if (mode === 'fitness') {
            document.getElementById('fitness-services')?.classList.remove('hidden');
        } else if (mode === 'surveillance') {
            document.getElementById('surveillance-services')?.classList.remove('hidden');
        }
    }
}

// Reset UI state for clean navigation
function resetUIState() {
    // Remove selection highlights from all mode cards
    document.querySelectorAll('.service-card').forEach(card => {
        card.classList.remove('ring-4', 'ring-blue-200', 'transform', 'scale-105');
    });
}



// Service selection
function selectService(service) {
    selectedService = service;

    // Update UI to show selected service
    resetUIState();

    const selectedCard = document.getElementById(`service-${service.replace('_', '-')}`);
    if (selectedCard) {
        selectedCard.classList.add('ring-4', 'ring-blue-200', 'transform', 'scale-105');
    }

    // Auto-navigate to demo after a brief delay only if on service step
    if (currentStep === 'service') {
        setTimeout(() => {
            navigateToStep('demo');
            initializeDemo();
        }, 800);
    }
}

function initializeDemo() {
    // Update demo UI with selected mode and service
    const demoTitle = document.getElementById('demo-title');
    const demoSubtitle = document.getElementById('demo-subtitle');
    const demoIcon = document.getElementById('demo-mode-icon');

    if (demoTitle && demoSubtitle) {
        const modeTitle = selectedMode === 'fitness' ? 'Fitness Tracking' : 'Surveillance Monitoring';
        const serviceTitle = getServiceTitle(selectedService);

        demoTitle.textContent = `${modeTitle}: ${serviceTitle}`;
        demoSubtitle.textContent = `Real-time ${serviceTitle.toLowerCase()} analysis`;
    }

    // Update mode icon
    if (demoIcon) {
        const icon = demoIcon.querySelector('i');
        if (selectedMode === 'fitness') {
            icon.className = 'fas fa-dumbbell text-white';
            demoIcon.className = 'gradient-fitness p-2 rounded-lg';
        } else if (selectedMode === 'surveillance') {
            icon.className = 'fas fa-shield-alt text-white';
            demoIcon.className = 'gradient-surveillance p-2 rounded-lg';
        }
    }

    updateSessionInfo();
    updateStatsDisplay();
}

function getServiceTitle(service) {
    const titles = {
        'squat': 'Squats',
        'pushup': 'Push-ups',
        'bicep_curl': 'Bicep Curls',
        'zone_detection': 'Zone Detection',
        'rapid_movement': 'Rapid Movement',
        'fall_detection': 'Fall Detection'
    };
    return titles[service] || service;
}

// Demo controls
async function startDemo() {
    try {
        console.log('Starting demo with mode:', selectedMode, 'service:', selectedService);

        // First set the mode
        if (selectedMode) {
            const modeResponse = await fetch(`/api/mode/${selectedMode}`, {
                method: 'POST'
            });
            const modeData = await modeResponse.json();
            console.log('Mode set response:', modeData);

            if (!modeData.success) {
                throw new Error('Failed to set mode');
            }
        }

        // Set specific service/exercise type if needed
        if (selectedMode === 'fitness' && selectedService) {
            const exerciseResponse = await fetch(`/api/exercise/set/${selectedService}`, {
                method: 'POST'
            });
            const exerciseData = await exerciseResponse.json();
            console.log('Exercise set response:', exerciseData);
        }
        
        // Set surveillance service if needed
        if (selectedMode === 'surveillance' && selectedService) {
            const serviceResponse = await fetch(`/api/surveillance/service/${selectedService}`, {
                method: 'POST'
            });
            const serviceData = await serviceResponse.json();
            console.log('Surveillance service set response:', serviceData);
        }

        // Initialize demo UI before starting
        initializeDemo();

        // Initialize demo UI before starting
        initializeDemo();

        // Show loading state
        updateConnectionStatus(false, 'Starting camera...');

        // Start camera and session
        const startResponse = await fetch('/api/control/start', { method: 'POST' });
        const startData = await startResponse.json();
        console.log('Start response:', startData);

        if (startData.success) {
            sessionStartTime = new Date();
            updateDemoControls(true);
            updateConnectionStatus(true, 'Connected');

            // Start real-time stats updates
            if (statsInterval) {
                clearInterval(statsInterval);
            }
            statsInterval = setInterval(updateStats, 1000); // Every 1 second
            updateStats(); // Immediate first update
            updateSessionInfo();
            
            console.log('Demo started successfully');
        } else {
            updateConnectionStatus(false, 'Connection failed');
            throw new Error(startData.error || 'Failed to start session');
        }
    } catch (error) {
        console.error('Error starting demo:', error);
        updateConnectionStatus(false);
        alert('Error starting demo. Please check camera connection and backend.');
    }
}

async function stopDemo() {
    try {
        updateConnectionStatus(false, 'Stopping...');
        
        const response = await fetch('/api/control/stop', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            updateDemoControls(false);
            updateConnectionStatus(false, 'Stopped');
            stopStatsUpdates();
            resetStats();
            console.log('Demo stopped successfully');
        } else {
            console.error('Failed to stop demo:', data.error);
        }
    } catch (error) {
        console.error('Error stopping demo:', error);
        updateConnectionStatus(false, 'Error stopping');
    }
}

async function resetDemo() {
    try {
        const response = await fetch('/api/control/reset', { method: 'POST' });
        await response.json();
        resetStats();
    } catch (error) {
        console.error('Error resetting demo:', error);
    }
}

async function setModeAndService(mode, service) {
    // Set mode
    await fetch(`/api/mode/${mode}`, { method: 'POST' });

    // Set exercise type for fitness mode
    if (mode === 'fitness' && service) {
        await fetch(`/api/exercise/set/${service}`, { method: 'POST' });
    }
}

function updateDemoControls(isActive) {
    const startBtn = document.getElementById('start-demo-btn');
    const stopBtn = document.getElementById('stop-demo-btn');

    if (startBtn && stopBtn) {
        if (isActive) {
            startBtn.classList.add('hidden');
            stopBtn.classList.remove('hidden');
        } else {
            startBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
        }
    }
}

async function saveSession() {
    try {
        const response = await fetch('/api/session/save', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            alert('Session saved successfully!');
            loadLogs(); // Refresh logs
        } else {
            alert('Error saving session: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving session:', error);
        alert('Error saving session');
    }
}

async function toggleAudio() {
    try {
        const response = await fetch('/api/audio/toggle', { method: 'POST' });
        const data = await response.json();

        const audioBtn = document.getElementById('audio-toggle-btn');
        if (audioBtn) {
            const icon = audioBtn.querySelector('i');
            const status = document.getElementById('audio-status');

            if (data.success) {
                if (data.audio_enabled) {
                    if (icon) icon.className = 'fas fa-volume-up mr-1';
                    if (status) status.textContent = 'Audio';
                    audioBtn.className = 'bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg transition font-medium';
                } else {
                    if (icon) icon.className = 'fas fa-volume-mute mr-1';
                    if (status) status.textContent = 'Muted';
                    audioBtn.className = 'bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition font-medium';
                }
            }
        }
    } catch (error) {
        console.error('Error toggling audio:', error);
    }
}



async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const stats = await response.json();
        console.log('Stats received:', stats); // Debug log

        // Update connection status based on camera status
        if (stats.is_running && stats.camera_active) {
            updateConnectionStatus(true);
        } else if (stats.is_running && !stats.camera_active) {
            updateConnectionStatus(false, 'Camera unavailable');
        } else {
            updateConnectionStatus(false);
        }

        // Update basic stats display
        const fpsValue = document.getElementById('fps-value');
        const peopleValue = document.getElementById('people-value');
        const repsValue = document.getElementById('reps-value');
        const alertsValue = document.getElementById('alerts-value');
        const durationValue = document.getElementById('duration-value');

        // FPS
        if (fpsValue) {
            const fps = Math.round(stats.fps || 0);
            fpsValue.textContent = fps;
            fpsValue.className = fps > 20 ? 'text-xl font-bold text-green-500' : 'text-xl font-bold text-red-500';
        }

        // People detected
        if (peopleValue) {
            const peopleCount = stats.detected_persons || stats.active_people || 0;
            peopleValue.textContent = peopleCount;
        }

        // Mode-specific stats
        const primaryStatLabel = document.getElementById('primary-stat-label');
        const alertsStat = document.getElementById('alerts-stat');

        if (selectedMode === 'fitness') {
            if (primaryStatLabel) primaryStatLabel.textContent = 'Reps';
            if (alertsStat) alertsStat.classList.add('hidden');

            if (repsValue) {
                const reps = stats.session_reps || 0;
                repsValue.textContent = reps;
                // Add visual feedback for rep changes
                if (reps > (parseInt(repsValue.getAttribute('data-last-reps')) || 0)) {
                    repsValue.classList.add('animate-bounce');
                    setTimeout(() => repsValue.classList.remove('animate-bounce'), 500);
                }
                repsValue.setAttribute('data-last-reps', reps);
            }

            // Update exercise-specific info
            const serviceInfoDiv = document.getElementById('service-info');
            if (serviceInfoDiv && selectedService) {
                const exerciseInfo = getExerciseInfo(selectedService, stats);
                serviceInfoDiv.innerHTML = exerciseInfo;
            }

        } else if (selectedMode === 'surveillance') {
            if (primaryStatLabel) primaryStatLabel.textContent = 'People';
            if (alertsStat) alertsStat.classList.remove('hidden');

            if (alertsValue) {
                const alerts = stats.alerts_count || 0;
                alertsValue.textContent = alerts;
                // Visual feedback for new alerts
                if (alerts > (parseInt(alertsValue.getAttribute('data-last-alerts')) || 0)) {
                    alertsValue.classList.add('animate-pulse');
                    setTimeout(() => alertsValue.classList.remove('animate-pulse'), 1000);
                }
                alertsValue.setAttribute('data-last-alerts', alerts);
            }

            // Update surveillance info
            const serviceInfoDiv = document.getElementById('service-info');
            if (serviceInfoDiv) {
                const surveillanceInfo = getSurveillanceInfo(selectedService, stats);
                serviceInfoDiv.innerHTML = surveillanceInfo;
            }
        }

        // Update session duration
        if (durationValue && sessionStartTime) {
            const now = new Date();
            const duration = Math.floor((now - sessionStartTime) / 1000);
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            durationValue.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }

        // Update connection status and video overlay
        updateConnectionStatus(true);

        const currentModeSpan = document.getElementById('current-mode');
        if (currentModeSpan) {
            const modeText = selectedMode === 'fitness' ? `FITNESS - ${selectedService?.toUpperCase() || 'GENERAL'}` :
                selectedMode === 'surveillance' ? `SURVEILLANCE - ${selectedService?.replace('_', ' ')?.toUpperCase() || 'GENERAL'}` : 'DEMO MODE';
            currentModeSpan.textContent = modeText;
        }

    } catch (error) {
        console.error('Error updating stats:', error);
        updateConnectionStatus(false);
    }
}

// Helper function for exercise-specific info
function getExerciseInfo(exercise, stats) {
    const templates = {
        'squat': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">Squats Completed:</span>
                    <span class="font-semibold text-blue-600">${stats.session_reps || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Form Quality:</span>
                    <span class="font-semibold text-green-600">${stats.form_score_avg || 'N/A'}%</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Keep your back straight and go down until thighs are parallel to floor
                </div>
            </div>
        `,
        'pushup': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">Push-ups Done:</span>
                    <span class="font-semibold text-blue-600">${stats.session_reps || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Avg Depth:</span>
                    <span class="font-semibold text-green-600">${stats.avg_depth || 'N/A'}°</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Keep your body straight and lower chest to ground
                </div>
            </div>
        `,
        'bicep_curl': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">Curls Completed:</span>
                    <span class="font-semibold text-blue-600">${stats.session_reps || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Range of Motion:</span>
                    <span class="font-semibold text-green-600">${stats.range_of_motion || 'Good'}</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Control the movement and squeeze at the top
                </div>
            </div>
        `
    };

    return templates[exercise] || `
        <div class="text-sm text-center text-gray-600">
            <div class="font-semibold">${exercise.replace('_', ' ').toUpperCase()}</div>
            <div>Reps: ${stats.session_reps || 0}</div>
        </div>
    `;
}

// Helper function for surveillance-specific info
function getSurveillanceInfo(service, stats) {
    const templates = {
        'zone_detection': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">Active Tracking:</span>
                    <span class="font-semibold text-blue-600">${stats.detected_persons || 0} people</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Zone Violations:</span>
                    <span class="font-semibold text-red-600">${stats.alert_counts?.restricted_zone_entry || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Restricted Zones:</span>
                    <span class="font-semibold text-yellow-600">${stats.restricted_zones || 0}</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Monitoring restricted areas for unauthorized access
                </div>
            </div>
        `,
        'rapid_movement': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">People Tracked:</span>
                    <span class="font-semibold text-blue-600">${stats.detected_persons || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Movement Alerts:</span>
                    <span class="font-semibold text-red-600">${stats.alert_counts?.rapid_movement || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Total People:</span>
                    <span class="font-semibold text-green-600">${stats.total_people_detected || 0}</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Detecting unusually rapid movements and running
                </div>
            </div>
        `,
        'fall_detection': `
            <div class="text-sm space-y-1">
                <div class="flex justify-between">
                    <span class="text-gray-600">People Monitored:</span>
                    <span class="font-semibold text-blue-600">${stats.detected_persons || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Fall Alerts:</span>
                    <span class="font-semibold text-red-600">${stats.alert_counts?.fall_detected || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">All Alerts:</span>
                    <span class="font-semibold text-yellow-600">${stats.alerts_count || 0}</span>
                </div>
                <div class="text-xs text-gray-500 mt-2">
                    Monitoring for falls and emergency situations
                </div>
            </div>
        `
    };

    return templates[service] || `
        <div class="text-sm space-y-1">
            <div class="flex justify-between">
                <span class="text-gray-600">Active Tracking:</span>
                <span class="font-semibold text-blue-600">${stats.detected_persons || 0} people</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-600">Total Alerts:</span>
                <span class="font-semibold text-red-600">${stats.alerts_count || 0}</span>
            </div>
            <div class="text-xs text-gray-500 mt-2">
                General surveillance monitoring active
            </div>
        </div>
    `;
}

// Enhanced stats management for multi-step UI
function startStatsUpdates() {
    if (statsInterval) clearInterval(statsInterval);
    statsInterval = setInterval(updateStats, 1000);
    updateStats(); // Initial update
}

function stopStatsUpdates() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
}

function resetStats() {
    const elements = ['fps-value', 'people-value', 'reps-value', 'alerts-value', 'duration-value'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = id === 'duration-value' ? '00:00' : '0';
        }
    });
    sessionStartTime = null;
}



async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const logs = await response.json();

        const container = document.getElementById('logs-container');

        if (logs.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm">No logs available</p>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="bg-gray-50 p-3 rounded border-l-4 border-indigo-500">
                <div class="flex justify-between items-center">
                    <span class="font-medium text-sm">${log.filename}</span>
                    <a href="/api/download/${log.filename}" 
                        class="text-indigo-600 hover:text-indigo-800 text-sm">
                        <i class="fas fa-download"></i>
                    </a>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                    ${new Date(log.modified).toLocaleString()} • ${(log.size / 1024).toFixed(1)} KB
                </p>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

function updateConnectionStatus(connected, customMessage = null) {
    isConnected = connected;
    const statusIndicator = document.getElementById('status-indicator');
    if (!statusIndicator) return;

    const indicator = statusIndicator.querySelector('div');
    const text = statusIndicator.querySelector('span');

    if (indicator && text) {
        if (connected) {
            indicator.classList.remove('bg-red-400', 'bg-yellow-400');
            indicator.classList.add('bg-green-400');
            text.textContent = customMessage || 'Online';
        } else {
            indicator.classList.remove('bg-green-400');
            if (customMessage && customMessage.includes('Starting')) {
                indicator.classList.add('bg-yellow-400');
                indicator.classList.remove('bg-red-400');
            } else {
                indicator.classList.add('bg-red-400');
                indicator.classList.remove('bg-yellow-400');
            }
            text.textContent = customMessage || 'Offline';
        }
    }

    // Update session status
    const sessionStatus = document.getElementById('session-status');
    if (sessionStatus) {
        let statusColor = 'bg-red-400';
        let statusText = customMessage || 'Offline';
        
        if (connected) {
            statusColor = 'bg-green-400';
            statusText = customMessage || 'Online';
        } else if (customMessage && customMessage.includes('Starting')) {
            statusColor = 'bg-yellow-400';
            statusText = customMessage;
        }
        
        sessionStatus.innerHTML = `<span class="flex items-center"><div class="w-2 h-2 ${statusColor} rounded-full mr-2 animate-pulse"></div>${statusText}</span>`;
    }
}

function updateSessionInfo() {
    // Update session info panel
    document.getElementById('session-mode').textContent = selectedMode ? selectedMode.charAt(0).toUpperCase() + selectedMode.slice(1) : '-';
    document.getElementById('session-service').textContent = selectedService ? getServiceTitle(selectedService) : '-';
    document.getElementById('session-start').textContent = sessionStartTime ? sessionStartTime.toLocaleTimeString() : '-';
}

function updateStatsDisplay() {
    const container = document.getElementById('stats-container');
    if (!container) return;

    // Create different stats based on mode
    if (selectedMode === 'fitness') {
        container.innerHTML = `
            <div class="gradient-fitness text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">FPS</span>
                    <span id="fps-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">Active People</span>
                    <span id="people-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-green-500 to-green-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">Reps Count</span>
                    <span id="reps-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-purple-500 to-purple-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">Duration</span>
                    <span id="duration-value" class="text-xl font-bold">00:00</span>
                </div>
            </div>
        `;
    } else if (selectedMode === 'surveillance') {
        container.innerHTML = `
            <div class="gradient-surveillance text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">FPS</span>
                    <span id="fps-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">People Detected</span>
                    <span id="people-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-red-500 to-red-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">Active Alerts</span>
                    <span id="alerts-value" class="text-xl font-bold">0</span>
                </div>
            </div>
            <div class="bg-gradient-to-r from-yellow-500 to-yellow-600 text-white p-4 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-sm opacity-90">Duration</span>
                    <span id="duration-value" class="text-xl font-bold">00:00</span>
                </div>
            </div>
        `;
    }
}

function updateDemoControls(isActive) {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');

    if (startBtn && stopBtn) {
        startBtn.disabled = isActive;
        stopBtn.disabled = !isActive;

        if (isActive) {
            startBtn.classList.add('opacity-50', 'cursor-not-allowed');
            startBtn.classList.remove('hover:bg-green-600');
            stopBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            stopBtn.classList.add('hover:bg-red-600');
        } else {
            startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            startBtn.classList.add('hover:bg-green-600');
            stopBtn.classList.add('opacity-50', 'cursor-not-allowed');
            stopBtn.classList.remove('hover:bg-red-600');
        }
    }
}