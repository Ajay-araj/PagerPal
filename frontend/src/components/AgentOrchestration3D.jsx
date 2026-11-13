import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { RotateCcw, ZoomIn, ZoomOut, Sparkles, Brain, CheckCircle2, ShieldAlert, AlertTriangle } from 'lucide-react';

/**
 * 8 AI Agents as officially defined in PagerPal Branding and LangGraph Architecture:
 * 1. Supervisor (Top center)
 * 2. Triage (Top right)
 * 3. Causal RCA (Right)
 * 4. Evidence Verifier (Bottom right)
 * 5. Confidence Scorer (Bottom center/right)
 * 6. Remediation Agent (Bottom left)
 * 7. Comms Agent (Left)
 * 8. Investigator (Top left)
 */
export const AGENTS_SPEC = [
  {
    id: 'Supervisor',
    name: 'Supervisor',
    role: 'Coordinates & Manages',
    description: 'Autonomous planner and state machine director. Routes investigation phases and orchestrates agent workflows.',
    color: '#328BFF',
    glowColor: 0x328bff,
    angle: -Math.PI / 2, // Top
    tier: 'core',
    defaultStatus: 'Queued'
  },
  {
    id: 'Triage',
    name: 'Triage',
    role: 'Assesses Severity',
    description: 'Classifies incident severity, calculates customer blast radius, and gauges checkout orders at risk.',
    color: '#00D69A',
    glowColor: 0x00d69a,
    angle: -Math.PI / 4, // Top Right
    tier: 'assessment',
    defaultStatus: 'Queued'
  },
  {
    id: 'Causal RCA',
    name: 'Causal RCA',
    role: 'Finds Root Cause',
    description: 'Traverses NetworkX causal dependency DAG to identify root failure origins and eliminate downstream symptoms.',
    color: '#FFAE42',
    glowColor: 0xffae42,
    angle: 0, // Right
    tier: 'analysis',
    defaultStatus: 'Queued'
  },
  {
    id: 'Evidence Verifier',
    name: 'Evidence Verifier',
    role: 'Validates Findings',
    description: 'Validates diagnostic assertions against empirical telemetry metrics and logs. Drops uncorroborated claims.',
    color: '#00D9FF',
    glowColor: 0x00d9ff,
    angle: Math.PI / 4, // Bottom Right
    tier: 'verification',
    defaultStatus: 'Queued'
  },
  {
    id: 'Confidence Scorer',
    name: 'Confidence Scorer',
    role: 'Calculates Confidence',
    description: 'Computes deterministic rule-based diagnostic confidence index and evidence coverage ratio (strictly non-LLM).',
    color: '#FF3399',
    glowColor: 0xff3399,
    angle: Math.PI / 2, // Bottom
    tier: 'scoring',
    defaultStatus: 'Queued'
  },
  {
    id: 'Remediation',
    name: 'Remediation Agent',
    role: 'Proposes Fixes',
    description: 'Selects reversible operational fixes from allowlisted runbooks and verifies Policy Engine safety preconditions.',
    color: '#00BFFF',
    glowColor: 0x00bfff,
    angle: (3 * Math.PI) / 4, // Bottom Left
    tier: 'execution',
    defaultStatus: 'Queued'
  },
  {
    id: 'Comms',
    name: 'Comms Agent',
    role: 'Updates & Reports',
    description: 'Dispatches real-time notifications to team channels (Slack/Discord) and drafts comprehensive postmortem reports.',
    color: '#A855F7',
    glowColor: 0xa855f7,
    angle: Math.PI, // Left
    tier: 'communication',
    defaultStatus: 'Queued'
  },
  {
    id: 'Investigator',
    name: 'Investigator',
    role: 'Collects Evidence',
    description: 'Executes allowlisted diagnostic probes to collect telemetry, logs, traces, and recent canary deployments.',
    color: '#8B5CF6',
    glowColor: 0x8b5cf6,
    angle: (-3 * Math.PI) / 4, // Top Left
    tier: 'discovery',
    defaultStatus: 'Queued'
  }
];

