document.addEventListener("DOMContentLoaded", function() {
  // Enhanced status management with better visual feedback
  function setStatus(message, type = 'info') {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    
    // Remove existing classes
    statusDiv.className = 'status-indicator';
    
    // Add appropriate class based on type
    switch(type) {
      case 'success':
        statusDiv.classList.add('connected');
        break;
      case 'error':
        statusDiv.classList.add('error');
        break;
      case 'warning':
        statusDiv.classList.add('connecting');
        break;
      default:
        statusDiv.classList.add('connecting');
    }
    
    // Add fade-in animation
    statusDiv.classList.add('fade-in');
    setTimeout(() => statusDiv.classList.remove('fade-in'), 500);
  }

  // Enhanced loading state management
  function setLoading(element, isLoading = true) {
    if (isLoading) {
      element.classList.add('loading');
      element.disabled = true;
    } else {
      element.classList.remove('loading');
      element.disabled = false;
    }
  }

  // Enhanced notification system
  function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm fade-in`;
    
    switch(type) {
      case 'success':
        notification.classList.add('bg-green-100', 'text-green-800', 'border', 'border-green-200');
        break;
      case 'error':
        notification.classList.add('bg-red-100', 'text-red-800', 'border', 'border-red-200');
        break;
      case 'warning':
        notification.classList.add('bg-yellow-100', 'text-yellow-800', 'border', 'border-yellow-200');
        break;
      default:
        notification.classList.add('bg-blue-100', 'text-blue-800', 'border', 'border-blue-200');
    }
    
    notification.innerHTML = `
      <div class="flex items-center justify-between">
        <span>${message}</span>
        <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-lg">&times;</button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after duration
    setTimeout(() => {
      if (notification.parentElement) {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
      }
    }, duration);
  }
  
  // Enhanced fetch with better error handling
  async function fetchJSON(url, options = {}) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Fetch error:', error);
      throw error;
    }
  }

  // Enhanced error handling wrapper
  async function handleAsyncOperation(operation, loadingElement = null, successMessage = null) {
    try {
      if (loadingElement) setLoading(loadingElement, true);
      const result = await operation();
      if (successMessage) showNotification(successMessage, 'success');
      return result;
    } catch (error) {
      console.error('Operation failed:', error);
      showNotification(error.message || 'An error occurred', 'error');
      throw error;
    } finally {
      if (loadingElement) setLoading(loadingElement, false);
    }
  }
  
  
  const dashboardSection = document.getElementById('dashboardSection');
  const connectBtn = document.getElementById('connectBtn');
  const disconnectBtn = document.getElementById('disconnectBtn');
  const ipAddressInput = document.getElementById('ipAddress');
  const portInput = document.getElementById('port');
  
  // Check for saved connection state on page load
  function checkSavedConnection() {
    const savedConnection = localStorage.getItem('arcadeConnection');
    if (savedConnection) {
      try {
        const connectionData = JSON.parse(savedConnection);
        ipAddressInput.value = connectionData.ip || '100.72.14.16';
        portInput.value = connectionData.port || '5034';
        
        // Auto-connect if we have saved connection data
        if (connectionData.autoConnect !== false) {
          setStatus("Auto-connecting...", "info");
          setTimeout(() => {
            connectBtn.click();
          }, 500); // Small delay to ensure page is fully loaded
        }
      } catch (e) {
        console.error('Error parsing saved connection data:', e);
        localStorage.removeItem('arcadeConnection');
      }
    }
  }
  
  // Save connection state
  function saveConnectionState(ip, port, isConnected = false) {
    const connectionData = {
      ip: ip,
      port: port,
      isConnected: isConnected,
      autoConnect: true,
      timestamp: Date.now()
    };
    localStorage.setItem('arcadeConnection', JSON.stringify(connectionData));
  }
  
  // Clear connection state
  function clearConnectionState() {
    localStorage.removeItem('arcadeConnection');
  }
  
  const liveTab = document.getElementById('liveTab');
  const replayTab = document.getElementById('replayTab');
  const analysisTab = document.getElementById('analysisTab');
  const renderPositionsTab = document.getElementById('renderPositionsTab');
  const uploadModelTab = document.getElementById('uploadModelTab');
  const datasetTab = document.getElementById('datasetTab');
  const pointTab = document.getElementById('pointTab');
  const liveContent = document.getElementById('liveContent');
  const replayContent = document.getElementById('replayContent');
  const analysisContent = document.getElementById('analysisContent');
  const renderPositionsContent = document.getElementById('renderPositionsContent');
  const uploadModelContent = document.getElementById('uploadModelContent');
  const datasetContent = document.getElementById('datasetContent');
  const pointCloudContent = document.getElementById('pointCloudContent');
  // sessionIdInput removed - using globalSessionSelect instead
  const loadReplayBtn = document.getElementById('loadReplayBtn');
  const refreshGlobalSessionsBtn = document.getElementById('refreshGlobalSessionsBtn');
  const globalSessionSelect = document.getElementById('globalSessionSelect');
  const globalFrameInput = document.getElementById('globalFrameInput');
  const refreshMeshesBtn = document.getElementById('refreshMeshesBtn');
  const meshList = document.getElementById('meshList');
  const uploadMeshBtn = document.getElementById('uploadMeshBtn');
  const meshFileInput = document.getElementById('meshFile');
  const liveStream = document.getElementById('liveStream');
  const replayGrid = document.getElementById('replayGrid');
  // refreshFramesBtn removed - element doesn't exist in HTML
  // frameList and analysisSessionId removed - using global selectors instead
  const frameDetails = document.getElementById('frameDetails');
  const renderPositionsBtn = document.getElementById('renderPositionsBtn');
  const renderPositionsGrid = document.getElementById('renderPositionsGrid');
  // frameNumberInput removed - using globalFrameInput only
  const loadFrameBtn = document.getElementById('loadFrameBtn');
  const frameRangeInfo = document.getElementById('frameRangeInfo');
  const frameRangeDetails = document.getElementById('frameRangeDetails');
  const frameCount = document.getElementById('frameCount');
  const sessionName = document.getElementById('sessionName');
  const modelList = document.getElementById('modelList');
  const modelCount = document.getElementById('modelCount');
  const applyModelsBtn = document.getElementById('applyModelsBtn');
  const uploadModelBtn = document.getElementById('uploadModelBtn');
  const inferenceModelFile = document.getElementById('inferenceModelFile');
  const replayInfo = document.getElementById('replayInfo');
  const datasetFrameIdInput = document.getElementById('datasetFrameId');
  const loadDatasetFrameBtn = document.getElementById('loadDatasetFrameBtn');
  const maxFrameIdSpan = document.getElementById('maxFrameId');
  const datasetFrameInfoLine = document.getElementById('datasetFrameInfoLine');
  const datasetCompositeImage = document.getElementById('datasetCompositeImage');
  const datasetOriginalRGB = document.getElementById('datasetOriginalRGB');
  const datasetGTDepth = document.getElementById('datasetGTDepth');
  const inferenceResultsGrid = document.getElementById('inferenceResultsGrid');
  const inferenceMetricsTableBody = document.getElementById('inferenceMetricsTableBody');
  const datasetInferredResults = document.getElementById('inferenceMetricsTableBody'); // we use the table for metrics
  
  // Point cloud elements
  const pointCloudSession = document.getElementById('pointCloudSession');
  const pointCloudFrame = document.getElementById('pointCloudFrame');
  const generatePointCloudBtn = document.getElementById('generatePointCloudBtn');
  const downloadPointCloudBtn = document.getElementById('downloadPointCloudBtn');
  const pointCloudInfo = document.getElementById('pointCloudInfo');
  const pointCloudDownload = document.getElementById('pointCloudDownload');
  const pointCloudPreview = document.getElementById('pointCloudPreview');
  const pointCloudList = document.getElementById('pointCloudList');
  const pointCloudItems = document.getElementById('pointCloudItems');
  
  // Virtual settings elements
  const virtualDepthInput = document.getElementById('virtualDepthInput');
  const virtualModeSelect = document.getElementById('virtualModeSelect');
  const virtualPosXInput = document.getElementById('virtualPosX');
  const virtualPosYInput = document.getElementById('virtualPosY');
  const virtualPosZInput = document.getElementById('virtualPosZ');
  const loadDefaultPositionBtn = document.getElementById('loadDefaultPositionBtn');
  const objectPositionSection = document.getElementById('objectPositionSection');
  const virtualDepthSection = document.getElementById('virtualDepthSection');
  const loadDefaultPositionSection = document.getElementById('loadDefaultPositionSection');
  
  // Function to toggle visibility based on mode
  function updateVirtualModeVisibility() {
    if (!virtualModeSelect) {
      console.warn('virtualModeSelect not found');
      return;
    }
    
    const mode = virtualModeSelect.value;
    console.log('Updating virtual mode visibility, mode:', mode);
    console.log('Elements found:', {
      objectPositionSection: !!objectPositionSection,
      virtualDepthSection: !!virtualDepthSection,
      loadDefaultPositionSection: !!loadDefaultPositionSection
    });
    
    if (mode === 'object') {
      // Show Object mode sections
      if (objectPositionSection) {
        objectPositionSection.classList.remove('hidden');
        console.log('Showing object position section');
      } else {
        console.warn('objectPositionSection not found');
      }
      if (loadDefaultPositionSection) {
        loadDefaultPositionSection.classList.remove('hidden');
        console.log('Showing load default position section');
      } else {
        console.warn('loadDefaultPositionSection not found');
      }
      // Hide Plane mode sections
      if (virtualDepthSection) {
        virtualDepthSection.classList.add('hidden');
        console.log('Hiding virtual depth section');
      } else {
        console.warn('virtualDepthSection not found');
      }
    } else if (mode === 'plane') {
      // Show Plane mode sections
      if (virtualDepthSection) {
        virtualDepthSection.classList.remove('hidden');
        console.log('Showing virtual depth section');
      } else {
        console.warn('virtualDepthSection not found');
      }
      // Hide Object mode sections
      if (objectPositionSection) {
        objectPositionSection.classList.add('hidden');
        console.log('Hiding object position section');
      } else {
        console.warn('objectPositionSection not found');
      }
      if (loadDefaultPositionSection) {
        loadDefaultPositionSection.classList.add('hidden');
        console.log('Hiding load default position section');
      } else {
        console.warn('loadDefaultPositionSection not found');
      }
    }
  }
  
  // Initialize mode visibility on page load
  if (virtualModeSelect) {
    // Use requestAnimationFrame to ensure DOM is fully ready
    requestAnimationFrame(() => {
      // Set initial visibility based on default selected mode
      updateVirtualModeVisibility();
      // Also send initial settings to server if connected
      updateVirtualSettings();
    });
    
    virtualModeSelect.addEventListener('change', () => {
      updateVirtualModeVisibility();
      // Send updated settings to server when mode changes
      updateVirtualSettings();
    });
  } else {
    console.warn('virtualModeSelect element not found during initialization');
  }
  
  if (virtualDepthInput) {
    virtualDepthInput.addEventListener('input', updateVirtualSettings);
  }
  if (virtualPosXInput) {
    virtualPosXInput.addEventListener('input', updateVirtualSettings);
  }
  if (virtualPosYInput) {
    virtualPosYInput.addEventListener('input', updateVirtualSettings);
  }
  if (virtualPosZInput) {
    virtualPosZInput.addEventListener('input', updateVirtualSettings);
  }
  if (loadDefaultPositionBtn) {
    loadDefaultPositionBtn.addEventListener('click', loadDefaultPosition);
  }
  
  let ws, currentSession = "", currentMode = "live", numInferenceModelsApplied = 0;
  let replayVideoElements = {};
  let selectedModels = new Set();
  
  async function resetToMesh() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    try {
      const data = await fetchJSON(`http://${ip}:${port}/select_mesh`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ mesh: "teapot.obj" })
      });
      console.log("Reset to mesh:", data);
    } catch (err) {
      console.error("Error resetting to mesh:", err);
      alert("Error resetting to mesh. Ensure that 'teapot.obj' exists in the 3D_models folder.");
    }
  }
  
  async function getMeshSettings() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    // Only fetch settings if we have connection details
    if (!ip || !port) {
      console.log("No connection details available, skipping mesh settings fetch");
      return;
    }
    
    try {
      const data = await fetchJSON(`http://${ip}:${port}/mesh_settings`);
      if (data && data.object_position) {
        const pos = data.object_position;
        if (virtualPosXInput) virtualPosXInput.value = pos[0] || 0;
        if (virtualPosYInput) virtualPosYInput.value = pos[1] || 0;
        if (virtualPosZInput) virtualPosZInput.value = pos[2] || 0;
        console.log("Fetched mesh settings:", pos);
      }
    } catch (err) {
      console.error("Error fetching mesh settings:", err);
      // Don't show error notification for this as it's not critical
    }
  }
  
  async function updateVirtualSettings() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    // Only update if we have connection details
    if (!ip || !port) {
      console.log("No connection details available, skipping virtual settings update");
      return;
    }
    
    const mode = virtualModeSelect ? virtualModeSelect.value : 'plane';
    let payload = {};
    
    if (mode === 'plane') {
      // Plane mode: send virtual_object as "virtual_plane" and virtual depth
      payload.virtual_object = "virtual_plane";
      let depthVal = virtualDepthInput && virtualDepthInput.value ? virtualDepthInput.value.trim() : '';
      if(depthVal !== ""){
        let parsed = parseFloat(depthVal);
        if(isNaN(parsed) || !isFinite(parsed)){
          console.error("Invalid virtual depth value.");
          return;
        }
        payload.virtual_depth = parsed;
      } else {
        payload.virtual_depth = null;
      }
    } else {
      // Object mode: only send position
      const posX = virtualPosXInput && virtualPosXInput.value ? virtualPosXInput.value.trim() : '';
      const posY = virtualPosYInput && virtualPosYInput.value ? virtualPosYInput.value.trim() : '';
      const posZ = virtualPosZInput && virtualPosZInput.value ? virtualPosZInput.value.trim() : '';
      
      // Only include position if all three values are provided
      if (posX !== "" && posY !== "" && posZ !== "") {
        const x = parseFloat(posX);
        const y = parseFloat(posY);
        const z = parseFloat(posZ);
        if(isNaN(x) || isNaN(y) || isNaN(z)) {
          console.error("Invalid virtual position values.");
          return;
        }
        payload.virtual_position = { x, y, z };
      }
    }
    
    try {
      const data = await fetchJSON(`http://${ip}:${port}/update_virtual_settings`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      console.log("Virtual settings updated:", data);
    } catch(err) {
      console.error("Error updating virtual settings:", err);
      // Don't show error notification for this as it's not critical for user experience
    }
  }

  async function loadDefaultPosition() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    // Only load if we have connection details
    if (!ip || !port) {
      showNotification("Please connect to server first.", "error");
      return;
    }
    
    try {
      console.log("Loading default position...");
      
      // Get the current session if one is selected
      const currentSession = globalSessionSelect ? globalSessionSelect.value.trim() : '';
      
      // Build URL with session parameter and force_from_metadata flag
      let settingsUrl = `http://${ip}:${port}/mesh_settings?force_from_metadata=true`;
      if (currentSession) {
        settingsUrl += `&session=${encodeURIComponent(currentSession)}`;
      }
      
      // Fetch the mesh settings (will use session metadata if session is provided)
      const settingsData = await fetchJSON(settingsUrl);
      console.log("Fetched mesh settings:", settingsData);
      console.log("Settings data keys:", Object.keys(settingsData || {}));
      
      if (settingsData && settingsData.object_position) {
        const pos = settingsData.object_position;
        console.log("Setting position values:", pos);
        
        // Update the input fields
        if (virtualPosXInput) {
          virtualPosXInput.value = pos[0] || 0;
          console.log("Set X to:", virtualPosXInput.value);
        } else {
          console.warn("virtualPosXInput not found");
        }
        if (virtualPosYInput) {
          virtualPosYInput.value = pos[1] || 0;
          console.log("Set Y to:", virtualPosYInput.value);
        } else {
          console.warn("virtualPosYInput not found");
        }
        if (virtualPosZInput) {
          virtualPosZInput.value = pos[2] || 0;
          console.log("Set Z to:", virtualPosZInput.value);
        } else {
          console.warn("virtualPosZInput not found");
        }
        
        // Send the updated position to the server
        await updateVirtualSettings();
        
        const sessionInfo = currentSession ? ` from session "${currentSession}"` : '';
        showNotification(`Default position loaded successfully${sessionInfo}!`, "success");
      } else {
        showNotification("Could not load default position values. No metadata found.", "warning");
      }
      
    } catch(err) {
      console.error("Error loading default position:", err);
      showNotification("Error loading default position: " + err.message, "error");
    }
  }
  
  // Initialize mesh settings on page load
  getMeshSettings();
  
  // Initialize mesh list on page load if connected
  if (ipAddressInput.value.trim() && portInput.value.trim()) {
    refreshMeshList();
  }
  
  function hideAllContent() {
    if (liveContent) liveContent.classList.add("hidden");
    if (replayContent) replayContent.classList.add("hidden");
    if (analysisContent) analysisContent.classList.add("hidden");
    if (renderPositionsContent) renderPositionsContent.classList.add("hidden");
    if (uploadModelContent) uploadModelContent.classList.add("hidden");
    if (datasetContent) datasetContent.classList.add("hidden");
    if (pointCloudContent) pointCloudContent.classList.add("hidden");
  }
  
  function switchTab(activeTab) {
    [liveTab, replayTab, analysisTab, renderPositionsTab, uploadModelTab, datasetTab, pointTab].forEach(tab => {
      if (tab) {
        tab.classList.remove("border-purple-600", "text-purple-600");
      }
    });
    if (activeTab) {
      activeTab.classList.add("border-purple-600", "text-purple-600");
    }
  }
  
  connectBtn.addEventListener("click", async () => {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    if (!ip || !port) {
      setStatus("Please enter both IP and port.", "error");
      showNotification("Please enter both IP and port.", "error");
      return;
    }
    
    // Save connection details
    saveConnectionState(ip, port, false);
    
    const wsUrl = `ws://${ip}:${port}/live`;
    await handleAsyncOperation(
      () => establishConnection(wsUrl),
      connectBtn,
      "Connected successfully!"
    );
  });
  
  // Handle disconnect button (both in connection section and status bar)
  document.querySelectorAll('#disconnectBtn').forEach(btn => {
    btn.addEventListener("click", () => {
      // Close WebSocket connection if it exists
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close();
      }
      
      // Clear saved connection state
      clearConnectionState();
      
      // Show connection section and hide dashboard
      connectionSection.classList.remove("hidden");
      dashboardSection.classList.add("hidden");
      
      // Reset status
      setStatus("Disconnected", "info");
      showNotification("Disconnected successfully", "info");
    });
  });
  
  if (liveTab) {
    liveTab.addEventListener("click", () => {
      currentMode = "live";
      switchTab(liveTab);
      hideAllContent();
      if (liveContent) {
        liveContent.classList.remove("hidden");
      }
      reconnectToLive();
    });
  }
  
  if (replayTab) {
    replayTab.addEventListener("click", () => {
      currentMode = "replay";
      switchTab(replayTab);
      hideAllContent();
      if (replayContent) {
        replayContent.classList.remove("hidden");
      }
      if (replayInfo) {
        replayInfo.textContent = numInferenceModelsApplied > 0 ?
          `Replay will display: Original + ${numInferenceModelsApplied} inference outputs.` :
          "Replay will display only original output.";
      }
      if (replayGrid) {
        replayGrid.innerHTML = "";
      }
      replayVideoElements = {};
    });
  }
  
  if (analysisTab) {
    analysisTab.addEventListener("click", () => {
      currentMode = "analysis";
      switchTab(analysisTab);
      hideAllContent();
      if (analysisContent) {
        analysisContent.classList.remove("hidden");
      }
    });
  }
  
  if (renderPositionsTab) {
    renderPositionsTab.addEventListener("click", () => {
      currentMode = "renderPositions";
      switchTab(renderPositionsTab);
      hideAllContent();
      if (renderPositionsContent) {
        renderPositionsContent.classList.remove("hidden");
      }
    });
  }
  
  if (uploadModelTab) {
    uploadModelTab.addEventListener("click", () => {
      currentMode = "uploadModel";
      switchTab(uploadModelTab);
      hideAllContent();
      if (uploadModelContent) {
        uploadModelContent.classList.remove("hidden");
      }
    });
  }
  
  if (pointTab) {
    pointTab.addEventListener("click", () => {
      currentMode = "pointCloud";
      switchTab(pointTab);
      hideAllContent();
      if (pointCloudContent) {
        pointCloudContent.classList.remove("hidden");
      }
    });
  }
  
  // Global session loading function
  async function loadGlobalSessions() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    if (!ip || !port) {
      showNotification("Enter IP and port to refresh sessions.", "error");
      return;
    }
    
    // Preserve the currently selected session
    const currentSelectedSession = globalSessionSelect ? globalSessionSelect.value : '';
    
    try {
      const data = await fetchJSON(`http://${ip}:${port}/list_sessions`);
      
      // Update global session selector
      globalSessionSelect.innerHTML = '<option value="">Choose a session...</option>';
      
      if (data.sessions && data.sessions.length > 0) {
        // Function to extract date from session name
        // Expected format: session_YYYYMMDD_HHMMSS or similar patterns
        function parseSessionDate(sessionName) {
          // Try to match patterns like: session_20250923_170311 or session_2025-09-23_17-03-11
          const dateMatch = sessionName.match(/(\d{4})(\d{2})(\d{2})[_\-](\d{2})(\d{2})(\d{2})/);
          if (dateMatch) {
            const [, year, month, day, hour, minute, second] = dateMatch;
            return new Date(year, month - 1, day, hour, minute, second);
          }
          // Try to match patterns like: session_2025-09-23 or 20250923
          const dateMatch2 = sessionName.match(/(\d{4})[\-_]?(\d{2})[\-_]?(\d{2})/);
          if (dateMatch2) {
            const [, year, month, day] = dateMatch2;
            return new Date(year, month - 1, day);
          }
          // Fallback: return a very old date so sessions without dates go to the end
          return new Date(0);
        }
        
        // Sort sessions by date (newest first)
        const sortedSessions = [...data.sessions].sort((a, b) => {
          const dateA = parseSessionDate(a);
          const dateB = parseSessionDate(b);
          return dateB - dateA; // Newest first (descending order)
        });
        
        // Add sorted sessions to the dropdown
        sortedSessions.forEach((session) => {
          const option = document.createElement("option");
          option.value = session;
          option.textContent = session;
          globalSessionSelect.appendChild(option);
        });
        
        // Restore the previously selected session if it still exists in the list
        if (currentSelectedSession && data.sessions.includes(currentSelectedSession)) {
          globalSessionSelect.value = currentSelectedSession;
          currentSession = currentSelectedSession;
        }
      }
      
      
      showNotification(`Found ${data.sessions?.length || 0} sessions`, 'success');
    } catch (error) {
      console.error('Error fetching sessions:', error);
      showNotification(error.message || 'An error occurred while fetching sessions', 'error');
    }
  }

  // Event listeners for session loading
  if (refreshGlobalSessionsBtn) {
    refreshGlobalSessionsBtn.addEventListener("click", loadGlobalSessions);
  }

  // Global session selector change handler
  if (globalSessionSelect) {
    globalSessionSelect.addEventListener("change", (e) => {
      const selectedSession = e.target.value;
      if (selectedSession) {
        currentSession = selectedSession;
        showNotification(`Selected session: ${selectedSession}`, 'success', 2000);
      }
    });
  }

  // Global frame input change handler
  if (globalFrameInput) {
    globalFrameInput.addEventListener("input", (e) => {
      const frameValue = e.target.value;
      // No need to sync with removed frameNumberInput
    });
  }

  if (datasetTab) {
    datasetTab.addEventListener("click", async () => {
      currentMode = "dataset";
      switchTab(datasetTab);
      hideAllContent();
      if (datasetContent) {
        datasetContent.classList.remove("hidden");
      }
      const ip = ipAddressInput.value.trim();
      const port = portInput.value.trim();
      try {
        const info = await fetchJSON(`http://${ip}:${port}/dataset_info`);
        if (maxFrameIdSpan) {
          maxFrameIdSpan.textContent = info.num_frames;
        }
      } catch (err) {
        console.error("Error fetching dataset info:", err);
      }
    });
  }
  
  if (loadReplayBtn) {
    loadReplayBtn.addEventListener("click", () => {
      const ip = ipAddressInput.value.trim();
      const port = portInput.value.trim();
      const session = globalSessionSelect.value.trim();
      if (!ip || !port || !session) {
        setStatus("Please enter IP, port, and select a session", "error");
        showNotification("Please select a session from the global session selector above", "error");
        return;
      }
      currentSession = session;
      const wsUrl = `ws://${ip}:${port}/replay?session=${encodeURIComponent(session)}`;
      establishConnection(wsUrl);
    });
  }
  
  loadDatasetFrameBtn.addEventListener("click", async () => {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    const frameId = datasetFrameIdInput.value;
    const planeDepth = virtualDepthInput.value.trim();
    
    if (!frameId) {
      showNotification("Please enter a frame id.", "error");
      return;
    }
    
    await handleAsyncOperation(async () => {
      let url = `http://${ip}:${port}/dataset_frame?frame=${frameId}`;
      if (planeDepth !== "") {
        url += `&virtual_depth=${planeDepth}`;
      }
      
      const data = await fetchJSON(url);
      
      // Update base images with fade-in effect
      if(data.original_rgb) {
        datasetOriginalRGB.src = "data:image/png;base64," + data.original_rgb;
        datasetOriginalRGB.classList.add('fade-in');
      }
      datasetCompositeImage.src = "data:image/png;base64," + data.composite;
      datasetCompositeImage.classList.add('fade-in');
      datasetGTDepth.src = "data:image/png;base64," + data.gt_depth_colormap;
      datasetGTDepth.classList.add('fade-in');
      
      // Update info line with enhanced styling
      datasetFrameInfoLine.innerHTML = `
        <div class="bg-blue-50 p-3 rounded-lg border border-blue-200">
          <strong>Resolution:</strong> ${data.resolution[0]}x${data.resolution[1]} 
          | <strong>Depth Range:</strong> ${data.min_depth.toFixed(2)} - ${data.max_depth.toFixed(2)}
        </div>
      `;
      datasetFrameInfoLine.classList.add('fade-in');
      
      // Build inferred results grid with enhanced styling
      inferenceResultsGrid.innerHTML = "";
      inferenceMetricsTableBody.innerHTML = "";
      
      if(data.inferred_composites && Object.keys(data.inferred_composites).length > 0) {
        for(const model in data.inferred_composites) {
          // Create a card for inferred images with enhanced styling
          let card = document.createElement("div");
          card.className = "card p-4 mb-4 fade-in";
          card.innerHTML = `
            <h4 class="text-lg font-semibold text-gray-700 mb-3 flex items-center">
              <span class="w-3 h-3 bg-purple-500 rounded-full mr-2"></span>
              ${model}
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div class="image-container">
                <p class="text-sm font-medium text-gray-600 mb-2">Composite</p>
                <img src="data:image/png;base64,${data.inferred_composites[model]}" 
                     class="w-full rounded-lg border shadow-sm" 
                     alt="Composite for ${model}"
                     loading="lazy">
              </div>
              <div class="image-container">
                <p class="text-sm font-medium text-gray-600 mb-2">Depth Map</p>
                <img src="data:image/png;base64,${data.inferred_depth_colormaps[model]}" 
                     class="w-full rounded-lg border shadow-sm" 
                     alt="Depth for ${model}"
                     loading="lazy">
              </div>
            </div>
          `;
          inferenceResultsGrid.appendChild(card);
          
          // Append error metrics row to the metrics table with enhanced styling
          let tr = document.createElement("tr");
          tr.className = "fade-in";
          tr.innerHTML = `
            <td class="px-3 py-2 text-sm font-medium text-gray-900">${model}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].RMSE ? data.depth_errors[model].RMSE.toFixed(3) : "N/A"}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].MSE ? data.depth_errors[model].MSE.toFixed(3) : "N/A"}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].AbsRel ? data.depth_errors[model].AbsRel.toFixed(3) : "N/A"}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].A1 ? (data.depth_errors[model].A1 * 100).toFixed(1) + '%' : "N/A"}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].A2 ? (data.depth_errors[model].A2 * 100).toFixed(1) + '%' : "N/A"}</td>
            <td class="px-3 py-2 text-sm text-gray-700">${data.depth_errors[model].A3 ? (data.depth_errors[model].A3 * 100).toFixed(1) + '%' : "N/A"}</td>
          `;
          inferenceMetricsTableBody.appendChild(tr);
        }
      } else {
        // Show message when no inference results
        inferenceResultsGrid.innerHTML = `
          <div class="text-center py-8 text-gray-500">
            <p class="text-lg">No inference models applied</p>
            <p class="text-sm">Apply inference models to see results here</p>
          </div>
        `;
      }
      
      return data;
    }, loadDatasetFrameBtn, `Dataset frame ${frameId} loaded successfully!`);
  });
  
  async function refreshMeshList() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    if (!ip || !port) {
      showNotification("Enter IP and port to refresh meshes.", "error");
      return;
    }
    
    try {
      const data = await fetchJSON(`http://${ip}:${port}/list_meshes`);
      meshList.innerHTML = "";
      
      if (data.meshes && data.meshes.length > 0) {
        const template = document.getElementById("meshItemTemplate");
        data.meshes.forEach((mesh, index) => {
          const clone = template.content.cloneNode(true);
          const li = clone.querySelector("li");
          li.textContent = mesh;
          li.classList.add("slide-in");
          li.style.animationDelay = `${index * 0.1}s`;
          li.addEventListener("click", () => {
            console.log("Mesh clicked:", mesh);
            // Remove previous selection
            document.querySelectorAll('#meshList .selected').forEach(el => el.classList.remove('selected'));
            // Add selection to clicked item
            li.classList.add('selected');
            selectMesh(mesh);
          });
          meshList.appendChild(clone);
        });
      } else {
        meshList.innerHTML = `
          <li class="list-item text-center text-gray-500 py-4">
            <p>No meshes available</p>
            <p class="text-sm">Upload .obj files to get started</p>
          </li>
        `;
      }
      
      showNotification(`Found ${data.meshes?.length || 0} meshes`, 'success');
    } catch (error) {
      console.error('Error fetching meshes:', error);
      showNotification(error.message || 'An error occurred while fetching meshes', 'error');
    }
  }
  refreshMeshesBtn.addEventListener("click", refreshMeshList);
  
  async function selectMesh(meshName) {
    console.log("selectMesh called with:", meshName);
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    if (!ip || !port) {
      console.error("No connection details available for mesh selection");
      showNotification("Please connect to server first.", "error");
      return;
    }
    
    await handleAsyncOperation(async () => {
      console.log("Sending mesh selection request:", { mesh: meshName });
      const data = await fetchJSON(`http://${ip}:${port}/select_mesh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mesh: meshName })
      });
      
      console.log("Mesh selection response:", data);
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // After successful mesh selection, fetch and display the default position values
      try {
        const settingsData = await fetchJSON(`http://${ip}:${port}/mesh_settings`);
        console.log("Fetched mesh settings after selection:", settingsData);
        
        if (settingsData && settingsData.object_position) {
          const pos = settingsData.object_position;
          virtualPosXInput.value = pos[0] || 0;
          virtualPosYInput.value = pos[1] || 0;
          virtualPosZInput.value = pos[2] || 0;
          console.log("Updated position inputs with default values:", pos);
        }
      } catch (settingsErr) {
        console.error("Error fetching mesh settings after selection:", settingsErr);
        // Don't throw error here as mesh selection was successful
      }
      
      return data;
    }, null, `Mesh "${meshName}" selected successfully!`);
  }
  
  uploadMeshBtn.addEventListener("click", async () => {
    const file = meshFileInput.files[0];
    if (!file) {
      showNotification("Select a .obj file to upload.", "error");
      return;
    }
    
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    await handleAsyncOperation(async () => {
      const formData = new FormData();
      formData.append("mesh", file);
      
      const data = await fetchJSON(`http://${ip}:${port}/upload_mesh`, { 
        method: "POST", 
        body: formData 
      });
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Refresh mesh list after successful upload
      await refreshMeshList();
      
      return data;
    }, uploadMeshBtn, `Mesh "${file.name}" uploaded successfully!`);
  });
  
  
  async function loadInferenceModels() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    try {
      // Fetch both available models and currently selected models
      const [modelsData, selectedData] = await Promise.all([
        fetchJSON(`http://${ip}:${port}/list_inference_models`),
        fetchJSON(`http://${ip}:${port}/get_selected_models`).catch(() => ({ models: [] })) // Fallback if endpoint doesn't exist
      ]);
      
      modelList.innerHTML = "";
      
      // Update selected models from server
      if (selectedData.models && selectedData.models.length > 0) {
        selectedModels.clear();
        selectedData.models.forEach(model => selectedModels.add(model));
      } else {
        selectedModels.clear();
      }
      
      if (modelsData.models && modelsData.models.length > 0) {
        modelsData.models.forEach(model => {
          const modelItem = document.createElement('div');
          modelItem.className = 'flex items-center justify-between p-2 bg-white rounded border hover:bg-gray-50 cursor-pointer';
          modelItem.innerHTML = `
            <span class="text-sm text-gray-700">${model}</span>
            <input type="checkbox" class="model-checkbox" value="${model}" ${selectedModels.has(model) ? 'checked' : ''}>
          `;
          
          // Add click handler for the entire item
          modelItem.addEventListener('click', (e) => {
            if (e.target.type !== 'checkbox') {
              const checkbox = modelItem.querySelector('.model-checkbox');
              checkbox.checked = !checkbox.checked;
              updateModelSelection(checkbox);
            }
          });
          
          // Add change handler for checkbox
          const checkbox = modelItem.querySelector('.model-checkbox');
          checkbox.addEventListener('change', (e) => updateModelSelection(e.target));
          
          modelList.appendChild(modelItem);
        });
      } else {
        modelList.innerHTML = '<p class="text-xs text-gray-500 text-center py-4">No models available</p>';
      }
      
      updateModelCount();
    } catch (err) {
      console.error("Error fetching inference models:", err);
      modelList.innerHTML = '<p class="text-xs text-red-500 text-center py-4">Error loading models</p>';
    }
  }
  
  function updateModelSelection(checkbox) {
    if (!selectedModels) {
      selectedModels = new Set();
    }
    if (checkbox.checked) {
      selectedModels.add(checkbox.value);
    } else {
      selectedModels.delete(checkbox.value);
    }
    updateModelCount();
  }
  
  function updateModelCount() {
    if (!selectedModels) {
      selectedModels = new Set();
    }
    const count = selectedModels.size;
    modelCount.textContent = `${count} selected`;
    applyModelsBtn.disabled = count === 0;
  }
  
  async function autoReapplySelectedModels() {
    if (!selectedModels) {
      selectedModels = new Set();
    }
    if (selectedModels.size === 0) {
      return; // No models to reapply
    }
    
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    const selected = Array.from(selectedModels);
    
    try {
      console.log("Auto-reapplying selected models:", selected);
      setStatus("Restoring models...", "info");
      
      const data = await fetchJSON(`http://${ip}:${port}/select_inference_models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: selected })
      });
      
      if (data.error) {
        console.error("Error auto-reapplying models:", data.error);
        setStatus("Connected!", "success");
        showNotification("Warning: Could not restore previous models", "warning", 3000);
      } else {
        console.log("Models auto-reapplied successfully:", data.message);
        setStatus("Connected!", "success");
        showNotification(`Models restored: ${selected.join(", ")}`, "success", 3000);
      }
    } catch (error) {
      console.error("Error auto-reapplying models:", error);
      setStatus("Connected!", "success");
      showNotification("Warning: Could not restore previous models", "warning", 3000);
    }
  }
  
  applyModelsBtn.addEventListener("click", async () => {
    if (!selectedModels) {
      selectedModels = new Set();
    }
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    const selected = Array.from(selectedModels);
    
    await handleAsyncOperation(async () => {
      const data = await fetchJSON(`http://${ip}:${port}/select_inference_models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: selected })
      });
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      numInferenceModelsApplied = selected.length;
      
      return data;
    }, applyModelsBtn, `Applied ${selected.length} inference model${selected.length !== 1 ? 's' : ''}: ${selected.length ? selected.join(", ") : "None"}`);
  });
  
  uploadModelBtn.addEventListener("click", async () => {
    const file = inferenceModelFile.files[0];
    if (!file) {
      showNotification("Select a .py file to upload.", "error");
      return;
    }
    
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    await handleAsyncOperation(async () => {
      const formData = new FormData();
      formData.append("model", file);
      
      const data = await fetchJSON(`http://${ip}:${port}/upload_inference_model`, { 
        method: "POST", 
        body: formData 
      });
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Refresh inference models list after successful upload
      await loadInferenceModels();
      
      return data;
    }, uploadModelBtn, `Model "${file.name}" uploaded successfully!`);
  });
  
  // Function to load frame range for a session
  async function loadFrameRange(sessionId) {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    if (!ip || !port) {
      showNotification("Enter IP and port to load frame range.", "error");
      return null;
    }
    
    try {
      const data = await fetchJSON(`http://${ip}:${port}/list_frames?session=${encodeURIComponent(sessionId)}`);
      
      if (data.frames && data.frames.length > 0) {
        const minFrame = Math.min(...data.frames);
        const maxFrame = Math.max(...data.frames);
        
        // Update UI with frame range info
        frameRangeInfo.textContent = `${minFrame} - ${maxFrame}`;
        frameCount.textContent = data.frames.length;
        sessionName.textContent = sessionId;
        frameRangeDetails.classList.remove('hidden');
        
        // Set input constraints for global frame input
        globalFrameInput.min = minFrame;
        globalFrameInput.max = maxFrame;
        globalFrameInput.placeholder = `Enter frame number (${minFrame}-${maxFrame})`;
        
        return { frames: data.frames, minFrame, maxFrame };
      } else {
        frameRangeInfo.textContent = "No frames available";
        frameRangeDetails.classList.add('hidden');
        showNotification("No frames found in this session.", "warning");
        return null;
      }
    } catch (error) {
      console.error('Error fetching frame range:', error);
      frameRangeInfo.textContent = "Error loading";
      frameRangeDetails.classList.add('hidden');
      showNotification(error.message || 'An error occurred while loading frame range', 'error');
      return null;
    }
  }

  // Load frame range when global session changes
  globalSessionSelect.addEventListener('change', async () => {
    const sessionId = globalSessionSelect.value.trim();
    if (sessionId) {
      await loadFrameRange(sessionId);
    } else {
      frameRangeInfo.textContent = "Not loaded";
      frameRangeDetails.classList.add('hidden');
    }
  });

  // Validate global frame number input
  globalFrameInput.addEventListener('input', () => {
    const value = parseInt(globalFrameInput.value);
    const min = parseInt(globalFrameInput.min);
    const max = parseInt(globalFrameInput.max);
    
    if (globalFrameInput.value && !isNaN(value)) {
      if (value < min || value > max) {
        globalFrameInput.classList.add('border-red-500');
        globalFrameInput.classList.remove('border-gray-300');
      } else {
        globalFrameInput.classList.remove('border-red-500');
        globalFrameInput.classList.add('border-gray-300');
      }
    } else {
      globalFrameInput.classList.remove('border-red-500');
      globalFrameInput.classList.add('border-gray-300');
    }
  });

  // Load specific frame
  loadFrameBtn.addEventListener("click", async () => {
    const sessionId = globalSessionSelect.value.trim();
    const frameNumber = globalFrameInput.value;
    
    if (!sessionId) {
      showNotification("Please select a session from the global session selector above.", "error");
      return;
    }
    
    if (!frameNumber) {
      showNotification("Please enter a frame number in the global frame input above.", "error");
      return;
    }
    
    const frameNum = parseInt(frameNumber);
    if (isNaN(frameNum)) {
      showNotification("Please enter a valid frame number.", "error");
      return;
    }
    
    // Check if frame number is within valid range
    const min = parseInt(globalFrameInput.min);
    const max = parseInt(globalFrameInput.max);
    if (frameNum < min || frameNum > max) {
      showNotification(`Frame number must be between ${min} and ${max}.`, "error");
      return;
    }
    
    // Set current session for frame loading
    currentSession = sessionId;
    
    try {
      await loadFrameDetails(frameNum);
    } catch (error) {
      console.error('Error loading frame:', error);
      showNotification(error.message || 'An error occurred while loading frame', 'error');
    }
  });
  
  async function loadFrameDetails(frameIndex) {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    await handleAsyncOperation(async () => {
      const data = await fetchJSON(`http://${ip}:${port}/frame_details?session=${encodeURIComponent(currentSession)}&frame=${frameIndex}`);
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Update base images with fade-in effect
      document.getElementById("frameDetailsRows").innerHTML = "";
      document.getElementById("detailRGB_0").src = "data:image/png;base64," + data.rgb;
      document.getElementById("detailRGB_0").classList.add('fade-in');
      document.getElementById("detailComposite_0").src = "data:image/png;base64," + data.composite;
      document.getElementById("detailComposite_0").classList.add('fade-in');
      document.getElementById("detailOriginalDepth_0").src = "data:image/png;base64," + data.original_depth_colormap;
      document.getElementById("detailOriginalDepth_0").classList.add('fade-in');
      
      // Add inferred results with enhanced styling
      for (const model in data.inferred_depth_colormaps) {
        let rowDiv = document.createElement("div");
        rowDiv.className = "grid grid-cols-3 gap-4 mb-6 fade-in";
        rowDiv.innerHTML = `
          <div class="image-container">
            <h4 class="text-md font-medium text-gray-700 mb-2 flex items-center">
              <span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
              Raw RGB (${model})
            </h4>
            <img src="data:image/png;base64,${data.rgb}" class="w-full rounded-lg border shadow-sm" loading="lazy">
          </div>
          <div class="image-container">
            <h4 class="text-md font-medium text-gray-700 mb-2 flex items-center">
              <span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
              Composite (${model})
            </h4>
            <img src="data:image/png;base64,${data.inferred_composites[model]}" class="w-full rounded-lg border shadow-sm" loading="lazy">
          </div>
          <div class="image-container">
            <h4 class="text-md font-medium text-gray-700 mb-2 flex items-center">
              <span class="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
              Depth (${model})
            </h4>
            <img src="data:image/png;base64,${data.inferred_depth_colormaps[model]}" class="w-full rounded-lg border shadow-sm" loading="lazy">
          </div>`;
        document.getElementById("frameDetailsRows").appendChild(rowDiv);
      }
      
      frameDetails.classList.remove("hidden");
      frameDetails.classList.add("fade-in");
      
      return data;
    }, null, `Frame ${frameIndex} details loaded successfully!`);
  }

  // Render per-position composites using server /render_positions
  if (renderPositionsBtn) {
    renderPositionsBtn.addEventListener('click', async () => {
      const ip = ipAddressInput.value.trim();
      const port = portInput.value.trim();
      const session = globalSessionSelect.value.trim();
      const frame = globalFrameInput.value.trim();
      if (!ip || !port || !session || !frame) {
        showNotification('Please connect, select a session and frame first.', 'error');
        return;
      }
      try {
        renderPositionsBtn.disabled = true;
        renderPositionsBtn.textContent = 'Rendering...';
        renderPositionsGrid.innerHTML = '';
        const url = `http://${ip}:${port}/render_positions`;
        console.log('Calling /render_positions:', { url, session, frame });
        const data = await fetchJSON(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session, frame: parseInt(frame, 10) })
        });
        if (data.error) {
          throw new Error(data.error);
        }
        const images = data.images || [];
        if (images.length === 0) {
          renderPositionsGrid.innerHTML = '<p class="text-sm text-gray-500">No candidate positions found in metadata.</p>';
          return;
        }
        showNotification(`Rendered ${images.length} positions`, 'success');
        images.forEach(item => {
          const card = document.createElement('div');
          card.className = 'bg-white rounded-lg border border-gray-200 p-3';
          const [x, y, z] = item.position;
          card.innerHTML = `
            <div class="text-sm text-gray-700 mb-2">#${item.index} at (${x.toFixed(3)}, ${y.toFixed(3)}, ${z.toFixed(3)})</div>
            <img class="w-full rounded border" src="data:image/png;base64,${item.image_base64}" loading="lazy" />
          `;
          renderPositionsGrid.appendChild(card);
        });
      } catch (err) {
        console.error('Error rendering positions:', err);
        showNotification(err.message || 'Error rendering positions', 'error');
      } finally {
        renderPositionsBtn.disabled = false;
        renderPositionsBtn.textContent = 'Render Candidate Positions';
      }
    });
  }
  
  function establishConnection(wsUrl) {
    console.log("Establishing WebSocket connection to:", wsUrl);
    setStatus("Connecting...");
    if (ws && ws.readyState !== WebSocket.CLOSED) ws.close();
    ws = new WebSocket(wsUrl);
    ws.binaryType = "blob";
    ws.onopen = () => {
      console.log("WebSocket connected");
      setStatus("Connected!", "success");
      connectionSection.classList.add("hidden");
      dashboardSection.classList.remove("hidden");
      
      // Update connection state as successful
      const ip = ipAddressInput.value.trim();
      const port = portInput.value.trim();
      saveConnectionState(ip, port, true);
      
      // Update connection info display
      const connectionInfo = document.getElementById('connectionInfo');
      if (connectionInfo) {
        connectionInfo.textContent = `Server: ${ip}:${port}`;
      }
      
      loadInferenceModels();
      getMeshSettings(); // Load mesh settings when connected
      refreshMeshList(); // Load mesh list when connected
      loadGlobalSessions(); // Load sessions list when connected
      
      // Auto-reapply selected models after a short delay to ensure models are loaded
      setTimeout(() => {
        autoReapplySelectedModels();
      }, 1000);
    };
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setStatus("WebSocket error. Check console.", "error");
    };
    ws.onclose = () => {
      console.log("WebSocket closed.");
      setStatus("Connection closed.", "warning");
      // Clear connection state when disconnected
      clearConnectionState();
    };
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        try {
          const data = JSON.parse(event.data);
          if (currentMode === "replay" && data.replay_frames) {
            for (const key in data.replay_frames) {
              if (!replayVideoElements[key]) {
                const gridItem = document.createElement("div");
                gridItem.className = "border rounded p-2";
                gridItem.innerHTML = `<p class="text-sm font-semibold mb-1">${key}</p><img class="w-full rounded">`;
                replayGrid.appendChild(gridItem);
                replayVideoElements[key] = gridItem.querySelector("img");
              }
              replayVideoElements[key].src = "data:image/png;base64," + data.replay_frames[key];
            }
          } else {
            console.log("Received message:", data);
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      } else {
        const url = URL.createObjectURL(event.data);
        if (currentMode === "live") liveStream.src = url;
        setTimeout(() => URL.revokeObjectURL(url), 100);
      }
    };
  }
  
  function reconnectToLive() {
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    if (!ip || !port) {
      setStatus("IP and port required.", "error");
      return;
    }
    establishConnection(`ws://${ip}:${port}/live`);
  }
  
  // Point cloud functionality
  let currentPointCloudData = null;
  
  
  generatePointCloudBtn.addEventListener("click", async () => {
    const session = globalSessionSelect.value.trim();
    const frame = globalFrameInput.value.trim();
    
    if (!session || !frame) {
      showNotification("Please select a session and enter a frame number in the global selectors above.", "error");
      return;
    }
    
    const ip = ipAddressInput.value.trim();
    const port = portInput.value.trim();
    
    if (!ip || !port) {
      showNotification("Please connect to server first.", "error");
      return;
    }
    
    // First, get information about available point clouds
    let pointCloudInfoData = null;
    try {
      const infoResponse = await fetch(`http://${ip}:${port}/point_cloud_info?session=${session}&frame=${frame}`);
      if (infoResponse.ok) {
        pointCloudInfoData = await infoResponse.json();
        console.log('Point cloud info:', pointCloudInfoData);
      }
    } catch (error) {
      console.warn('Could not fetch point cloud info:', error);
    }
    
    // Generate the point clouds
    currentPointCloudData = await handleAsyncOperation(async () => {
      const response = await fetch(`http://${ip}:${port}/point_cloud?session=${session}&frame=${frame}`);
      if (!response.ok) {
        throw new Error(`Failed to generate point cloud: ${response.statusText}`);
      }
      return response.blob();
    }, generatePointCloudBtn, `Point clouds generated for session ${session}, frame ${frame}!`);
    
    if (currentPointCloudData) {
      // Show success UI
      pointCloudInfo.classList.remove("hidden");
      pointCloudDownload.classList.remove("hidden");
      pointCloudPreview.classList.remove("hidden");
      
      // Show available point clouds list if we have the info
      if (pointCloudInfoData && pointCloudInfoData.available_point_clouds) {
        pointCloudList.classList.remove("hidden");
        pointCloudItems.innerHTML = '';
        
        pointCloudInfoData.available_point_clouds.forEach(cloudName => {
          const item = document.createElement('div');
          item.className = 'flex items-center space-x-2';
          item.innerHTML = `
            <span class="w-2 h-2 bg-blue-500 rounded-full"></span>
            <span>point_cloud_${cloudName}.ply</span>
          `;
          pointCloudItems.appendChild(item);
        });
      }
      
      // Show success message
      console.log('Point clouds generated successfully');
      console.log('ZIP file ready for download');
    }
  });
  
  downloadPointCloudBtn.addEventListener("click", () => {
    if (!currentPointCloudData) {
      showNotification("No point cloud data available. Generate point clouds first.", "error");
      return;
    }
    
    const session = globalSessionSelect.value.trim();
    const frame = globalFrameInput.value.trim();
    const filename = `point_clouds_${session}_frame_${frame}.zip`;
    
    const url = URL.createObjectURL(currentPointCloudData);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification("Point clouds ZIP file downloaded successfully!", "success");
  });
  
  
  
  
  
  
  // Check for saved connection state on page load
  checkSavedConnection();
});
