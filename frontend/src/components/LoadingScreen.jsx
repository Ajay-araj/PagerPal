import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

const INITIALIZATION_STEPS = [
  { threshold: 0, text: 'INITIALIZING PAGERPAL' },
  { threshold: 18, text: 'LOADING AI AGENTS' },
  { threshold: 38, text: 'CONNECTING SIMULATION ENGINE' },
  { threshold: 58, text: 'INITIALIZING SERVICE TOPOLOGY' },
  { threshold: 78, text: 'VERIFYING SYSTEM STATUS' },
  { threshold: 92, text: 'PREPARING DASHBOARD' },
  { threshold: 100, text: 'SYSTEM READY' }
];

export function LoadingScreen({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('INITIALIZING PAGERPAL');
  const [isFadingOut, setIsFadingOut] = useState(false);
  const canvasContainerRef = useRef(null);

  // 1. Progress Animation Simulation synced with real initialization
  useEffect(() => {
    let current = 0;
    const interval = setInterval(() => {
      // Smooth non-linear progress
      const increment = current < 30 ? 2.5 : current < 70 ? 1.8 : current < 90 ? 1.2 : 2.0;
      current = Math.min(100, current + increment);
      setProgress(Math.floor(current));

      // Update status message
      const matchedStep = [...INITIALIZATION_STEPS]
        .reverse()
        .find((s) => current >= s.threshold);
      if (matchedStep) {
        setStatusText(matchedStep.text);
      }

      if (current >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          setIsFadingOut(true);
          setTimeout(() => {
            if (onComplete) onComplete();
          }, 700);
        }, 400);
      }
    }, 45);

    return () => clearInterval(interval);
  }, [onComplete]);

  // 2. Three.js Floating 3D Geometric Objects Overlay
  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.z = 180;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      return;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Subtle ambient & directional lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const goldLight = new THREE.DirectionalLight(0xffd700, 1.5);
    goldLight.position.set(100, 80, 50);
    scene.add(goldLight);

    const cyanLight = new THREE.DirectionalLight(0x00d9ff, 1.2);
    cyanLight.position.set(-100, -60, 50);
    scene.add(cyanLight);

    // Group for objects floating AROUND the central sphere composition
    const objectsGroup = new THREE.Group();
    scene.add(objectsGroup);

    const floatingItems = [];

    // Metallic Gold Material
    const goldMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.9,
      roughness: 0.2,
      emissive: 0x3a2e0a,
      emissiveIntensity: 0.2
    });

    // Dark Chrome / Metallic Silver Material
    const chromeMaterial = new THREE.MeshStandardMaterial({
      color: 0x8892a0,
      metalness: 0.95,
      roughness: 0.15
    });

    // Glass / Translucent Material
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      metalness: 0.1,
      roughness: 0.1,
      transparent: true,
      opacity: 0.45,
      transmission: 0.85,
      ior: 1.5
    });

    // Wireframe Cyan & Gold Materials
    const cyanWireframe = new THREE.MeshBasicMaterial({
      color: 0x00d9ff,
      wireframe: true,
      transparent: true,
      opacity: 0.45
    });

    const goldWireframe = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      wireframe: true,
      transparent: true,
      opacity: 0.4
    });

    // Definitions of floating elements distributed around periphery
    const elementConfigs = [
      // Top Left quadrant
      { type: 'cube', mat: goldMaterial, size: 7, pos: [-75, 45, -10], rotSpeed: [0.01, 0.015, 0] },
      { type: 'ring', mat: goldWireframe, size: [12, 0.4, 16], pos: [-65, 30, 15], rotSpeed: [0.012, 0.008, 0.005] },
      { type: 'poly', mat: cyanWireframe, size: 8, pos: [-85, 10, -20], rotSpeed: [0.006, 0.012, 0.008] },
      { type: 'sphere', mat: glassMaterial, size: 5, pos: [-50, 55, 10], rotSpeed: [0.005, 0.005, 0] },

      // Top Right quadrant
      { type: 'cube', mat: chromeMaterial, size: 6, pos: [70, 50, -15], rotSpeed: [0.015, 0.008, 0.01] },
      { type: 'ring', mat: cyanWireframe, size: [14, 0.4, 20], pos: [80, 25, 10], rotSpeed: [0.007, 0.015, 0.01] },
      { type: 'poly', mat: goldWireframe, size: 7, pos: [60, 40, 25], rotSpeed: [0.01, 0.01, 0.01] },
      { type: 'sphere', mat: glassMaterial, size: 6, pos: [85, 5, -10], rotSpeed: [0.004, 0.008, 0] },

      // Bottom Left & Right outer areas (avoiding central floor reflection)
      { type: 'cube', mat: goldMaterial, size: 5, pos: [-80, -35, 5], rotSpeed: [0.008, 0.012, 0] },
      { type: 'ring', mat: goldWireframe, size: [10, 0.35, 16], pos: [-65, -45, -10], rotSpeed: [0.005, 0.01, 0.015] },
      { type: 'poly', mat: cyanWireframe, size: 6, pos: [75, -35, 10], rotSpeed: [0.012, 0.007, 0.005] },
      { type: 'sphere', mat: glassMaterial, size: 4.5, pos: [65, -45, -5], rotSpeed: [0.006, 0.006, 0] }
    ];

    elementConfigs.forEach((cfg, idx) => {
      let mesh;
      if (cfg.type === 'cube') {
        mesh = new THREE.Mesh(new THREE.BoxGeometry(cfg.size, cfg.size, cfg.size), cfg.mat);
      } else if (cfg.type === 'sphere') {
        mesh = new THREE.Mesh(new THREE.SphereGeometry(cfg.size, 24, 24), cfg.mat);
      } else if (cfg.type === 'ring') {
        mesh = new THREE.Mesh(new THREE.TorusGeometry(cfg.size[0], cfg.size[1], 8, cfg.size[2]), cfg.mat);
      } else if (cfg.type === 'poly') {
        mesh = new THREE.Mesh(new THREE.IcosahedronGeometry(cfg.size, 1), cfg.mat);
      }

      if (mesh) {
        mesh.position.set(cfg.pos[0], cfg.pos[1], cfg.pos[2]);
        objectsGroup.add(mesh);
        floatingItems.push({
          mesh,
          baseY: cfg.pos[1],
          rotSpeed: cfg.rotSpeed,
          floatOffset: idx * 0.7,
          floatSpeed: 0.8 + (idx % 4) * 0.25
        });
      }
    });

    // Small glowing cyan and golden particles
    const particleCount = 45;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      // Distribute in a spherical halo around periphery
      const radius = 60 + Math.random() * 55;
      const theta = Math.random() * Math.PI * 2;
      const phi = (Math.random() - 0.5) * Math.PI * 0.8;

      positions[i * 3] = radius * Math.cos(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi);
      positions[i * 3 + 2] = radius * Math.cos(phi) * Math.sin(theta);

      // Gold vs Cyan particle color distribution
      const isGold = Math.random() > 0.45;
      if (isGold) {
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.84;
        colors[i * 3 + 2] = 0.3;
      } else {
        colors[i * 3] = 0.0;
        colors[i * 3 + 1] = 0.85;
        colors[i * 3 + 2] = 1.0;
      }
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 2.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    objectsGroup.add(particles);

    // Animation Loop
    let animId;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Independent rotation and gentle floating for elements
      floatingItems.forEach((item) => {
        item.mesh.rotation.x += item.rotSpeed[0];
        item.mesh.rotation.y += item.rotSpeed[1];
        item.mesh.rotation.z += item.rotSpeed[2];
        item.mesh.position.y = item.baseY + Math.sin(elapsed * item.floatSpeed + item.floatOffset) * 3.5;
      });

      // Very slow drift of background particle cloud
      particles.rotation.y = elapsed * 0.04;
      particles.rotation.z = Math.sin(elapsed * 0.02) * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!renderer) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
      if (renderer && renderer.domElement) {
        renderer.dispose();
      }
    };
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: `url('/loading-bg.png') center center / cover no-repeat fixed #000000`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '48px 24px 60px',
        overflow: 'hidden',
        opacity: isFadingOut ? 0 : 1,
        transition: 'opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1)',
        pointerEvents: isFadingOut ? 'none' : 'auto'
      }}
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      {/* Three.js 3D Floating Geometry Overlay Canvas */}
      <div
        ref={canvasContainerRef}
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 1
        }}
      />

      {/* Top Section: PagerPal Branding */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          textAlign: 'center',
          animation: 'fadeInDown 0.8s ease-out'
        }}
      >
        <h1
          style={{
            fontFamily: "'Space Grotesk', 'Inter', sans-serif",
            fontSize: '28px',
            fontWeight: 700,
            letterSpacing: '0.24em',
            color: '#FFFFFF',
            margin: '0 0 6px 0',
            textShadow: '0 0 24px rgba(255, 255, 255, 0.35)'
          }}
        >
          PAGERPAL
        </h1>
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.28em',
            color: 'rgba(234, 243, 255, 0.75)',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px'
          }}
        >
          <span style={{ color: '#d4af37' }}>✦</span>
          <span>AUTONOMOUS INCIDENT RESPONSE</span>
          <span style={{ color: '#00d9ff' }}>✦</span>
        </div>
      </div>

      {/* Center Spacer: Let the Black Sphere with Golden Ring remain the hero visual */}
      <div style={{ flex: 1 }} />

      {/* Bottom Section: Large Animated Percentage, Progress Bar & System Messages */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          width: '100%',
          maxWidth: '460px',
          animation: 'fadeInUp 0.8s ease-out'
        }}
      >
        {/* Large Animated Percentage */}
        <div
          style={{
            fontFamily: "'Space Grotesk', 'JetBrains Mono', monospace",
            fontSize: '56px',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: '#FFFFFF',
            lineHeight: 1,
            marginBottom: '18px',
            textShadow: '0 0 30px rgba(212, 175, 55, 0.45), 0 0 15px rgba(255, 255, 255, 0.6)'
          }}
        >
          {String(progress).padStart(2, '0')}%
        </div>

        {/* Thin Elegant Progress Bar */}
        <div
          style={{
            width: '100%',
            height: '2px',
            background: 'rgba(255, 255, 255, 0.12)',
            borderRadius: '99px',
            overflow: 'hidden',
            position: 'relative',
            marginBottom: '16px'
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #00d9ff 0%, #ffd700 50%, #ffffff 100%)',
              boxShadow: '0 0 12px rgba(255, 215, 0, 0.8), 0 0 20px rgba(0, 217, 255, 0.6)',
              transition: 'width 0.1s linear'
            }}
          />
        </div>

        {/* Current Initialization Message */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            fontSize: '11px',
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: '0.12em',
            color: 'rgba(234, 243, 255, 0.75)'
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: progress >= 100 ? '#00e6a0' : '#ffd700',
                boxShadow: `0 0 8px ${progress >= 100 ? '#00e6a0' : '#ffd700'}`
              }}
            />
            {statusText}
          </span>
          <span style={{ color: 'rgba(234, 243, 255, 0.45)' }}>
            [V2.4.0 · SIMULATION]
          </span>
        </div>
      </div>
    </div>
  );
}
