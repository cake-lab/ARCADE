import SwiftUI
import RealityKit
import ARKit
import CoreImage
import UIKit
import Combine
import Accelerate

// Disambiguate RealityKit.Material from SwiftUI.Material
typealias RKMaterial = any RealityKit.Material

// MARK: - UI

struct ContentView: View {
    @StateObject private var arViewModel = ARViewModel()
    @State private var isRecording = false
    @State private var showServerSheet = false

    // Persist across launches
    @AppStorage("ws_ip") private var wsIP: String = "100.78.65.25"
    @AppStorage("ws_port") private var wsPort: String = "5034"
    @AppStorage("ws_path") private var wsPath: String = "/websocket"

    var body: some View {
        ZStack(alignment: .top) {
            ARViewContainer(arViewModel: arViewModel)
                .edgesIgnoringSafeArea(.all)

            VStack {
                HStack(spacing: 12) {
                    Button(action: { showServerSheet = true }) {
                        Text("Server")
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(Color.black.opacity(0.5))
                            .cornerRadius(8)
                    }

                    Button(action: toggleRecording) {
                        Text(recordButtonTitle)
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(recordButtonColor)
                            .cornerRadius(8)
                    }
                    .disabled(arViewModel.wsState == .connecting)

                    Spacer()
                }
                .padding()

                // Optional: show connection state
                Text(connectionLabel)
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.black.opacity(0.35))
                    .cornerRadius(8)
                    .padding(.top, 4)

                Spacer()
            }
        }
        .onAppear {
            arViewModel.setServer(ip: wsIP, port: wsPort, path: wsPath)
        }
        .sheet(isPresented: $showServerSheet) {
            ServerSettingsView(ip: $wsIP, port: $wsPort, path: $wsPath) { ip, port, path in
                arViewModel.setServer(ip: ip, port: port, path: path)
            }
        }
    }

    private var recordButtonTitle: String {
        if isRecording { return "Stop Recording" }
        if arViewModel.wsState == .connecting { return "Connecting..." }
        return "Start Recording"
    }

    private var recordButtonColor: Color {
        if isRecording { return Color.red.opacity(0.5) }
        return Color.black.opacity(0.5)
    }

    private var connectionLabel: String {
        switch arViewModel.wsState {
        case .disconnected: return "Disconnected"
        case .connecting: return "Connecting..."
        case .connected: return "Connected"
        case .failed(let msg): return "Failed: \(msg)"
        }
    }

    private func toggleRecording() {
        if isRecording {
            isRecording = false
            arViewModel.stopCapturing()
        } else {
            isRecording = true
            arViewModel.startCapturing()
        }
    }
}

struct ARViewContainer: UIViewRepresentable {
    @ObservedObject var arViewModel: ARViewModel

    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)
        arViewModel.arView = arView
        arViewModel.setupARView()
        return arView
    }

    func updateUIView(_ uiView: ARView, context: Context) { }
}

// MARK: - Server Settings Sheet

struct ServerSettingsView: View {
    @Environment(\.dismiss) private var dismiss

    @Binding var ip: String
    @Binding var port: String
    @Binding var path: String

    let onSave: (_ ip: String, _ port: String, _ path: String) -> Void

