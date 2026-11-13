import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RotateCcw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

const DEFAULT_TOPOLOGY = {
  nodes: [
    { id: 'gateway', name: 'api-gateway', display: 'API Gateway', tier: 'edge', x: -160, y: 0, z: 0 },
    { id: 'auth', name: 'auth-svc', display: 'Auth Service', tier: 'core', x: -60, y: 70, z: 40 },
    { id: 'checkout', name: 'checkout-svc', display: 'Checkout Service', tier: 'core', x: -50, y: -40, z: -30 },
    { id: 'inventory', name: 'inventory-svc', display: 'Inventory Service', tier: 'backend', x: 60, y: -80, z: -50 },
    { id: 'payments', name: 'payments-svc', display: 'Payments Service', tier: 'backend', x: 60, y: 30, z: 50 },
    { id: 'orders-db', name: 'orders-db', display: 'Orders DB', tier: 'datastore', x: 170, y: -20, z: -20 },
    { id: 'cache', name: 'cache', display: 'Redis Cache', tier: 'datastore', x: 160, y: 80, z: 30 }
  ],
  edges: [
    { from: 'gateway', to: 'auth' },
    { from: 'gateway', to: 'checkout' },
    { from: 'checkout', to: 'payments' },
    { from: 'checkout', to: 'inventory' },
    { from: 'checkout', to: 'orders-db' },
    { from: 'payments', to: 'orders-db' },
    { from: 'inventory', to: 'cache' },
    { from: 'auth', to: 'cache' }
  ]
};

