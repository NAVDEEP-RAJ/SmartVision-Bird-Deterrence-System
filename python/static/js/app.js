/**
 * SmartVision Bird Deterrence Interface Engine
 * Controls background polling, telemetry rendering, and API commands.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const systemPulse = document.getElementById("system-pulse");
    const systemStatusText = document.getElementById("system-status-text");
    const videoSourceBadge = document.getElementById("video-source-badge");
    const alarmBanner = document.getElementById("alarm-banner");
    const fpsCounter = document.getElementById("fps-counter");
    
    // Stats elements
    const sightingStat = document.getElementById("sighting-stat");
    const triggerStat = document.getElementById("trigger-stat");
    const uptimeStat = document.getElementById("uptime-stat");
    
    // Hardware elements
    const hwStatusBadge = document.getElementById("hw-status-badge");
    const hardwarePort = document.getElementById("hardware-port");
    const laserStatus = document.getElementById("laser-status");
    const scanningMode = document.getElementById("scanning-mode");
    
    // Console log elements
    const consoleOutput = document.getElementById("console-output");
    
    // Action buttons
    const btnManualTrigger = document.getElementById("btn-manual-trigger");
    const btnManualClear = document.getElementById("btn-manual-clear");

    // Keep track of logged messages to prevent duplicates representation
    const printedLogs = new Set();
    let currentAlarmActive = false;

    // Helper: Print a clean log entry to the UI Terminal
    function addConsoleLog(message, type = "default") {
        if (printedLogs.has(message)) return;
        
        // Cap the set size to manage memory
        if (printedLogs.size > 200) {
            printedLogs.clear();
        }
        printedLogs.add(message);

        const logLine = document.createElement("div");
        logLine.className = `log-line ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        logLine.textContent = `[${timestamp}] ${message}`;
        
        consoleOutput.appendChild(logLine);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    // API Post: Send controls to the Flask Backend
    async function sendControlAction(action) {
        try {
            addConsoleLog(`Transmitting manual command override: ${action}`, "system");
            const response = await fetch("/api/control", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ action: action })
            });

            const result = await response.json();
            if (result.success) {
                addConsoleLog(`Override success: '${action}' accepted by controller.`, "command");
            } else {
                addConsoleLog(`Override rejected: ${result.error || 'Server rejected request'}`, "alarm");
            }
        } catch (error) {
            addConsoleLog(`Communication error sending command: ${error}`, "alarm");
        }
    }

    // Event listeners
    btnManualTrigger.addEventListener("click", () => sendControlAction("BIRD"));
    btnManualClear.addEventListener("click", () => sendControlAction("CLEAR"));

    // Main Polling Loop: Fetches metrics periodically
    async function updateTelemetry() {
        try {
            const response = await fetch("/api/status");
            if (!response.ok) {
                throw new Error(`HTTP index ${response.status}`);
            }
            
            const data = await response.json();

            // 1. Alarm UI states
            if (data.active_sighted) {
                if (!currentAlarmActive) {
                    currentAlarmActive = true;
                    alarmBanner.classList.add("active");
                    systemPulse.classList.add("alert-active");
                    addConsoleLog("TARGET DETECTED - Triggering active deterrence commands...", "alarm");
                }
            } else {
                if (currentAlarmActive) {
                    currentAlarmActive = false;
                    alarmBanner.classList.remove("active");
                    systemPulse.classList.remove("alert-active");
                    addConsoleLog("Target cleared. Restoring standby operations.", "system");
                }
            }

            // 2. Refresh Counter Labels
            sightingStat.textContent = data.active_sighted ? "1" : "0";
            triggerStat.textContent = data.total_detections || "0";
            uptimeStat.textContent = data.uptime || "00:00:00";
            fpsCounter.textContent = `Frame Rate: ${data.fps || '--'} FPS`;
            
            // 3. Update Camera source label
            const camDriver = data.camera.driver;
            if (camDriver === "rpicam") {
                videoSourceBadge.textContent = "RPi Camera (Raw YUV)";
                videoSourceBadge.style.color = "var(--success)";
            } else if (camDriver === "opencv") {
                videoSourceBadge.textContent = "USB/Webcam (OpenCV)";
                videoSourceBadge.style.color = "#38bdf8";
            } else {
                videoSourceBadge.textContent = "No Camera Input";
                videoSourceBadge.style.color = "var(--danger)";
            }

            // 4. Update Hardware Bridge Diagnostics
            const hw = data.hardware;
            hardwarePort.textContent = hw.port || "/dev/ttyUSB0";
            
            if (hw.connected) {
                hwStatusBadge.textContent = "Arduino Connected";
                hwStatusBadge.setAttribute("data-status", "connected");
            } else if (hw.simulated) {
                hwStatusBadge.textContent = "Hardware Simulated";
                hwStatusBadge.setAttribute("data-status", "simulated");
            } else {
                hwStatusBadge.textContent = "Disconnected";
                hwStatusBadge.setAttribute("data-status", "disconnected");
            }

            // 5. Update Laser Status Output
            if (data.laser_status === "ACTIVE") {
                laserStatus.textContent = "EMITTING (HIGH)";
                laserStatus.className = "info-value text-red";
                scanningMode.textContent = "LOCKED / TARGET HOLDBACK";
            } else {
                laserStatus.textContent = "DEACTIVATED";
                laserStatus.className = "info-value text-green";
                scanningMode.textContent = "DYNAMIC ACTIVE SCAN";
            }

            // 6. Print new telemetry event logs
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => {
                    let logType = "default";
                    if (log.includes("[ALARM]") || log.includes("YOLO")) logType = "alarm";
                    else if (log.includes("[HARDWARE]") || log.includes("Arduino")) logType = "command";
                    else if (log.includes("[SYSTEM]")) logType = "system";

                    addConsoleLog(log, logType);
                });
            }

        } catch (error) {
            console.error("Failed to parse status payload:", error);
            hwStatusBadge.textContent = "Network Down";
            hwStatusBadge.setAttribute("data-status", "disconnected");
            addConsoleLog("Server connection interrupted. Polling backup feeds...", "alarm");
        }
    }

    // Set interactive updates on interval
    setInterval(updateTelemetry, 1000);
    updateTelemetry(); // Immediate boot-up call
});