    @State private var errorText: String?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("WebSocket Server")) {
                    TextField("IP or hostname", text: $ip)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    TextField("Port", text: $port)
                        .keyboardType(.numberPad)

                    TextField("Path", text: $path)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                if let errorText {
                    Section {
                        Text(errorText).foregroundColor(.red)
                    }
                }

                Section {
                    Button("Save") {
                        let trimmedIP = ip.trimmingCharacters(in: .whitespacesAndNewlines)
                        let trimmedPort = port.trimmingCharacters(in: .whitespacesAndNewlines)
                        let trimmedPath = path.trimmingCharacters(in: .whitespacesAndNewlines)

                        guard isValidHost(trimmedIP) else {
                            errorText = "Enter a valid IP or hostname."
                            return
                        }
                        guard let p = Int(trimmedPort), (1...65535).contains(p) else {
                            errorText = "Enter a valid port (1–65535)."
                            return
                        }

                        let normalizedPath = normalizePath(trimmedPath)
                        errorText = nil
                        onSave(trimmedIP, "\(p)", normalizedPath)
                        dismiss()
                    }
                }
            }
            .navigationTitle("Server")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private func normalizePath(_ s: String) -> String {
        if s.isEmpty { return "/websocket" }
        return s.hasPrefix("/") ? s : "/" + s
    }

    private func isValidHost(_ s: String) -> Bool {
        if s.isEmpty { return false }
        // Simple allowlist for IPv4/IPv6/hostname chars
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:")
        return s.rangeOfCharacter(from: allowed.inverted) == nil
    }
}

// MARK: - Frame throttler (stable cadence)

final class FrameThrottler {
    private let fps: Double
    private var lastFire: CFTimeInterval = 0

    init(fps: Double) { self.fps = fps }

    func shouldFire(now: CFTimeInterval) -> Bool {
        let budget = 1.0 / fps
        if now - lastFire >= budget {
            lastFire = now
            return true
        }
        return false
    }
}

// MARK: - ViewModel

final class ARViewModel: NSObject, ObservableObject, ARSessionDelegate {

    // MARK: WebSocket state

    enum WSState: Equatable {
        case disconnected
        case connecting
        case connected
        case failed(String)
    }

    @Published private(set) var wsState: WSState = .disconnected
    private var shouldStartCaptureAfterConnect = false

    // AR
    var arView: ARView?
    private var updateSubscription: Cancellable?
    private var isInitialized = false

    // WebSocket config (editable)
    private var serverIP: String = "100.78.65.25"
    private var serverPort: Int = 5034
    private var serverPath: String = "/websocket"

    private var webSocketURL: URL? {
        var comps = URLComponents()
        comps.scheme = "ws"
        comps.host = serverIP
        comps.port = serverPort
        comps.path = serverPath.isEmpty ? "/websocket" : serverPath
        return comps.url
    }

    // WebSocket runtime
    private var webSocketTask: URLSessionWebSocketTask?
    private var sendBusy = false      // strict budget: single in-flight send

    // Content
    private var teapotEntity: ModelEntity?

    // Plane tracking & candidates
    private var planeAnchors: [ARPlaneAnchor] = []
    @Published var candidatePositions: [SIMD3<Float>] = []
    private var candidatePositionsSerialized: [[Float]] = []

    // Tuning
    private let targetFPS: Double = 20.0
    private lazy var throttler = FrameThrottler(fps: targetFPS)
    private let jpegQuality: CGFloat = 0.8
    private let outWidth = 640
    private let outHeight = 480
    private let liveDownscale: CGFloat = 1.0

    private let objectFootprintRadius: Float = 0.06
    private let gridStep: Float = 0.20
    private let minDistanceBetweenObjects: Float = 0.15
    private let candidateRefreshHz: Double = 2.0
    private var lastCandidateUpdateTime: TimeInterval = 0

    // Debug
    private let debugLog = false
    private var lastLogTime: TimeInterval = 0

    // --- Object mask snapshot helpers (safe) ---
    private var originalMaterials: [ObjectIdentifier: [RKMaterial]] = [:]
    private var maskBackdrop: ModelEntity?
    private var cameraAnchor: AnchorEntity?
    private var maskBusy = false

    // MARK: Public: set server

    func setServer(ip: String, port: String, path: String) {
        serverIP = ip
        serverPort = Int(port) ?? 5034
        serverPath = path.isEmpty ? "/websocket" : path

        // If already running/connected, reconnect.
        if updateSubscription != nil || webSocketTask != nil {
            reconnectWebSocket()
        }
    }

    // MARK: Setup