export function Topology3D({ 
  graphData, 
  activeSim, 
  onSelectNode, 
  height = '420px', 
  interactive = true,
  title = 'Autonomous Service Dependency Grid'
}) {
  const containerRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const controlsRef = useRef({});

  // Determine active incident and affected services
  const hasIncident = activeSim && activeSim.active && activeSim.sim.phase !== 'resolved';
  const rootSvcId = hasIncident && activeSim.sim.scenario ? activeSim.sim.scenario.svc : (graphData?.root_service || null);
  const propagationPath = (graphData && graphData.propagation_path) || (hasIncident ? ['checkout-svc', rootSvcId] : []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // SCENE SETUP
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050914, 0.0018);

    const width = container.clientWidth;
    const heightPx = container.clientHeight || 420;

    const camera = new THREE.PerspectiveCamera(45, width / heightPx, 1, 2000);
    camera.position.set(0, 40, 460);

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch {
      return; // Fallback handled gracefully
    }

    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // LIGHTS
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00d9ff, 1.2);
    dirLight1.position.set(200, 300, 200);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x328bff, 0.8);
    dirLight2.position.set(-200, -200, -100);
    scene.add(dirLight2);

    // GROUPS
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // Subtle 3D Grid Plane
    const gridHelper = new THREE.GridHelper(520, 26, 0x00d9ff, 0x101d30);
    gridHelper.position.y = -110;
    gridHelper.material.opacity = 0.22;
    gridHelper.material.transparent = true;
    worldGroup.add(gridHelper);

    // MERGE NODES
    const rawNodes = (graphData && graphData.nodes && graphData.nodes.length > 0)
      ? graphData.nodes
      : DEFAULT_TOPOLOGY.nodes;

    const nodeMap = new Map();
    const nodeMeshes = [];

    // Colors
    const COLOR_HEALTHY = 0x00e6a0; // Green
    const COLOR_DEGRADED = 0xffae42; // Amber
    const COLOR_FAILING = 0xff3d55; // Red
    const COLOR_CYAN = 0x00d9ff;

    rawNodes.forEach((node, idx) => {
      const def = DEFAULT_TOPOLOGY.nodes.find(d => d.id === node.id || d.name === node.name) || {};
      const x = node.x ?? def.x ?? (idx * 50 - 150);
      const y = node.y ?? def.y ?? (Math.sin(idx) * 40);
      const z = node.z ?? def.z ?? (Math.cos(idx) * 50);

      const isRoot = (rootSvcId && (node.id === rootSvcId || node.name === rootSvcId));
      const isPath = propagationPath.some(p => p === node.name || p === node.id);
      
      let statusColor = COLOR_HEALTHY;
      let statusText = 'HEALTHY';

      if (isRoot) {
        statusColor = COLOR_FAILING;
        statusText = 'ROOT FAILURE';
      } else if (hasIncident && isPath) {
        statusColor = COLOR_DEGRADED;
        statusText = 'DEGRADED';
      } else if (node.color === 'red') {
        statusColor = COLOR_FAILING;
        statusText = 'FAILING';
      } else if (node.color === 'amb') {
        statusColor = COLOR_DEGRADED;
        statusText = 'DEGRADED';
      }

      // 1. Core Sphere / Faceted Node
      const nodeGeo = new THREE.IcosahedronGeometry(isRoot ? 16 : 13, 2);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: statusColor,
        emissive: statusColor,
        emissiveIntensity: isRoot ? 0.65 : 0.35,
        roughness: 0.25,
        metalness: 0.85
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.set(x, y, z);
      nodeMesh.userData = {
        ...node,
        computedStatus: statusText,
        colorHex: statusColor,
        isRoot,
        isPath
      };
      worldGroup.add(nodeMesh);
      nodeMeshes.push(nodeMesh);
      nodeMap.set(node.id || node.name, nodeMesh);

      // 2. Outer Wireframe Ring
      const ringGeo = new THREE.TorusGeometry(isRoot ? 22 : 18, 0.7, 8, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isRoot ? 0xff3d55 : COLOR_CYAN,
        wireframe: true,
        transparent: true,
        opacity: isRoot ? 0.8 : 0.4
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = Math.PI / 2;
      nodeMesh.add(ringMesh);
      nodeMesh.userData.ring = ringMesh;

      // 3. Shockwave Pulse ring for Root Cause Failure
      if (isRoot) {
        const pulseGeo = new THREE.RingGeometry(18, 20, 32);
        const pulseMat = new THREE.MeshBasicMaterial({
          color: 0xff3d55,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8
        });
        const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
        pulseMesh.rotation.x = Math.PI / 2;
        nodeMesh.add(pulseMesh);
        nodeMesh.userData.pulse = pulseMesh;
      }
    });

    // EDGES & PACKETS
    const edges = (graphData && graphData.edges && graphData.edges.length > 0)
      ? graphData.edges
      : DEFAULT_TOPOLOGY.edges;

    const dataPackets = [];

    edges.forEach((edge) => {
      const fromMesh = nodeMap.get(edge.from);
      const toMesh = nodeMap.get(edge.to);

      if (!fromMesh || !toMesh) return;

      const p1 = fromMesh.position;
      const p2 = toMesh.position;

      const isPathEdge = edge.is_path || (
        propagationPath.includes(fromMesh.userData.name) && 
        propagationPath.includes(toMesh.userData.name)
      );

      // Line Geometry
      const points = [p1, p2];
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: isPathEdge ? 0xff3d55 : 0x00d9ff,
        transparent: true,
        opacity: isPathEdge ? 0.85 : 0.28,
        linewidth: isPathEdge ? 2.5 : 1
      });
      const line = new THREE.Line(lineGeo, lineMat);
      worldGroup.add(line);

      // Animated traveling data packet along edge
      const packetGeo = new THREE.SphereGeometry(isPathEdge ? 2.8 : 1.8, 8, 8);
      const packetMat = new THREE.MeshBasicMaterial({
        color: isPathEdge ? 0xff5c72 : 0x00d9ff,
        transparent: true,
        opacity: 0.95
      });
      const packet = new THREE.Mesh(packetGeo, packetMat);
      worldGroup.add(packet);

      dataPackets.push({
        mesh: packet,
        p1,
        p2,
        progress: Math.random(),
        speed: (Math.random() * 0.005 + 0.006) * (isPathEdge ? 1.6 : 1.0)
      });
    });

    // INTERACTIVITY: Raycasting, Orbit & Pan
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-1000, -1000);

    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };
    let targetRotationY = 0;
    let targetRotationX = 0;
    let autoRotate = true;

    const onPointerDown = (e) => {
      isDragging = true;
      autoRotate = false;
      prevMouse = { x: e.clientX, y: e.clientY };
    };

    const onPointerMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isDragging) {
        const deltaX = e.clientX - prevMouse.x;
        const deltaY = e.clientY - prevMouse.y;
        targetRotationY += deltaX * 0.006;
        targetRotationX += deltaY * 0.006;
        targetRotationX = Math.max(-0.6, Math.min(0.6, targetRotationX));
        prevMouse = { x: e.clientX, y: e.clientY };
      }

      // Check hover on nodes
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const data = hit.userData;
        container.style.cursor = 'pointer';
        setTooltip({
          name: data.display || data.name,
          id: data.id,
          tier: data.tier || 'BACKEND',
          status: data.computedStatus,
          color: data.colorHex === COLOR_FAILING ? 'red' : data.colorHex === COLOR_DEGRADED ? 'amb' : 'grn',
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        container.style.cursor = isDragging ? 'grabbing' : 'grab';
        setTooltip(null);
      }
    };

    const onPointerUp = (e) => {
      if (isDragging) {
        const moveDist = Math.hypot(e.clientX - prevMouse.x, e.clientY - prevMouse.y);
        isDragging = false;

        // If it was a quick click, select node
        if (moveDist < 4) {
          raycaster.setFromCamera(mouse, camera);
          const intersects = raycaster.intersectObjects(nodeMeshes);
          if (intersects.length > 0) {
            const hit = intersects[0].object;
            setSelectedNodeId(hit.userData.id);
            if (onSelectNode) onSelectNode(hit.userData);
          }
        }
      }
    };

    const onWheel = (e) => {
      e.preventDefault();
      camera.position.z += e.deltaY * 0.3;
      camera.position.z = Math.max(220, Math.min(750, camera.position.z));
    };

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    container.addEventListener('wheel', onWheel, { passive: false });

    // CONTROLS EXPOSURE
    controlsRef.current.reset = () => {
      targetRotationX = 0;
      targetRotationY = 0;
      camera.position.set(0, 40, 460);
      autoRotate = true;
    };
    controlsRef.current.zoomIn = () => {
      camera.position.z = Math.max(220, camera.position.z - 60);
    };
    controlsRef.current.zoomOut = () => {
      camera.position.z = Math.min(750, camera.position.z + 60);
    };

    // ANIMATION LOOP
    let animId;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Idle auto-rotation
      if (autoRotate) {
        targetRotationY += 0.0018;
      }

      // Smooth interpolation for rotation
      worldGroup.rotation.y += (targetRotationY - worldGroup.rotation.y) * 0.08;
      worldGroup.rotation.x += (targetRotationX - worldGroup.rotation.x) * 0.08;

      // Pulse and rotate node rings
      nodeMeshes.forEach((mesh) => {
        if (mesh.userData.ring) {
          mesh.userData.ring.rotation.z += 0.015;
        }
        if (mesh.userData.pulse) {
          const s = 1 + (Math.sin(elapsed * 4) + 1) * 0.25;
          mesh.userData.pulse.scale.set(s, s, 1);
          mesh.userData.pulse.material.opacity = 0.8 - (s - 1) * 1.5;
        }
        // Floating motion
        mesh.position.y += Math.sin(elapsed * 2 + mesh.id) * 0.08;
      });

      // Advance data packets along edges
      dataPackets.forEach((pkt) => {
        pkt.progress += pkt.speed;
        if (pkt.progress > 1) pkt.progress = 0;
        pkt.mesh.position.lerpVectors(pkt.p1, pkt.p2, pkt.progress);
      });

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight || 420;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('wheel', onWheel);
      cancelAnimationFrame(animId);
      if (renderer && renderer.domElement) {
        renderer.dispose();
      }
    };
  }, [graphData, activeSim, hasIncident, rootSvcId]);

  return (
    <div style={{ position: 'relative', width: '100%', height, borderRadius: '14px', overflow: 'hidden' }}>
      {/* 3D WebGL Canvas Container */}
      <div 
        ref={containerRef} 
        style={{ width: '100%', height: '100%', outline: 'none' }} 
      />

      {/* Top HUD Overlay Header */}
      <div style={{
        position: 'absolute',
        top: '16px',
        left: '20px',
        right: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        pointerEvents: 'none'
      }}>
        <div style={{
          background: 'rgba(8, 15, 29, 0.75)',
          padding: '6px 14px',
          borderRadius: '8px',
          border: '1px solid rgba(0, 217, 255, 0.2)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: hasIncident ? 'var(--red)' : 'var(--green)',
            boxShadow: `0 0 10px ${hasIncident ? 'var(--red)' : 'var(--green)'}`
          }} />
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#FFFFFF', letterSpacing: '0.04em' }}>
            {title.toUpperCase()}
          </span>
          <span className="mono" style={{ fontSize: '11px', color: 'var(--cyan)' }}>
            [7 NODES · 8 EDGES]
          </span>
        </div>

        {/* Orbit / Zoom Controls */}
        <div style={{ display: 'flex', gap: '6px', pointerEvents: 'auto' }}>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.zoomIn && controlsRef.current.zoomIn()}
            title="Zoom In"
            style={{ padding: '6px', background: 'rgba(8, 15, 29, 0.85)' }}
          >
            <ZoomIn size={14} />
          </button>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.zoomOut && controlsRef.current.zoomOut()}
            title="Zoom Out"
            style={{ padding: '6px', background: 'rgba(8, 15, 29, 0.85)' }}
          >
            <ZoomOut size={14} />
          </button>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.reset && controlsRef.current.reset()}
            title="Reset Camera & Orbit"
            style={{ padding: '6px', background: 'rgba(8, 15, 29, 0.85)' }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Floating Hover Tooltip HUD */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: `${Math.min(tooltip.x + 15, containerRef.current.clientWidth - 200)}px`,
          top: `${Math.max(tooltip.y - 65, 10)}px`,
          background: 'rgba(11, 20, 36, 0.95)',
          border: '1px solid var(--cyan)',
          borderRadius: '8px',
          padding: '8px 12px',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6), 0 0 16px rgba(0, 217, 255, 0.3)',
          pointerEvents: 'none',
          backdropFilter: 'blur(12px)',
          zIndex: 20,
          minWidth: '160px'
        }}>
          <div style={{ fontWeight: 700, fontSize: '13px', color: '#FFFFFF', marginBottom: '2px' }}>
            {tooltip.name}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
            <span style={{ color: 'var(--text2)', textTransform: 'uppercase' }}>{tooltip.tier}</span>
            <span className={`b ${tooltip.color}`} style={{ padding: '1px 6px', fontSize: '10px' }}>
              {tooltip.status}
            </span>
          </div>
        </div>
      )}

      {/* Bottom Hint Banner */}
      <div style={{
        position: 'absolute',
        bottom: '12px',
        left: '20px',
        right: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        pointerEvents: 'none',
        fontSize: '11px',
        color: 'var(--text2)'
      }}>
        <span>Interactive 3D: Drag to orbit · Scroll to zoom · Click node to inspect</span>
        {hasIncident && (
          <span style={{ color: 'var(--red)', fontWeight: 600 }}>
             Pulsating Red: Active Fault Root Origin
          </span>
        )}
      </div>
    </div>
  );
}
