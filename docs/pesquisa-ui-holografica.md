# 🔬 Pesquisa: Interface Holográfica Cyberpunk — D3.js & Three.js

> **Projeto:** Atena Evolução  
> **Data:** 25/06/2026  
> **Objetivo:** Compilar técnicas, códigos de exemplo e referências para criar uma interface holográfica cyberpunk usando CSS, D3.js, Three.js e WebGL.

---

## Sumário

1. [Efeitos de Holograma](#1-efeitos-de-holograma)
2. [Paleta Cyberpunk](#2-paleta-cyberpunk)
3. [Animações de Dados em Tempo Real](#3-animações-de-dados-em-tempo-real)
4. [Tipografia Futurista](#4-tipografia-futurista)
5. [Componentes de UI Flutuantes](#5-componentes-de-ui-flutuantes)
6. [Arquitetura Recomendada](#6-arquitetura-recomendada)
7. [Referências](#7-referências)

---

## 1. Efeitos de Holograma

### 1.1 Glitch Effect (CSS)

Técnica de **aberração cromática** com pseudoelementos `::before` / `::after` e `clip-path` animado. Inspirado no **cybercore-css** (★57 GitHub).

```css
/* ── Glitch Heading ────────────────────────────────── */
.cyber-heading {
  position: relative;
  display: inline-block;
  color: var(--cyber-cyan-500);
  text-shadow:
    0 0 10px var(--cyber-cyan-500),
    0 0 20px color-mix(in srgb, var(--cyber-cyan-500) 60%, transparent);
}

.cyber-heading::before,
.cyber-heading::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 80%;
  will-change: transform, clip-path;
}

.cyber-heading::before {
  z-index: -1;
  color: var(--cyber-magenta-500);
  animation: glitch-1 8s infinite linear alternate-reverse;
}

.cyber-heading::after {
  z-index: -1;
  color: var(--cyber-cyan-300);
  animation: glitch-2 6s infinite linear alternate;
}

@keyframes glitch-1 {
  0%, 100% { transform: translate(-2px, 0); clip-path: inset(0 0 95% 0); }
  10%      { transform: translate(2px, 0);  clip-path: inset(30% 0 40% 0); }
  20%      { transform: translate(-1px, 0); clip-path: inset(70% 0 10% 0); }
  30%      { transform: translate(1px, 0);  clip-path: inset(10% 0 60% 0); }
  40%      { transform: translate(-2px, 0); clip-path: inset(80% 0 5% 0); }
  50%      { transform: translate(2px, 0);  clip-path: inset(20% 0 55% 0); }
  60%      { transform: translate(-1px, 0); clip-path: inset(50% 0 30% 0); }
  70%      { transform: translate(1px, 0);  clip-path: inset(5% 0 85% 0); }
}

@keyframes glitch-2 {
  0%, 100% { transform: translate(2px, 0);  clip-path: inset(95% 0 0 0); }
  15%      { transform: translate(-1px, 0); clip-path: inset(40% 0 30% 0); }
  35%      { transform: translate(1px, 0);  clip-path: inset(60% 0 20% 0); }
  55%      { transform: translate(-2px, 0); clip-path: inset(10% 0 70% 0); }
}
```

**Uso no HTML:**
```html
<h1 class="cyber-heading" data-text="ATENA">ATENA</h1>
```

### 1.2 Scanlines (CSS)

Overlay de **CRT monitor** com `repeating-linear-gradient` — 3 variantes: fine, heavy, flicker, scroll.

```css
/* ── Scanlines Effect ────────────────────────────────── */
.cyber-scanlines {
  position: relative;
}

.cyber-scanlines::after {
  content: "";
  position: absolute;
  z-index: 10;
  border-radius: inherit;
  background: repeating-linear-gradient(
    0deg,
    transparent 0,
    transparent 2px,
    rgb(0 0 0 / 50%) 2px,
    rgb(0 0 0 / 50%) 4px
  );
  pointer-events: none;
  inset: 0;
}

/* Variante: scanlines finas */
.cyber-scanlines--fine::after {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 1px,
    rgb(0 0 0 / 20%) 1px,
    rgb(0 0 0 / 20%) 2px
  );
}

/* Variante: scanlines animadas (scroll) */
.cyber-scanlines--scroll::after {
  animation: cyber-scanline-scroll 8s linear infinite;
}

@keyframes cyber-scanline-scroll {
  0%   { background-position: 0 0; }
  100% { background-position: 0 100vh; }
}

/* Variante: flicker */
.cyber-scanlines--flicker::after {
  animation: cyber-scanline-flicker 0.15s infinite;
}

@keyframes cyber-scanline-flicker {
  0%   { opacity: 0.8; }
  50%  { opacity: 0.6; }
  100% { opacity: 0.8; }
}
```

### 1.3 Glow / Neon Border (CSS)

Borda animada com **gradiente arco-íris + blur** — efeito neon cyberpunk.

```css
/* ── Neon Border Effect ────────────────────────────────── */
.cyber-neon-border {
  position: relative;
  isolation: isolate;
}

.cyber-neon-border::before {
  content: "";
  position: absolute;
  z-index: -1;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    var(--cyber-cyan-500, #00f0ff),
    var(--cyber-magenta-500, #ff2a6d),
    var(--cyber-yellow-500, #fcee0a),
    var(--cyber-green-500, #05ffa1),
    var(--cyber-cyan-500, #00f0ff)
  );
  background-size: 400% 100%;
  animation: neon-flow 4s linear infinite;
  filter: blur(15px);
  inset: 0;
}

.cyber-neon-border::after {
  content: "";
  position: absolute;
  z-index: -1;
  border-radius: inherit;
  background: var(--color-bg-secondary, #0d1117);
  inset: 0;
}

@keyframes neon-flow {
  0%   { background-position: 0% 50%; }
  100% { background-position: 400% 50%; }
}

/* Variante: apenas cyan */
.cyber-neon-border--cyan::before {
  background: linear-gradient(
    90deg,
    #33f3ff, #00c4cc, #00f0ff, #33f3ff
  );
  background-size: 400% 100%;
  animation: neon-flow 4s linear infinite;
  filter: blur(15px);
}
```

### 1.4 Partículas Holográficas (Three.js)

Sistema de partículas com **PointsMaterial** e animação por shader:

```javascript
// ── Holographic Particles ──────────────────────────────
import * as THREE from 'three';

const PARTICLE_COUNT = 5000;

// Geometria
const geometry = new THREE.BufferGeometry();
const positions = new Float32Array(PARTICLE_COUNT * 3);
const aSizes = new Float32Array(PARTICLE_COUNT);

for (let i = 0; i < PARTICLE_COUNT; i++) {
  positions[i * 3]     = (Math.random() - 0.5) * 10;   // x
  positions[i * 3 + 1] = (Math.random() - 0.5) * 10;   // y
  positions[i * 3 + 2] = (Math.random() - 0.5) * 10;   // z
  aSizes[i]             = Math.random() * 2.0 + 0.5;
}

geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geometry.setAttribute('aSize', new THREE.BufferAttribute(aSizes, 1));

// Material com shader customizado
const material = new THREE.ShaderMaterial({
  uniforms: {
    uTime:  { value: 0.0 },
    uColor: { value: new THREE.Color('#00f0ff') },
  },
  vertexShader: `
    uniform float uTime;
    attribute float aSize;
    varying float vAlpha;

    void main() {
      vec3 pos = position;
      pos.y += sin(uTime * 0.5 + position.x * 2.0) * 0.3;
      pos.x += cos(uTime * 0.3 + position.z * 1.5) * 0.2;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_PointSize = aSize * (200.0 / -mvPosition.z);
      gl_Position = projectionMatrix * mvPosition;

      // Fade com distância
      vAlpha = smoothstep(8.0, 2.0, length(pos));
    }
  `,
  fragmentShader: `
    uniform vec3 uColor;
    varying float vAlpha;

    void main() {
      // Circular soft particle
      float dist = length(gl_PointCoord - vec2(0.5));
      if (dist > 0.5) discard;
      float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
      gl_FragColor = vec4(uColor, alpha * vAlpha * 0.8);
    }
  `,
  transparent: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});

const particles = new THREE.Points(geometry, material);
scene.add(particles);

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  material.uniforms.uTime.value = clock.getElapsedTime();
  renderer.render(scene, camera);
}
```

### 1.5 GLSL Shaders Holográficos (Three.js)

Shaders **vertex + fragment** do projeto **HOLO.SYS** (YasirAwan4831):

#### Vertex Shader — Glitch Displacement

```glsl
uniform float uTime;
uniform float uProgress;
uniform float uMinY;
uniform float uMaxY;

varying vec3 vPosition;
varying vec3 vNormal;

float random(vec2 st) {
  return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

void main() {
  vec4 modelPosition = modelMatrix * vec4(position, 1.0);

  // ── Base Glitch Effect ──
  float glitchTime = uTime - modelPosition.y;
  float glitchStrength = sin(glitchTime)
                       * sin(glitchTime * 3.45)
                       + sin(glitchTime * 8.76);
  glitchStrength /= 3.0;
  glitchStrength  = smoothstep(0.5, 1.0, glitchStrength);
  glitchStrength *= 2.0;

  modelPosition.x += (random(modelPosition.xz + uTime) - 0.5) * glitchStrength;
  modelPosition.z += (random(modelPosition.xz + uTime) - 0.5) * glitchStrength;

  // ── Progress-Based Glitch (transition wave) ──
  float normalizedY    = (modelPosition.y - uMinY) / (uMaxY - uMinY);
  float diff           = abs(normalizedY - uProgress);
  float progressGlitch = smoothstep(0.02, 0.0, diff) * 0.3;

  modelPosition.x += (random(modelPosition.xz + uTime) - 0.5) * progressGlitch;
  modelPosition.z += (random(modelPosition.xz + uTime) - 0.5) * progressGlitch;

  gl_Position = projectionMatrix * viewMatrix * modelPosition;
  vPosition = modelPosition.xyz;
  vNormal = (modelMatrix * vec4(normal, 0.0)).xyz;
}
```

#### Fragment Shader — Scanlines + Fresnel Glow

```glsl
uniform float uTime;
uniform float uProgress;
uniform vec3  uColor;
uniform float uMinY;
uniform float uMaxY;

varying vec3 vPosition;
varying vec3 vNormal;

void main() {
  // ── Scan Line Effect ──
  float lines  = 20.0;
  float offset = vPosition.y - uTime * 0.2;
  float density = mod(offset * lines, 1.0);
  density = pow(density, 3.0);

  // ── Fresnel Rim Glow ──
  vec3  viewDirection = normalize(vPosition - cameraPosition);
  float fresnel       = 1.0 - abs(dot(normalize(vNormal), viewDirection));
  fresnel             = pow(fresnel, 2.0);

  // ── Fresnel Falloff ──
  float falloff = smoothstep(0.8, 0.0, fresnel);

  // ── Combine ──
  float holographic  = density * fresnel;
  holographic       += fresnel * 1.25;
  holographic       *= falloff;

  gl_FragColor = vec4(uColor, holographic);
}
```

### 1.6 Post-Processing Pipeline (Three.js)

Combinação de passes do **EffectComposer** para efeito holográfico completo:

```javascript
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }     from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { GlitchPass }     from 'three/addons/postprocessing/GlitchPass.js';
import { ShaderPass }     from 'three/addons/postprocessing/ShaderPass.js';
import { FilmPass }       from 'three/addons/postprocessing/FilmPass.js';
import { RGBShiftShader } from 'three/addons/shaders/RGBShiftShader.js';
import { OutputPass }     from 'three/addons/postprocessing/OutputPass.js';

// Setup
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

// 1) Unreal Bloom — glow neon
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  1.5,   // strength
  0.4,   // radius
  0.85   // threshold
);
composer.addPass(bloomPass);

// 2) Glitch — distorção digital esporádica
const glitchPass = new GlitchPass();
glitchPass.goWild = false; // glitch sutil, não constante
composer.addPass(glitchPass);

// 3) RGB Shift — aberração cromática
const rgbShiftPass = new ShaderPass(RGBShiftShader);
rgbShiftPass.uniforms['amount'].value = 0.003;
composer.addPass(rgbShiftPass);

// 4) Film — grain + scanlines
const filmPass = new FilmPass(0.35, false); // intensity, grayscale
composer.addPass(filmPass);

// 5) Output (tone mapping + encoding)
composer.addPass(new OutputPass());

// Render loop
function animate() {
  requestAnimationFrame(animate);
  composer.render();
}
```

**Tabela de Passes Disponíveis no Three.js:**

| Pass | Efeito | Uso Holográfico |
|------|--------|-----------------|
| `UnrealBloomPass` | Glow/bloom estilo Unreal | Brilho neon em bordas |
| `GlitchPass` | Distorção digital aleatória | Glitch esporádico |
| `FilmPass` | Grain + scanlines | Textura CRT |
| `RGBShiftShader` | Aberração cromática | Separar canais RGB |
| `AfterimagePass` | Rastro/ghosting | Persistência visual |
| `DotScreenPass` | Halftone dots | Efeito display retro |
| `OutlinePass` | Contorno luminoso | Highlight de objetos |

---

## 2. Paleta Cyberpunk

### 2.1 Definição de Cores (CSS Custom Properties)

```css
:root {
  /* ── Neon Core ── */
  --cyber-cyan-300:    #66f7ff;
  --cyber-cyan-400:    #33f3ff;
  --cyber-cyan-500:    #00f0ff;   /* ★ PRIMARY */
  --cyber-cyan-600:    #00c4cc;

  --cyber-magenta-300: #ff5c8a;
  --cyber-magenta-400: #ff3d76;
  --cyber-magenta-500: #ff2a6d;   /* ★ ACCENT */
  --cyber-magenta-600: #cc1557;

  --cyber-purple-300:  #c471ff;
  --cyber-purple-400:  #a855f7;
  --cyber-purple-500:  #8b2fc9;   /* ★ SECONDARY */
  --cyber-purple-600:  #6b21a8;

  /* ── Suporte ── */
  --cyber-yellow-500:  #fcee0a;   /* Warning/highlight */
  --cyber-green-500:   #05ffa1;   /* Success/active */
  --cyber-red-500:     #ff0040;   /* Critical/error */

  /* ── Backgrounds ── */
  --bg-primary:        #0a0a0f;   /* Quase preto */
  --bg-secondary:      #0d1117;   /* Card/panel */
  --bg-tertiary:       #161b22;   /* Surface elevada */
  --bg-grid:           rgba(0, 240, 255, 0.03); /* Grid sutil */

  /* ── Text ── */
  --text-primary:      #e0e0e8;
  --text-secondary:    #8b949e;
  --text-muted:        #484f58;

  /* ── Glow Intensities ── */
  --glow-sm:  0 0 5px;
  --glow-md:  0 0 10px, 0 0 20px;
  --glow-lg:  0 0 10px, 0 0 30px, 0 0 60px;
}
```

### 2.2 Classes de Glow Utilitárias

```css
.glow-cyan    { text-shadow: var(--glow-md) var(--cyber-cyan-500); }
.glow-magenta { text-shadow: var(--glow-md) var(--cyber-magenta-500); }
.glow-purple  { text-shadow: var(--glow-md) var(--cyber-purple-400); }

.box-glow-cyan    { box-shadow: var(--glow-md) var(--cyber-cyan-500); }
.box-glow-magenta { box-shadow: var(--glow-md) var(--cyber-magenta-500); }

.border-glow-cyan {
  border: 1px solid var(--cyber-cyan-500);
  box-shadow: inset 0 0 8px var(--cyber-cyan-500), 0 0 8px var(--cyber-cyan-500);
}
```

### 2.3 Three.js — Materiais com Paleta Cyberpunk

```javascript
// Neon emissive materials
const cyanMaterial = new THREE.MeshStandardMaterial({
  color: 0x00f0ff,
  emissive: 0x00f0ff,
  emissiveIntensity: 0.8,
  transparent: true,
  opacity: 0.9,
});

const magentaMaterial = new THREE.MeshStandardMaterial({
  color: 0xff2a6d,
  emissive: 0xff2a6d,
  emissiveIntensity: 0.6,
  transparent: true,
  opacity: 0.85,
});

// Wireframe holográfico
const holoWireframe = new THREE.MeshBasicMaterial({
  color: 0x00f0ff,
  wireframe: true,
  transparent: true,
  opacity: 0.4,
});

// Shader material com fresnel (borda brilhante, centro transparente)
const fresnelMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uColor: { value: new THREE.Color(0x00f0ff) },
    uTime:  { value: 0 },
  },
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vViewDir;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      vViewDir = normalize(-mvPos.xyz);
      gl_Position = projectionMatrix * mvPos;
    }
  `,
  fragmentShader: `
    uniform vec3 uColor;
    uniform float uTime;
    varying vec3 vNormal;
    varying vec3 vViewDir;
    void main() {
      float fresnel = pow(1.0 - abs(dot(vNormal, vViewDir)), 3.0);
      float scanline = 0.5 + 0.5 * sin(gl_FragCoord.y * 1.5 + uTime * 2.0);
      float alpha = fresnel * (0.7 + 0.3 * scanline);
      gl_FragColor = vec4(uColor, alpha);
    }
  `,
  transparent: true,
  side: THREE.DoubleSide,
  depthWrite: false,
});
```

---

## 3. Animações de Dados em Tempo Real

### 3.1 D3.js — Force Graph com Glow Neon

```javascript
import * as d3 from 'd3';

// ── Setup SVG com filtro SVG para glow ──
const svg = d3.select('#graph-container')
  .append('svg')
  .attr('width', width)
  .attr('height', height);

// Filtro SVG para glow neon
const defs = svg.append('defs');

const cyanGlow = defs.append('filter').attr('id', 'glow-cyan');
cyanGlow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
cyanGlow.append('feMerge').selectAll('feMergeNode')
  .data(['blur', 'SourceGraphic'])
  .join('feMergeNode')
  .attr('in', d => d);

const magentaGlow = defs.append('filter').attr('id', 'glow-magenta');
magentaGlow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
magentaGlow.append('feMerge').selectAll('feMergeNode')
  .data(['blur', 'SourceGraphic'])
  .join('feMergeNode')
  .attr('in', d => d);

// ── Force Simulation ──
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id).distance(80))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(30));

// ── Links ──
const link = svg.append('g')
  .selectAll('line')
  .data(links)
  .join('line')
  .attr('stroke', '#00f0ff')
  .attr('stroke-opacity', 0.3)
  .attr('stroke-width', 1);

// ── Nodes ──
const node = svg.append('g')
  .selectAll('circle')
  .data(nodes)
  .join('circle')
  .attr('r', d => d.size || 8)
  .attr('fill', d => d.type === 'core' ? '#00f0ff' : '#ff2a6d')
  .attr('filter', d => d.type === 'core' ? 'url(#glow-cyan)' : 'url(#glow-magenta)')
  .call(d3.drag()
    .on('start', dragStarted)
    .on('drag', dragged)
    .on('end', dragEnded));

simulation.on('tick', () => {
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);
  node
    .attr('cx', d => d.x)
    .attr('cy', d => d.y);
});
```

### 3.2 D3.js — Stream de Dados em Tempo Real

```javascript
// ── Real-time data stream com D3 ──
const MAX_POINTS = 60;
let dataStream = [];

const xScale = d3.scaleLinear().domain([0, MAX_POINTS - 1]).range([0, width]);
const yScale = d3.scaleLinear().domain([0, 100]).range([height, 0]);

const line = d3.line()
  .x((d, i) => xScale(i))
  .y(d => yScale(d))
  .curve(d3.curveCatmullRom.alpha(0.5)); // smooth curve

const path = svg.append('path')
  .attr('fill', 'none')
  .attr('stroke', '#00f0ff')
  .attr('stroke-width', 2)
  .attr('filter', 'url(#glow-cyan)');

// Área sob a curva (gradient fill)
const area = d3.area()
  .x((d, i) => xScale(i))
  .y0(height)
  .y1(d => yScale(d))
  .curve(d3.curveCatmullRom.alpha(0.5));

const areaGradient = defs.append('linearGradient')
  .attr('id', 'area-gradient')
  .attr('x1', '0%').attr('y1', '0%')
  .attr('x2', '0%').attr('y2', '100%');
areaGradient.append('stop').attr('offset', '0%').attr('stop-color', '#00f0ff').attr('stop-opacity', 0.3);
areaGradient.append('stop').attr('offset', '100%').attr('stop-color', '#00f0ff').attr('stop-opacity', 0.0);

const areaPath = svg.append('path')
  .attr('fill', 'url(#area-gradient)');

// WebSocket ou setInterval para dados
function updateData(newValue) {
  dataStream.push(newValue);
  if (dataStream.length > MAX_POINTS) dataStream.shift();

  path.attr('d', line(dataStream));
  areaPath.attr('d', area(dataStream));
}

// Exemplo: dados simulados
setInterval(() => {
  const val = 50 + 30 * Math.sin(Date.now() * 0.002) + Math.random() * 10;
  updateData(val);
}, 1000);
```

### 3.3 D3.js — Radial Pulse (Dados Circulares Holográficos)

```javascript
// ── Radial data pulse ──
const radialLine = d3.lineRadial()
  .angle((d, i) => (i / data.length) * 2 * Math.PI)
  .radius(d => rScale(d.value))
  .curve(d3.curveCardinalClosed.tension(0.5));

const radialPath = radialGroup.append('path')
  .attr('d', radialLine(data))
  .attr('fill', 'rgba(0, 240, 255, 0.05)')
  .attr('stroke', '#00f0ff')
  .attr('stroke-width', 1.5)
  .attr('filter', 'url(#glow-cyan)');

// Animação de pulse
function animatePulse() {
  data.forEach(d => {
    d.value = d.baseValue + Math.random() * d.variance;
  });
  radialPath
    .transition()
    .duration(800)
    .ease(d3.easeCubicInOut)
    .attr('d', radialLine(data));
}
setInterval(animatePulse, 1000);
```

### 3.4 Three.js — Data Particles 3D

```javascript
// ── 3D Data Points animados ──
class DataParticles {
  constructor(count, scene) {
    this.count = count;
    this.geometry = new THREE.BufferGeometry();
    this.positions = new Float32Array(count * 3);
    this.targetPositions = new Float32Array(count * 3);
    this.colors = new Float32Array(count * 3);

    const cyan = new THREE.Color('#00f0ff');
    const magenta = new THREE.Color('#ff2a6d');

    for (let i = 0; i < count; i++) {
      const color = Math.random() > 0.7 ? magenta : cyan;
      this.colors[i * 3]     = color.r;
      this.colors[i * 3 + 1] = color.g;
      this.colors[i * 3 + 2] = color.b;
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positions, 3));
    this.geometry.setAttribute('color', new THREE.BufferAttribute(this.colors, 3));

    this.material = new THREE.PointsMaterial({
      size: 0.08,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    this.mesh = new THREE.Points(this.geometry, this.material);
    scene.add(this.mesh);
  }

  // Interpolar posições suavemente (spring animation)
  update(dt) {
    const lerp_factor = 1 - Math.exp(-3 * dt);
    for (let i = 0; i < this.count * 3; i++) {
      this.positions[i] += (this.targetPositions[i] - this.positions[i]) * lerp_factor;
    }
    this.geometry.attributes.position.needsUpdate = true;
  }

  // Atualizar dados em tempo real (ex: do WebSocket)
  setData(dataPoints) {
    for (let i = 0; i < this.count; i++) {
      const dp = dataPoints[i] || { x: 0, y: 0, z: 0 };
      this.targetPositions[i * 3]     = dp.x;
      this.targetPositions[i * 3 + 1] = dp.y;
      this.targetPositions[i * 3 + 2] = dp.z;
    }
  }
}
```

---

## 4. Tipografia Futurista

### 4.1 Fontes Recomendadas

| Fonte | Estilo | Uso | URL |
|-------|--------|-----|-----|
| **Orbitron** | Geométrica/sci-fi | Headings, HUD | [Google Fonts](https://fonts.google.com/specimen/Orbitron) |
| **Rajdhani** | Tech/clean | Body, labels | [Google Fonts](https://fonts.google.com/specimen/Rajdhani) |
| **Exo 2** | Futurista legível | Data, UI text | [Google Fonts](https://fonts.google.com/specimen/Exo+2) |
| **Share Tech Mono** | Monospace tech | Code, números | [Google Fonts](https://fonts.google.com/specimen/Share+Tech+Mono) |
| **Audiowide** | Display/wide | Logos, titles | [Google Fonts](https://fonts.google.com/specimen/Audiowide) |
| **Cyberpunk** (custom) | Display punk | Hero text | [CDN](https://cdn.jsdelivr.net/npm/cyberpunk-font@1.0.0/) |

### 4.2 CSS Tipográfico Holográfico

```css
/* ── Font Imports ── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

/* ── Typography Scale ── */
.text-holo-h1 {
  font-family: 'Orbitron', sans-serif;
  font-weight: 900;
  font-size: clamp(2rem, 5vw, 4rem);
  color: var(--cyber-cyan-500);
  text-shadow:
    0 0 10px var(--cyber-cyan-500),
    0 0 30px var(--cyber-cyan-500),
    0 0 60px rgba(0, 240, 255, 0.3);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.text-holo-h2 {
  font-family: 'Orbitron', sans-serif;
  font-weight: 700;
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  color: var(--cyber-magenta-500);
  text-shadow:
    0 0 8px var(--cyber-magenta-500),
    0 0 20px rgba(255, 42, 109, 0.4);
  letter-spacing: 0.08em;
}

.text-holo-body {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 400;
  font-size: 1rem;
  color: var(--text-primary);
  letter-spacing: 0.02em;
  line-height: 1.6;
}

.text-holo-mono {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.875rem;
  color: var(--cyber-green-500);
  letter-spacing: 0.05em;
}

/* ── Typed/Efeito digitando ── */
.text-holo-typed {
  font-family: 'Share Tech Mono', monospace;
  color: var(--cyber-cyan-500);
  border-right: 2px solid var(--cyber-cyan-500);
  animation: blink-caret 0.75s step-end infinite;
  white-space: nowrap;
  overflow: hidden;
}

@keyframes blink-caret {
  0%, 100% { border-color: var(--cyber-cyan-500); }
  50%      { border-color: transparent; }
}
```

### 4.3 Canvas Text Rendering (Three.js)

Para texto 3D no espaço holográfico:

```javascript
import { FontLoader }   from 'three/addons/loaders/FontLoader.js';
import { TextGeometry }  from 'three/addons/geometries/TextGeometry.js';

// Ou mais simples: Canvas texture
function createTextSprite(text, options = {}) {
  const {
    fontSize = 48,
    fontFamily = 'Orbitron',
    color = '#00f0ff',
    backgroundColor = 'transparent',
  } = options;

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = 512;
  canvas.height = 128;

  ctx.font = `${fontSize}px ${fontFamily}`;
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(2, 0.5, 1);
  return sprite;
}

// CSS2DRenderer para HUD overlays (mais nítido que sprites)
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
document.body.appendChild(labelRenderer.domElement);

const hudLabel = new CSS2DObject(document.querySelector('.hud-panel'));
hudLabel.position.set(0, 2, 0);
scene.add(hudLabel);
```

---

## 5. Componentes de UI Flutuantes

### 5.1 Panel Flutuante Holográfico (CSS)

```css
/* ── Holographic Floating Panel ── */
.holo-panel {
  position: relative;
  background: linear-gradient(
    135deg,
    rgba(0, 240, 255, 0.05) 0%,
    rgba(13, 17, 23, 0.9) 50%,
    rgba(139, 47, 201, 0.05) 100%
  );
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 4px;
  backdrop-filter: blur(10px);
  padding: 1.5rem;
  animation: float 6s ease-in-out infinite, holographic-flicker 4s infinite;
  transform-style: preserve-3d;
  perspective: 1000px;
}

.holo-panel::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 4px;
  background: linear-gradient(90deg, #00f0ff, #ff2a6d, #8b2fc9, #00f0ff);
  background-size: 300% 100%;
  animation: border-flow 3s linear infinite;
  z-index: -1;
  opacity: 0.5;
  filter: blur(4px);
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotateX(0deg); }
  25%      { transform: translateY(-8px) rotateX(1deg); }
  50%      { transform: translateY(-4px) rotateX(0deg); }
  75%      { transform: translateY(-10px) rotateX(-1deg); }
}

@keyframes holographic-flicker {
  0%, 100% { opacity: 1; }
  92%      { opacity: 1; }
  93%      { opacity: 0.8; }
  94%      { opacity: 1; }
  96%      { opacity: 0.9; }
  97%      { opacity: 1; }
}

@keyframes border-flow {
  0%   { background-position: 0% 50%; }
  100% { background-position: 300% 50%; }
}
```

```html
<div class="holo-panel cyber-scanlines cyber-scanlines--fine">
  <h2 class="text-holo-h2">STATUS</h2>
  <div class="holo-data-row">
    <span class="text-holo-mono">CPU_LOAD</span>
    <span class="text-holo-mono glow-cyan">87.3%</span>
  </div>
</div>
```

### 5.2 HUD Circular (SVG + D3.js)

```javascript
// ── Circular HUD Gauge ──
function createHoloGauge(containerId, value, maxValue, label) {
  const width = 200, height = 200;
  const radius = 80;
  const thickness = 6;

  const svg = d3.select(`#${containerId}`)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const defs = svg.append('defs');
  const glow = defs.append('filter').attr('id', `glow-${containerId}`);
  glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
  glow.append('feMerge').selectAll('feMergeNode')
    .data(['blur', 'SourceGraphic'])
    .join('feMergeNode').attr('in', d => d);

  const g = svg.append('g')
    .attr('transform', `translate(${width/2}, ${height/2})`);

  // Background arc
  const arc = d3.arc()
    .innerRadius(radius - thickness)
    .outerRadius(radius)
    .startAngle(0);

  g.append('path')
    .datum({ endAngle: 2 * Math.PI })
    .attr('d', arc)
    .attr('fill', 'rgba(0, 240, 255, 0.1)');

  // Value arc
  const angle = (value / maxValue) * 2 * Math.PI;
  const foreground = g.append('path')
    .datum({ endAngle: 0 })
    .attr('d', arc)
    .attr('fill', '#00f0ff')
    .attr('filter', `url(#glow-${containerId})`);

  foreground.transition()
    .duration(1500)
    .attrTween('d', (d) => {
      const interpolate = d3.interpolate(d.endAngle, angle);
      return (t) => arc({ endAngle: interpolate(t) });
    });

  // Label
  g.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', '#00f0ff')
    .attr('font-family', 'Orbitron')
    .attr('font-size', '1.5rem')
    .text(label);

  return { svg, foreground, arc, g };
}
```

### 5.3 Three.js — Floating Holographic Card

```javascript
class HoloCard {
  constructor(text, position, scene) {
    this.group = new THREE.Group();

    // Plane com shader holográfico
    const geometry = new THREE.PlaneGeometry(2, 1.2, 32, 32);
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uTime:  { value: 0 },
        uColor: { value: new THREE.Color(0x00f0ff) },
      },
      vertexShader: `
        uniform float uTime;
        varying vec2 vUv;
        varying vec3 vPos;
        void main() {
          vUv = uv;
          vPos = position;
          vec3 pos = position;
          pos.z += sin(pos.x * 3.0 + uTime) * 0.02; // subtle wave
          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        varying vec2 vUv;
        varying vec3 vPos;
        void main() {
          // Scanline
          float scan = sin(vUv.y * 80.0 + uTime * 2.0) * 0.5 + 0.5;
          scan = pow(scan, 8.0);

          // Border glow
          float border = smoothstep(0.0, 0.05, vUv.x) * smoothstep(0.0, 0.05, 1.0 - vUv.x)
                       * smoothstep(0.0, 0.08, vUv.y) * smoothstep(0.0, 0.08, 1.0 - vUv.y);
          float edgeGlow = 1.0 - border;

          // Combine
          float alpha = 0.15 + scan * 0.05 + edgeGlow * 0.8;
          gl_FragColor = vec4(uColor, alpha);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    this.group.add(mesh);

    // CSS2DObject para texto nítido
    const labelDiv = document.createElement('div');
    labelDiv.className = 'holo-card-label';
    labelDiv.textContent = text;
    labelDiv.style.cssText = `
      font-family: Orbitron, sans-serif;
      color: #00f0ff;
      font-size: 14px;
      text-shadow: 0 0 8px #00f0ff;
      pointer-events: none;
    `;
    const label = new CSS2DObject(labelDiv);
    this.group.add(label);

    this.group.position.copy(position);
    scene.add(this.group);

    this.material = material;
  }

  update(time) {
    // Floating animation
    this.group.position.y += Math.sin(time * 0.5) * 0.001;
    this.group.rotation.y = Math.sin(time * 0.3) * 0.05;
    this.material.uniforms.uTime.value = time;
  }
}
```

### 5.4 Grid Holográfico de Fundo (Three.js)

```javascript
// ── Infinite Holographic Grid ──
const gridHelper = new THREE.GridHelper(100, 50, 0x00f0ff, 0x00f0ff);
gridHelper.material.opacity = 0.08;
gridHelper.material.transparent = true;
scene.add(gridHelper);

// Grid animado com shader (melhor visual)
const gridGeometry = new THREE.PlaneGeometry(100, 100, 100, 100);
const gridMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(0x00f0ff) },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vPos;
    void main() {
      vUv = uv;
      vPos = position;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform vec3 uColor;
    varying vec2 vUv;
    varying vec3 vPos;

    float grid(vec2 st, float res) {
      vec2 g = abs(fract(st * res) - 0.5);
      return 1.0 - smoothstep(0.0, 0.02, min(g.x, g.y));
    }

    void main() {
      // Perspective grid
      vec2 st = vPos.xz * 0.1;
      float g = grid(st, 1.0);
      g *= 0.15;

      // Fade com distância
      float dist = length(vPos.xz) * 0.02;
      float fade = exp(-dist * dist);

      // Pulse animation
      float pulse = 0.8 + 0.2 * sin(uTime * 0.5 - length(vPos.xz) * 0.2);

      gl_FragColor = vec4(uColor, g * fade * pulse);
    }
  `,
  transparent: true,
  side: THREE.DoubleSide,
  depthWrite: false,
});

const gridMesh = new THREE.Mesh(gridGeometry, gridMaterial);
gridMesh.rotation.x = -Math.PI / 2;
scene.add(gridMesh);
```

---

## 6. Arquitetura Recomendada

### 6.1 Stack para Atena Evolução

```
┌─────────────────────────────────────────────┐
│               BROWSER                        │
│                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Three.js │  │  D3.js   │  │   CSS      │ │
│  │ 3D Scene │  │ Data Viz │  │ HUD/Layout │ │
│  │ Particles│  │ Graphs   │  │ Effects    │ │
│  │ Shaders  │  │ Streams  │  │ Typography │ │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘ │
│       │              │              │         │
│  ┌────┴──────────────┴──────────────┴──────┐ │
│  │         EffectComposer                   │ │
│  │  Bloom → Glitch → RGBShift → Film      │ │
│  └────────────────┬───────────────────────┘ │
│                   │                          │
│  ┌────────────────┴───────────────────────┐ │
│  │          WebGL Canvas                   │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │       CSS2DRenderer (HUD overlay)      │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
         │
    WebSocket / SSE
         │
┌────────┴────────┐
│   DATA SOURCE    │
│  (Backend/API)  │
└──────────────────┘
```

### 6.2 Pipeline de Renderização

```javascript
// ── Main render pipeline ──
class HoloRenderer {
  constructor(container) {
    // Three.js core
    this.scene    = new THREE.Scene();
    this.camera   = new THREE.PerspectiveCamera(75, ...);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

    // CSS2D overlay
    this.labelRenderer = new CSS2DRenderer();

    // Post-processing
    this.composer = new EffectComposer(this.renderer);
    this.setupPostProcessing();

    // Layers
    this.gridLayer      = new HoloGrid(this.scene);
    this.particleLayer  = new DataParticles(3000, this.scene);
    this.cardLayer      = [];
    this.dataVizLayer   = null; // D3 SVG overlay
  }

  setupPostProcessing() {
    const { width, height } = this.renderer.getSize(new THREE.Vector2());

    this.composer.addPass(new RenderPass(this.scene, this.camera));

    this.bloom = new UnrealBloomPass(
      new THREE.Vector2(width, height), 1.2, 0.4, 0.85
    );
    this.composer.addPass(this.bloom);

    this.glitch = new GlitchPass();
    this.glitch.goWild = false;
    this.composer.addPass(this.glitch);

    this.rgbShift = new ShaderPass(RGBShiftShader);
    this.rgbShift.uniforms['amount'].value = 0.002;
    this.composer.addPass(this.rgbShift);

    this.composer.addPass(new OutputPass());
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    const time = this.clock.getElapsedTime();

    this.particleLayer.update(1/60);
    this.gridLayer.update(time);
    this.cardLayer.forEach(c => c.update(time));

    this.composer.render();
    this.labelRenderer.render(this.scene, this.camera);
  }
}
```

### 6.3 Integração D3.js + Three.js

```javascript
// ── Bridge: D3 data → Three.js 3D objects ──
class D3ThreeBridge {
  constructor(d3Svg, threeScene, camera) {
    this.svg = d3Svg;
    this.scene = threeScene;
    this.camera = camera;
    this.projection = d3.geoOrthographic(); // ou outro
  }

  // Converte coordenadas SVG 2D → posição 3D
  svgTo3D(x, y, z = 0) {
    // Normalizar para [-1, 1]
    const nx = (x / window.innerWidth) * 2 - 1;
    const ny = -(y / window.innerHeight) * 2 + 1;

    // Unproject para 3D world space
    const vec = new THREE.Vector3(nx, ny, 0.5);
    vec.unproject(this.camera);
    const dir = vec.sub(this.camera.position).normalize();
    const distance = -this.camera.position.z / dir.z;
    const pos = this.camera.position.clone().add(dir.multiplyScalar(distance));
    pos.z = z;
    return pos;
  }

  // Sincroniza nós D3 com objetos Three.js
  syncNodes(d3Nodes, threeObjects) {
    d3Nodes.each((d, i) => {
      if (threeObjects[i]) {
        const pos = this.svgTo3D(d.x, d.y);
        threeObjects[i].position.lerp(pos, 0.1); // smooth
      }
    });
  }
}
```

---

## 7. Referências

### Projetos GitHub

| Repo | Stars | Descrição |
|------|-------|-----------|
| [sebyx07/cybercore-css](https://github.com/sebyx07/cybercore-css) | ★57 | Framework CSS cyberpunk puro — glitch, neon, scanlines, terminal |
| [YasirAwan4831/holographic-shader-visualizer-three.Js](https://github.com/YasirAwan4831/holographic-shader-visualizer-three.Js) | ★2 | Visualizador 3D holográfico — GLSL shaders, GSAP, glitch, scanlines |
| [satiricalguru/Jarvis](https://github.com/satiricalguru/Jarvis) | ★5 | JARVIS AI com interface holográfica Three.js |
| [harsh-raj00/my-jarvis](https://github.com/harsh-raj00/my-jarvis) | ★3 | JARVIS holográfico — React + Three.js + FastAPI |
| [AnnieIsthar/Advance-hologram-shader-AAA](https://github.com/AnnieIsthar/Advance-hologram-shader-AAA) | ★13 | Shader Godot 4 com tint, scanlines, glitch |
| [Yagasaki7K/cypnk-ui](https://github.com/Yagasaki7K/cypnk-ui) | ★6 | Lib CSS inspirada em Cyberpunk 2077 |

### Three.js Post-Processing (Built-in)

| Pass/Shader | Arquivo | Uso |
|-------------|---------|-----|
| **UnrealBloomPass** | `postprocessing/UnrealBloomPass.js` | Glow neon |
| **GlitchPass** | `postprocessing/GlitchPass.js` | Distorção digital |
| **FilmPass** | `postprocessing/FilmPass.js` | Scanlines + grain |
| **RGBShiftShader** | `shaders/RGBShiftShader.js` | Aberração cromática |
| **DigitalGlitch** | `shaders/DigitalGlitch.js` | Glitch squares |
| **AfterimagePass** | `postprocessing/AfterimagePass.js` | Ghosting/persistência |
| **OutlinePass** | `postprocessing/OutlinePass.js` | Contorno luminoso |
| **SobelOperatorShader** | `shaders/SobelOperatorShader.js` | Edge detection |

### D3.js Gallery & Exemplos

| Recurso | URL | Relevância |
|---------|-----|------------|
| Force-Directed Graph | [observablehq.com/@d3/force-directed-graph](https://observablehq.com/@d3/force-directed-graph) | Rede de dados holográfica |
| Radial Area Chart | [observablehq.com/@d3/radial-area-chart](https://observablehq.com/@d3/radial-area-chart) | Pulse circular |
| Stream Graph | [observablehq.com/@d3/streamgraph](https://observablehq.com/@d3/streamgraph) | Data stream |
| Voronoi Labels | [observablehq.com/@d3/voronoi-labels](https://observablehq.com/@d3/voronoi-labels) | Diagram de dados |
| Dynamic SVG Filters | [developer.mozilla.org](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/filter) | Glow via SVG filter |

### CodePen — Inspiração Holográfica

| Efeito | Search Terms | Notas |
|--------|-------------|-------|
| Glitch Text | `codepen.io glitch text css` | clip-path + pseudo-elements |
| Hologram UI | `codepen.io hologram interface three.js` | HUD + scanner |
| Neon Buttons | `codepen.io cyberpunk button css` | Glowing borders |
| Scanlines | `codepen.io crt scanlines css` | repeating-linear-gradient |
| D3 Particles | `codepen.io d3 particle animation` | Force + glow |
| Three.js HUD | `codepen.io three.js hud overlay` | CSS2DRenderer |

### Fontes & Tipografia

| Fonte | Provedor | URL |
|-------|----------|-----|
| Orbitron | Google Fonts | [fonts.google.com/specimen/Orbitron](https://fonts.google.com/specimen/Orbitron) |
| Rajdhani | Google Fonts | [fonts.google.com/specimen/Rajdhani](https://fonts.google.com/specimen/Rajdhani) |
| Exo 2 | Google Fonts | [fonts.google.com/specimen/Exo+2](https://fonts.google.com/specimen/Exo+2) |
| Share Tech Mono | Google Fonts | [fonts.google.com/specimen/Share+Tech+Mono](https://fonts.google.com/specimen/Share+Tech+Mono) |
| Audiowide | Google Fonts | [fonts.google.com/specimen/Audiwide](https://fonts.google.com/specimen/Audiowide) |

### Artigos Técnicos

| Título | Autor | URL |
|--------|-------|-----|
| Building HOLO.SYS | Yasir Awan | [Dev.to](https://dev.to/yasirawan4831/building-holosys-a-futuristic-3d-holographic-visualization-system-with-react-threejs-glsl-oea) |
| Three.js Post-Processing Guide | Three.js Docs | [threejs.org/docs](https://threejs.org/docs/#api/en/renderers/WebGLRenderer) |
| D3 + Three.js Integration | Elijah Meeks | [medium.com/@Elijah_Meeks](https://medium.com/@Elijah_Meeks) |

---

## Checklist de Implementação para Atena

- [ ] **Setup base:** Three.js scene + EffectComposer + CSS2DRenderer
- [ ] **Post-processing:** UnrealBloomPass + GlitchPass + RGBShift
- [ ] **Paleta:** CSS custom properties com cores cyberpunk
- [ ] **Tipografia:** Import Orbitron + Rajdhani + Share Tech Mono
- [ ] **Efeitos CSS:** Glitch heading, scanlines, neon border
- [ ] **Grid 3D:** Holographic ground grid com shader
- [ ] **Partículas:** Sistema de partículas holográficas (5000+)
- [ ] **Data Viz D3:** Force graph com SVG glow filter
- [ ] **Data Stream:** Real-time line chart com D3
- [ ] **HUD Panels:** Floating holographic cards (CSS + Three.js)
- [ ] **Circular Gauges:** D3 arc gauges com glow
- [ ] **WebSocket:** Conexão real-time para atualização de dados
- [ ] **Responsive:** Layout adaptativo, mobile fallback
- [ ] **Performance:** LOD, frustum culling, instancing para partículas

---

> *"The future is holographic. Build it in the browser."* — HOLO.SYS