    func setupARView() {
        guard let arView = arView else { return }

        let configuration = ARWorldTrackingConfiguration()
        configuration.frameSemantics = [.sceneDepth]
        configuration.planeDetection = [.horizontal]
        configuration.worldAlignment = .gravity
        arView.session.run(configuration, options: [.resetTracking, .removeExistingAnchors])
        arView.session.delegate = self

        // Load teapot
        guard let modelEntity = try? ModelEntity.loadModel(named: "teapot.usdz") else {
            fatalError("Unable to load teapot.usdz. Make sure the file is added to the project.")
        }
        modelEntity.scale = [0.006, 0.006, 0.006]
        self.teapotEntity = modelEntity

        let anchor = AnchorEntity(plane: .horizontal, minimumBounds: [0.2, 0.2])
        anchor.addChild(modelEntity)
        arView.scene.addAnchor(anchor)
    }

    // MARK: Capture control

    func startCapturing() {
        guard arView != nil else { return }

        // Already connected -> start right away.
        if wsState == .connected {
            beginFrameLoop()
            return
        }

        // Otherwise connect first; only start after ping succeeds.
        shouldStartCaptureAfterConnect = true
        connectWebSocket()
    }

    func stopCapturing() {
        shouldStartCaptureAfterConnect = false

        updateSubscription?.cancel()
        updateSubscription = nil

        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil

        sendBusy = false
        isInitialized = false
        wsState = .disconnected
    }

    private func beginFrameLoop() {
        guard let arView = arView else { return }

        // Avoid double subscription
        updateSubscription?.cancel()

        updateSubscription = arView.scene.subscribe(to: SceneEvents.Update.self) { [weak self] _ in
            guard let self = self, let frame = self.arView?.session.currentFrame else { return }
            let t = frame.timestamp

            if self.throttler.shouldFire(now: t) {
                self.captureCurrentFrame(frame: frame)
            }

            if (t - self.lastCandidateUpdateTime) >= (1.0 / self.candidateRefreshHz) {
                self.lastCandidateUpdateTime = t
                self.refreshCandidateSpots()

                if self.debugLog, (t - self.lastLogTime) > 2.0 {
                    self.lastLogTime = t
                    print("planes=\(self.planeAnchors.count) candidates=\(self.candidatePositions.count)")
                }
            }
        }

        refreshCandidateSpots()
    }

    // MARK: WebSocket