export function AgentOrchestration3D({ 
  simData, 
  onSelectAgent, 
  selectedAgentId,
  height = '460px' 
}) {
  const containerRef = useRef(null);
  const [hoveredAgent, setHoveredAgent] = useState(null);
  const controlsRef = useRef({});

  // Compute live agent status dictionary from actual LangGraph simData
  const agentStatuses = useMemo(() => {
    const statuses = {};
    const stages = simData?.sim?.stages || [];
    
    // Default all to idle/waiting
    AGENTS_SPEC.forEach(a => {
      statuses[a.id] = {
        status: 'waiting',
        label: 'Idle / Queued',
        color: 'mu',
        result: '',
        timestamp: ''
      };
    });

    if (simData && simData.active && simData.sim) {
      stages.forEach(stg => {
        const id = stg.agent;
        if (statuses[id]) {
          statuses[id] = {
            status: stg.status, // 'waiting', 'running', 'completed', 'review', 'failed'
            label: stg.status === 'completed' ? 'Completed' : stg.status === 'running' ? 'Active / Executing' : stg.status === 'review' ? 'Needs Approval' : stg.status,
            color: stg.status === 'completed' ? 'grn' : stg.status === 'running' ? 'cy' : stg.status === 'review' ? 'amb' : stg.status === 'failed' ? 'red' : 'mu',
            result: stg.result || '',
            timestamp: stg.timestamp || ''
          };
        }
      });

      // Handle Confidence Scorer state
      const verifierDone = statuses['Evidence Verifier']?.status === 'completed';
      const isAwait = simData.sim.phase === 'await' || ['executing', 'verifying', 'resolved'].includes(simData.sim.phase);
      if (verifierDone || isAwait) {
        statuses['Confidence Scorer'] = {
          status: 'completed',
          label: 'Completed (86% Conf)',
          color: 'grn',
          result: 'Diagnostic confidence 86%, 5 of 6 claims corroborated',
          timestamp: 'Verified'
        };
      } else if (statuses['Evidence Verifier']?.status === 'running') {
        statuses['Confidence Scorer'] = {
          status: 'running',
          label: 'Calculating Score',
          color: 'cy',
          result: 'Awaiting evidence verification claims',
          timestamp: 'In Progress'
        };
      }
    }

    return statuses;
  }, [simData]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let renderer, animationId;
    let width = container.clientWidth;
    let heightPx = container.clientHeight || 460;

    // SCENE & CAMERA
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050505, 0.0016);

    const camera = new THREE.PerspectiveCamera(42, width / heightPx, 1, 2000);
    camera.position.set(0, 80, 480);

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch {
      return;
    }

    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x050505, 0);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // LIGHTING
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const mainCyanLight = new THREE.DirectionalLight(0x00d9ff, 1.4);
    mainCyanLight.position.set(150, 300, 200);
    scene.add(mainCyanLight);

    const goldAccentLight = new THREE.DirectionalLight(0xd6a15e, 0.9);
    goldAccentLight.position.set(-180, -150, -100);
    scene.add(goldAccentLight);

    const shieldPointLight = new THREE.PointLight(0x00d9ff, 2.2, 350);
    shieldPointLight.position.set(0, 10, 50);
    scene.add(shieldPointLight);

    // WORLD GROUP
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // CONCENTRIC FLOOR PEDESTAL & NEON ENERGY RINGS (matches official artwork)
    const floorRingsGroup = new THREE.Group();
    floorRingsGroup.position.y = -85;
    worldGroup.add(floorRingsGroup);

    // 1. Concentric Grid Mesh
    const gridHelper = new THREE.GridHelper(520, 24, 0x00d9ff, 0x181818);
    gridHelper.position.y = -86;
    gridHelper.material.opacity = 0.22;
    gridHelper.material.transparent = true;
    worldGroup.add(gridHelper);

    // 2. Glowing Neon Pedestal Disc
    const discGeo = new THREE.CylinderGeometry(85, 95, 4, 48);
    const discMat = new THREE.MeshStandardMaterial({
      color: 0x080f1d,
      roughness: 0.4,
      metalness: 0.8,
      emissive: 0x002244,
      emissiveIntensity: 0.5
    });
    const discMesh = new THREE.Mesh(discGeo, discMat);
    floorRingsGroup.add(discMesh);

    // 3. Concentric glowing rings on pedestal
    const ringRadii = [60, 85, 115, 150, 195];
    const ringColors = [0x00d9ff, 0x368bff, 0x00d69a, 0x9933ff, 0x00d9ff];
    ringRadii.forEach((r, idx) => {
      const ringGeo = new THREE.RingGeometry(r - 0.7, r + 0.7, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: ringColors[idx % ringColors.length],
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.45 - idx * 0.05
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 2.5;
      floorRingsGroup.add(ring);
    });

    // ==========================================
    // CENTRAL 3D PAGERPAL SHIELD (Official Logo)
    // ==========================================
    const shieldGroup = new THREE.Group();
    shieldGroup.position.set(0, 8, 0);
    worldGroup.add(shieldGroup);

    // Texture loader for official shield
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/branding/pagerpal-shield.png', (tex) => {
      tex.minFilter = THREE.LinearFilter;
      tex.generateMipmaps = false;

      // Shield Front Plate
      const shieldPlaneGeo = new THREE.PlaneGeometry(90, 92);
      const shieldPlaneMat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        side: THREE.DoubleSide,
        depthWrite: false
      });
      const shieldPlate = new THREE.Mesh(shieldPlaneGeo, shieldPlaneMat);
      shieldPlate.position.z = 2;
      shieldGroup.add(shieldPlate);

      // Backing Plate with metallic bevel
      const backPlateGeo = new THREE.PlaneGeometry(94, 96);
      const backPlateMat = new THREE.MeshStandardMaterial({
        color: 0x0a1424,
        metalness: 0.9,
        roughness: 0.2,
        emissive: 0x00d9ff,
        emissiveIntensity: 0.25,
        transparent: true,
        opacity: 0.8
      });
      const backPlate = new THREE.Mesh(backPlateGeo, backPlateMat);
      backPlate.position.z = -2;
      shieldGroup.add(backPlate);
    });

    // Subtle pulsating light inside shield
    const shieldCoreGlowGeo = new THREE.SphereGeometry(22, 24, 24);
    const shieldCoreGlowMat = new THREE.MeshBasicMaterial({
      color: 0x00d9ff,
      transparent: true,
      opacity: 0.25
    });
    const shieldCoreMesh = new THREE.Mesh(shieldCoreGlowGeo, shieldCoreGlowMat);
    shieldGroup.add(shieldCoreMesh);

    // ==========================================
    // 8 ORBITAL AGENT HOLOGRAPHIC 3D NODES
    // ==========================================
    const orbitRadiusX = 185;
    const orbitRadiusZ = 145;

    // Draw orbital ellipse track line
    const orbitCurve = new THREE.EllipseCurve(0, 0, orbitRadiusX, orbitRadiusZ, 0, 2 * Math.PI, false, 0);
    const orbitPoints = orbitCurve.getPoints(96);
    const orbitGeo = new THREE.BufferGeometry().setFromPoints(
      orbitPoints.map(p => new THREE.Vector3(p.x, 0, p.y))
    );
    const orbitMat = new THREE.LineBasicMaterial({
      color: 0x00d9ff,
      transparent: true,
      opacity: 0.28
    });
    const orbitLine = new THREE.Line(orbitGeo, orbitMat);
    orbitLine.position.y = 8;
    worldGroup.add(orbitLine);

    // Agent 3D Meshes Mapping
    const agentNodes = [];
    const agentMeshesMap = new Map();

    AGENTS_SPEC.forEach((spec) => {
      const x = Math.cos(spec.angle) * orbitRadiusX;
      const z = Math.sin(spec.angle) * orbitRadiusZ;
      const y = 8;

      const nodeGroup = new THREE.Group();
      nodeGroup.position.set(x, y, z);
      nodeGroup.userData = { spec, agentId: spec.id };

      // 1. Core Sphere
      const sphereGeo = new THREE.SphereGeometry(15, 32, 32);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(spec.color),
        metalness: 0.85,
        roughness: 0.25,
        emissive: new THREE.Color(spec.color),
        emissiveIntensity: 0.45
      });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      nodeGroup.add(sphere);

      // 2. Holographic Outer Glass Shell
      const shellGeo = new THREE.SphereGeometry(18.5, 24, 24);
      const shellMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.18,
        metalness: 0.1,
        roughness: 0.1,
        wireframe: true
      });
      const shell = new THREE.Mesh(shellGeo, shellMat);
      nodeGroup.add(shell);

      // 3. Orbiting Ring Around Node
      const ringGeo = new THREE.TorusGeometry(22, 0.9, 16, 48);
      const ringMat = new THREE.MeshBasicMaterial({
        color: spec.glowColor,
        transparent: true,
        opacity: 0.65
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 3;
      nodeGroup.add(ring);

      // 4. Expanding Pulse Wave Ring (for active/running state)
      const pulseGeo = new THREE.RingGeometry(18, 20, 32);
      const pulseMat = new THREE.MeshBasicMaterial({
        color: spec.glowColor,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0
      });
      const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
      pulseMesh.rotation.x = -Math.PI / 2;
      nodeGroup.add(pulseMesh);

      // 5. Floating Name Tag Sprite
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(5, 5, 5, 0.75)';
        ctx.roundRect(8, 8, 240, 48, 8);
        ctx.fill();
        ctx.strokeStyle = spec.color;
        ctx.lineWidth = 2;
        ctx.roundRect(8, 8, 240, 48, 8);
        ctx.stroke();

        ctx.font = 'bold 20px Sora, sans-serif';
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(spec.name, 128, 32);
      }
      const labelTex = new THREE.CanvasTexture(canvas);
      labelTex.minFilter = THREE.LinearFilter;
      const labelMat = new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthWrite: false });
      const labelSprite = new THREE.Sprite(labelMat);
      labelSprite.position.set(0, 32, 0);
      labelSprite.scale.set(48, 12, 1);
      nodeGroup.add(labelSprite);

      worldGroup.add(nodeGroup);
      agentNodes.push({ nodeGroup, sphere, shell, ring, pulseMesh, spec });
      agentMeshesMap.set(spec.id, { nodeGroup, sphere, shell, ring, pulseMesh, spec });
    });

    // ==========================================
    // MOVING ENERGY PHOTON PARTICLES
    // ==========================================
    const particleCount = 28;
    const particlesGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 2;
      particlePositions[i * 3] = Math.cos(angle) * orbitRadiusX;
      particlePositions[i * 3 + 1] = 8 + (Math.random() - 0.5) * 8;
      particlePositions[i * 3 + 2] = Math.sin(angle) * orbitRadiusZ;

      particleColors[i * 3] = 0.0;     // R
      particleColors[i * 3 + 1] = 0.85; // G
      particleColors[i * 3 + 2] = 1.0;  // B
    }

    particlesGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particlesGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const particlesMat = new THREE.PointsMaterial({
      size: 4.5,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });
    const photonParticles = new THREE.Points(particlesGeo, particlesMat);
    worldGroup.add(photonParticles);

    // ==========================================
    // INTERACTIVE CONTROLS & RAYCASTING
    // ==========================================
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-999, -999);
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let targetRotationY = 0;
    let targetRotationX = 0.18;
    let targetZoom = 480;

    controlsRef.current = {
      zoomIn: () => { targetZoom = Math.max(300, targetZoom - 60); },
      zoomOut: () => { targetZoom = Math.min(680, targetZoom + 60); },
      reset: () => {
        targetRotationY = 0;
        targetRotationX = 0.18;
        targetZoom = 480;
      }
    };

    const onPointerDown = (e) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onPointerMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isDragging) {
        const deltaX = e.clientX - prevMouseX;
        const deltaY = e.clientY - prevMouseY;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;

        targetRotationY += deltaX * 0.005;
        targetRotationX = Math.max(-0.25, Math.min(0.65, targetRotationX + deltaY * 0.003));
      }
    };

    const onPointerUp = (e) => {
      isDragging = false;
      // Handle click selection if not dragged
      const rect = container.getBoundingClientRect();
      const clickX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const clickY = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      
      raycaster.setFromCamera(new THREE.Vector2(clickX, clickY), camera);
      const interactables = agentNodes.map(n => n.sphere);
      const hits = raycaster.intersectObjects(interactables);
      if (hits.length > 0) {
        const hitGroup = hits[0].object.parent;
        if (hitGroup && hitGroup.userData?.spec) {
          if (onSelectAgent) {
            onSelectAgent(hitGroup.userData.spec);
          }
        }
      }
    };

    const onWheel = (e) => {
      e.preventDefault();
      targetZoom = Math.max(300, Math.min(680, targetZoom + e.deltaY * 0.4));
    };

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    container.addEventListener('wheel', onWheel, { passive: false });

    // ==========================================
    // RENDER / ANIMATION LOOP
    // ==========================================
    let clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth camera interpolation
      camera.position.z += (targetZoom - camera.position.z) * 0.08;
      worldGroup.rotation.y += (targetRotationY - worldGroup.rotation.y) * 0.08;
      worldGroup.rotation.x += (targetRotationX - worldGroup.rotation.x) * 0.08;

      // Central shield floating & lighting pulsation
      shieldGroup.position.y = 8 + Math.sin(elapsedTime * 1.6) * 5;
      shieldCoreMesh.scale.setScalar(1 + Math.sin(elapsedTime * 2.5) * 0.12);
      shieldPointLight.intensity = 2.0 + Math.sin(elapsedTime * 2.0) * 0.6;

      // Floor pedestal slow majestic rotation
      floorRingsGroup.rotation.y = elapsedTime * 0.08;

      // Update Agent Nodes & Status Animations
      agentNodes.forEach(({ nodeGroup, sphere, shell, ring, pulseMesh, spec }) => {
        // Subtle floating motion with offset phase
        nodeGroup.position.y = 8 + Math.sin(elapsedTime * 1.5 + spec.angle * 2) * 4;
        shell.rotation.y = elapsedTime * 0.4;
        shell.rotation.z = elapsedTime * 0.2;
        ring.rotation.z = elapsedTime * 0.6;

        // Check active status from prop dictionary
        const currentLiveStatus = agentStatuses[spec.id]?.status || 'waiting';
        const isSelected = selectedAgentId === spec.id;

        if (currentLiveStatus === 'running') {
          // Pulsing expansion wave
          const pulseScale = (elapsedTime * 1.8) % 1;
          pulseMesh.scale.setScalar(1 + pulseScale * 1.4);
          pulseMesh.material.opacity = Math.max(0, 0.8 - pulseScale * 0.8);
          sphere.material.emissiveIntensity = 0.8 + Math.sin(elapsedTime * 4.0) * 0.35;
        } else if (currentLiveStatus === 'review') {
          // Warning amber pulse
          pulseMesh.material.color.setHex(0xffaa36);
          sphere.material.emissive.setHex(0xffaa36);
          sphere.material.emissiveIntensity = 0.8 + Math.sin(elapsedTime * 5.0) * 0.4;
        } else if (currentLiveStatus === 'completed') {
          pulseMesh.material.opacity = 0;
          sphere.material.emissive.setHex(0x00d69a);
          sphere.material.emissiveIntensity = 0.6;
        } else {
          // Idle / waiting
          pulseMesh.material.opacity = 0;
          sphere.material.emissiveIntensity = isSelected ? 0.9 : 0.35;
        }

        // Selected node scale enhancement
        if (isSelected) {
          nodeGroup.scale.lerp(new THREE.Vector3(1.22, 1.22, 1.22), 0.1);
        } else {
          nodeGroup.scale.lerp(new THREE.Vector3(1.0, 1.0, 1.0), 0.1);
        }
      });

      // Animate Moving Energy Photons
      const positions = photonParticles.geometry.attributes.position.array;
      const speed = simData?.active ? 0.35 : 0.12;
      for (let i = 0; i < particleCount; i++) {
        let currentAngle = (i / particleCount) * Math.PI * 2 + elapsedTime * speed;
        positions[i * 3] = Math.cos(currentAngle) * orbitRadiusX;
        positions[i * 3 + 2] = Math.sin(currentAngle) * orbitRadiusZ;
      }
      photonParticles.geometry.attributes.position.needsUpdate = true;

      // Raycast for hover tooltip
      raycaster.setFromCamera(mouse, camera);
      const interactables = agentNodes.map(n => n.sphere);
      const intersects = raycaster.intersectObjects(interactables);

      if (intersects.length > 0) {
        const hitGroup = intersects[0].object.parent;
        if (hitGroup && hitGroup.userData?.spec) {
          const spec = hitGroup.userData.spec;
          const rect = container.getBoundingClientRect();
          setHoveredAgent({
            spec,
            x: ((mouse.x + 1) / 2) * rect.width,
            y: ((-mouse.y + 1) / 2) * rect.height,
            statusInfo: agentStatuses[spec.id] || { label: 'Idle / Queued', color: 'mu' }
          });
        }
      } else {
        setHoveredAgent(null);
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container || !renderer) return;
      width = container.clientWidth;
      heightPx = container.clientHeight || 460;
      camera.aspect = width / heightPx;
      camera.updateProjectionMatrix();
      renderer.setSize(width, heightPx);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('wheel', onWheel);
      if (renderer && renderer.domElement) {
        renderer.dispose();
      }
    };
  }, [agentStatuses, selectedAgentId, simData, onSelectAgent]);

  return (
    <div style={{ position: 'relative', width: '100%', height, borderRadius: '12px', overflow: 'hidden', background: 'var(--card)' }}>
      {/* 3D WebGL Canvas */}
      <div 
        ref={containerRef} 
        style={{ width: '100%', height: '100%', outline: 'none', cursor: 'grab' }} 
      />

      {/* Header Overlay HUD */}
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
          background: 'rgba(13, 13, 13, 0.88)',
          padding: '6px 14px',
          borderRadius: '8px',
          border: '1px solid var(--border)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Sparkles size={15} style={{ color: 'var(--cyan)' }} />
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', letterSpacing: '0.04em' }}>
            AUTONOMOUS AGENT ORCHESTRATION FABRIC
          </span>
          <span className="mono" style={{ fontSize: '11px', color: 'var(--cyan)' }}>
            [8 COLLABORATIVE AGENTS]
          </span>
        </div>

        {/* Orbit / Zoom Controls */}
        <div style={{ display: 'flex', gap: '6px', pointerEvents: 'auto' }}>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.zoomIn && controlsRef.current.zoomIn()}
            title="Zoom In"
            style={{ padding: '6px', background: 'var(--elevated)' }}
          >
            <ZoomIn size={14} />
          </button>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.zoomOut && controlsRef.current.zoomOut()}
            title="Zoom Out"
            style={{ padding: '6px', background: 'var(--elevated)' }}
          >
            <ZoomOut size={14} />
          </button>
          <button 
            className="btn" 
            onClick={() => controlsRef.current.reset && controlsRef.current.reset()}
            title="Reset Camera & Orbit"
            style={{ padding: '6px', background: 'var(--elevated)' }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Hover Tooltip HUD */}
      {hoveredAgent && (
        <div style={{
          position: 'absolute',
          left: `${Math.min(hoveredAgent.x + 15, (containerRef.current?.clientWidth || 600) - 220)}px`,
          top: `${Math.max(hoveredAgent.y - 75, 15)}px`,
          background: 'rgba(13, 13, 13, 0.95)',
          border: `1px solid ${hoveredAgent.spec.color}`,
          borderRadius: '8px',
          padding: '10px 14px',
          boxShadow: `0 8px 24px rgba(0, 0, 0, 0.8), 0 0 16px ${hoveredAgent.spec.color}44`,
          pointerEvents: 'none',
          backdropFilter: 'blur(12px)',
          zIndex: 20,
          minWidth: '190px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
            <b style={{ color: '#FFFFFF', fontSize: '13.5px' }}>{hoveredAgent.spec.name}</b>
            <span className={`b ${hoveredAgent.statusInfo.color}`} style={{ padding: '1px 6px', fontSize: '10px' }}>
              {hoveredAgent.statusInfo.label}
            </span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--cyan)', fontWeight: 600, marginBottom: '4px' }}>
            {hoveredAgent.spec.role}
          </div>
          <div style={{ fontSize: '11.5px', color: 'var(--text2)', lineHeight: 1.4 }}>
            {hoveredAgent.spec.description}
          </div>
          <div style={{ marginTop: '6px', fontSize: '10px', color: 'var(--text-muted)' }}>
            Click node to inspect execution details
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
        <span>Drag to orbit · Scroll to zoom · Click any AI agent node to inspect telemetry & findings</span>
        <span style={{ color: 'var(--cyan)', fontWeight: 600 }}>
          Central Shield: PagerPal Deterministic Safety & Policy Authority
        </span>
      </div>
    </div>
  );
}