    private func reconnectWebSocket() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        sendBusy = false
        isInitialized = false
        wsState = .disconnected
        connectWebSocket()
    }

    private func connectWebSocket() {
        // If already connecting/connected, do nothing.
        if wsState == .connecting || wsState == .connected { return }

        guard let url = webSocketURL else {
            wsState = .failed("Invalid URL")
            return
        }

        wsState = .connecting

        let cfg = URLSessionConfiguration.default
        cfg.waitsForConnectivity = false
        cfg.allowsCellularAccess = true
        cfg.allowsExpensiveNetworkAccess = true
        cfg.allowsConstrainedNetworkAccess = true

        let urlSession = URLSession(configuration: cfg)
        webSocketTask = urlSession.webSocketTask(with: url)
        webSocketTask?.resume()

        receiveMessage()
        verifyConnectedAndStartIfNeeded()
    }

    private func verifyConnectedAndStartIfNeeded() {
        guard let task = webSocketTask else {
            wsState = .failed("No socket task")
            return
        }

        // This confirms the WebSocket is actually open.
        task.sendPing { [weak self] error in
            DispatchQueue.main.async {
                guard let self = self else { return }

                if let error = error {
                    self.wsState = .failed("Ping failed: \(error.localizedDescription)")
                    self.webSocketTask?.cancel(with: .goingAway, reason: nil)
                    self.webSocketTask = nil
                    self.sendBusy = false
                    self.isInitialized = false
                    return
                }

                self.wsState = .connected

                if self.shouldStartCaptureAfterConnect {
                    self.shouldStartCaptureAfterConnect = false
                    self.beginFrameLoop()
                }
            }
        }
    }

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }

            switch result {
            case .failure(let error):
                DispatchQueue.main.async {
                    self.wsState = .failed("Receive error: \(error.localizedDescription)")
                }
            case .success(let message):
                if self.debugLog {
                    switch message {
                    case .string(let text): print("Received text: \(text)")
                    case .data(let data): print("Received data (\(data.count) bytes)")
                    @unknown default: print("Received unknown message")
                    }
                }
            }

            // Keep receiving unless we're disconnected.
            if self.webSocketTask != nil {
                self.receiveMessage()
            }
        }
    }

    private func sendJSONString(_ jsonString: String) {
        guard let webSocketTask = webSocketTask else { return }
        if sendBusy { return } // strict single in-flight send

        sendBusy = true
        webSocketTask.send(.string(jsonString)) { [weak self] error in
            if let error = error { print("WebSocket send error: \(error)") }
            self?.sendBusy = false
        }
    }

    // MARK: Frame capture

    private func captureCurrentFrame(frame: ARFrame) {
        guard wsState == .connected else { return }
        guard let teapot = teapotEntity else { return }

        // Depth (raw bytes)
        var depthData: Data? = nil
        var widthDepth = -1
        var heightDepth = -1
        if let sceneDepth = frame.sceneDepth {
            let result = getDepthData(from: sceneDepth.depthMap)
            depthData = result.data
            widthDepth = result.width
            heightDepth = result.height
        }

        // RGB (fast downscale + JPEG)
        guard let rgbData = getRGBImageDataFast(
            frame.capturedImage,
            outW: Int(CGFloat(outWidth) * liveDownscale),
            outH: Int(CGFloat(outHeight) * liveDownscale),
            quality: jpegQuality
        ) else { return }

        // Initialize intrinsics/resolutions once (scaled to out size)
        if !isInitialized {
            let originalWidth = CVPixelBufferGetWidth(frame.capturedImage)
            let originalHeight = CVPixelBufferGetHeight(frame.capturedImage)
            let newWidth = Int(CGFloat(outWidth) * liveDownscale)
            let newHeight = Int(CGFloat(outHeight) * liveDownscale)

            let scaleX = CGFloat(newWidth) / CGFloat(originalWidth)
            let scaleY = CGFloat(newHeight) / CGFloat(originalHeight)
            let K = frame.camera.intrinsics
            let fx = K.columns.0.x * Float(scaleX)
            let fy = K.columns.1.y * Float(scaleY)
            let cx = K.columns.2.x * Float(scaleX)
            let cy = K.columns.2.y * Float(scaleY)

            let initMsg: [String: Any] = [
                "type": "initialize",
                "intrinsics": [fx, fy, cx, cy],
                "rgbResolution": [newWidth, newHeight],
                "depthResolution": [widthDepth, heightDepth]
            ]
            if let json = toJSONString(initMsg) {
                sendJSONString(json)
            }

            isInitialized = true
            if debugLog { print("Sent initialization message.") }
        }

        // Metadata (+ capture timestamp)
        let teapotWorldPosition = teapot.position(relativeTo: nil)
        var metadata = createFrameMetadata(
            frame: frame,
            objPosition: [teapotWorldPosition.x, teapotWorldPosition.y, teapotWorldPosition.z],
            candidatePositions: candidatePositionsSerialized
        )
        metadata["ts_capture_ms"] = monotonicMS()

        sendFrameToWebSocket(metadata: metadata, rgbData: rgbData, depthData: depthData)
    }

    // Fast downscale using CIContext, then JPEG encoding
    private func getRGBImageDataFast(_ pixelBuffer: CVPixelBuffer,
                                     outW: Int, outH: Int,
                                     quality: CGFloat) -> Data? {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let scaleX = CGFloat(outW) / ciImage.extent.width
        let scaleY = CGFloat(outH) / ciImage.extent.height
        let scale = min(scaleX, scaleY)

        let resized = ciImage
            .transformed(by: CGAffineTransform(scaleX: scale, y: scale))
            .cropped(to: CGRect(origin: .zero, size: CGSize(width: outW, height: outH)))

        struct Static {
            static let ctx = CIContext(options: [
                .priorityRequestLow: true,
                .useSoftwareRenderer: false
            ])
        }

        guard let cg = Static.ctx.createCGImage(
            resized,
            from: CGRect(x: 0, y: 0, width: outW, height: outH)
        ) else { return nil }

        let ui = UIImage(cgImage: cg)
        return ui.jpegData(compressionQuality: quality)
    }

    private func getDepthData(from depthMap: CVPixelBuffer) -> (data: Data, width: Int, height: Int) {
        CVPixelBufferLockBaseAddress(depthMap, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(depthMap, .readOnly) }

        let height = CVPixelBufferGetHeight(depthMap)
        let width = CVPixelBufferGetWidth(depthMap)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(depthMap)

        guard let baseAddress = CVPixelBufferGetBaseAddress(depthMap) else {
            return (Data(), width, height)
        }

        let data = Data(bytes: baseAddress, count: bytesPerRow * height)
        return (data, width, height)
    }

    private func sendFrameToWebSocket(metadata: [String: Any], rgbData: Data, depthData: Data?) {
        if sendBusy { return } // strict: drop if busy
        guard wsState == .connected else { return }

        let rgbBase64 = rgbData.base64EncodedString()
        let depthBase64 = depthData?.base64EncodedString() ?? ""

        let frameMsg: [String: Any] = [
            "type": "frame",
            "metadata": metadata,
            "rgbImage": rgbBase64,
            "depthData": depthBase64
        ]

        if let json = toJSONString(frameMsg) {
            sendJSONString(json)
            if debugLog { print("Sent frame message.") }
        }
    }

    private func toJSONString(_ dict: [String: Any]) -> String? {
        guard JSONSerialization.isValidJSONObject(dict),
              let data = try? JSONSerialization.data(withJSONObject: dict, options: []),
              let str = String(data: data, encoding: .utf8) else { return nil }
        return str
    }

    private func createFrameMetadata(frame: ARFrame, objPosition: [Float], candidatePositions: [[Float]]) -> [String: Any] {
        let timestamp = frame.timestamp
        let transform = frame.camera.transform
        let pose4x4: [Float] = [
            transform.columns.0.x, transform.columns.0.y, transform.columns.0.z, transform.columns.0.w,
            transform.columns.1.x, transform.columns.1.y, transform.columns.1.z, transform.columns.1.w,
            transform.columns.2.x, transform.columns.2.y, transform.columns.2.z, transform.columns.2.w,
            transform.columns.3.x, transform.columns.3.y, transform.columns.3.z, transform.columns.3.w
        ]
        return [
            "timestamp": timestamp,
            "pose4x4": pose4x4,
            "objPosition": objPosition,
            "candidatePositions": candidatePositions
        ]
    }

    // MARK: Object mask snapshot (unchanged, safe)

    private func generateObjectMaskSnapshot(completion: @escaping (Data?) -> Void) {
        if maskBusy { completion(nil); return }
        maskBusy = true

        DispatchQueue.main.async {
            guard let arView = self.arView, let teapot = self.teapotEntity else {
                self.maskBusy = false
                completion(nil)
                return
            }

            let key = ObjectIdentifier(teapot)
            if self.originalMaterials[key] == nil, let mc = teapot.model {
                self.originalMaterials[key] = mc.materials
            }

            if var mc = teapot.model {
                let white = RealityKit.UnlitMaterial(color: .white)
                mc.materials = [white]
                teapot.model = mc
            }

            if self.cameraAnchor == nil {
                let cam = AnchorEntity(.camera)
                arView.scene.addAnchor(cam)
                self.cameraAnchor = cam
            }

            if self.maskBackdrop == nil {
                let mesh = MeshResource.generatePlane(width: 6.0, depth: 6.0)
                let black = RealityKit.UnlitMaterial(color: .black)
                let quad = ModelEntity(mesh: mesh, materials: [black])
                quad.transform.rotation = simd_quatf(angle: .pi / 2, axis: SIMD3<Float>(1, 0, 0))
                quad.position = [0, 0, -0.5]
                self.maskBackdrop = quad
            }

            if let quad = self.maskBackdrop, quad.parent == nil {
                self.cameraAnchor?.addChild(quad)
            }

            arView.snapshot(saveToHDR: false) { img in
                if var mc = teapot.model, let mats = self.originalMaterials[key] {
                    mc.materials = mats
                    teapot.model = mc
                }

                self.maskBackdrop?.removeFromParent()
                self.maskBusy = false

                if let img = img, let png = img.pngData() {
                    completion(png)
                } else {
                    completion(nil)
                }
            }
        }
    }

    // MARK: Plane candidate generation

    private func refreshCandidateSpots() {
        guard !planeAnchors.isEmpty else {
            candidatePositions = []
            candidatePositionsSerialized = []
            return
        }

        var occupied: [SIMD3<Float>] = []
        if let teapot = teapotEntity {
            occupied.append(teapot.position(relativeTo: nil))
        }

        var allCandidatesWorld: [SIMD3<Float>] = []

        for plane in planeAnchors {
            guard plane.extent.x > 0.05, plane.extent.z > 0.05 else { continue }
            let localCandidates = sampleGridOnPlane(plane: plane, step: gridStep, margin: objectFootprintRadius)

            let T = plane.transform
            let c = plane.center

            for lc in localCandidates {
                let local4 = SIMD4<Float>(lc.x + c.x, 0, lc.y + c.z, 1)
                let world4 = T * local4
                let world = SIMD3<Float>(world4.x, world4.y, world4.z)

                if occupied.contains(where: { simd_distance($0, world) < minDistanceBetweenObjects }) { continue }
                allCandidatesWorld.append(world)
            }
        }

        candidatePositions = allCandidatesWorld
        candidatePositionsSerialized = allCandidatesWorld.map { [$0.x, $0.y, $0.z] }
    }

    private func sampleGridOnPlane(plane: ARPlaneAnchor, step: Float, margin: Float) -> [SIMD2<Float>] {
        let halfX = max(plane.extent.x * 0.5 - margin, 0)
        let halfZ = max(plane.extent.z * 0.5 - margin, 0)
        guard halfX > 0, halfZ > 0 else { return [] }

        var out: [SIMD2<Float>] = []
        var x = -halfX
        while x <= halfX {
            var z = -halfZ
            while z <= halfZ {
                out.append(SIMD2<Float>(x, z))
                z += step
            }
            x += step
        }
        return out
    }

    // MARK: ARSessionDelegate

    func session(_ session: ARSession, didAdd anchors: [ARAnchor]) {
        var changed = false
        for a in anchors {
            if let p = a as? ARPlaneAnchor, p.alignment == .horizontal {
                planeAnchors.append(p)
                changed = true
            }
        }
        if changed { refreshCandidateSpots() }
    }

    func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
        var changed = false
        for a in anchors {
            if let p = a as? ARPlaneAnchor, p.alignment == .horizontal {
                if let idx = planeAnchors.firstIndex(where: { $0.identifier == p.identifier }) {
                    planeAnchors[idx] = p
                } else {
                    planeAnchors.append(p)
                }
                changed = true
            }
        }
        if changed { refreshCandidateSpots() }
    }

    func session(_ session: ARSession, didRemove anchors: [ARAnchor]) {
        var changed = false
        for a in anchors {
            if let p = a as? ARPlaneAnchor {
                let before = planeAnchors.count
                planeAnchors.removeAll { $0.identifier == p.identifier }
                changed = changed || (planeAnchors.count != before)
            }
        }
        if changed { refreshCandidateSpots() }
    }

    // MARK: Utils

    private func monotonicMS() -> Double {
        (CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970) * 1000.0
    }
}
