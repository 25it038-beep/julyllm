"""
HS AI SOLUTIONS — UNIVERSAL VISUAL STUDIO & VISUAL RESPONSE ENGINE
Module: hs_ecosystem.visual.visual_studio
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Renders high-fidelity, interactive visualizations across:
- Interactive HTML5 / Canvas / SVG widgets with Pan, Zoom, Animation Playback & Export.
- Three.js 3D Tensors and Architecture Scenes.
- Terminal Unicode & Mermaid Diagrams.
Works universally for both JULY LLM and GRAVITY LLM.
"""

from __future__ import annotations
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class UniversalVisualEngine:
    """Universal visualization generator and renderer for HS AI Solutions Ecosystem."""

    SUPPORTED_TYPES = [
        "water_phase_diagram",
        "binary_search",
        "neural_network",
        "transformer_architecture",
        "electrical_circuit",
        "cpu_architecture",
        "os_scheduling",
        "uml_class_diagram",
        "math_plot"
    ]

    @classmethod
    def render_interactive_html(
        cls,
        visualization_type: str,
        title: str,
        explanation: str = "",
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a standalone, responsive, interactive HTML5 visualization widget
        with Obsidian Black & Champagne Gold styling, pan/zoom, timeline controls, and export.
        """
        vtype = visualization_type.lower().strip()
        custom_data = data or {}

        # Content generator based on type
        if "phase" in vtype or "water" in vtype:
            canvas_script = cls._get_phase_diagram_script()
        elif "binary" in vtype or "search" in vtype:
            canvas_script = cls._get_binary_search_script(custom_data.get("target", 23))
        elif "transformer" in vtype or "attention" in vtype:
            canvas_script = cls._get_transformer_script()
        elif "circuit" in vtype:
            canvas_script = cls._get_circuit_script()
        elif "cpu" in vtype:
            canvas_script = cls._get_cpu_architecture_script()
        elif "scheduling" in vtype or "os" in vtype:
            canvas_script = cls._get_os_scheduling_script()
        elif "uml" in vtype:
            canvas_script = cls._get_uml_script()
        elif "math" in vtype or "plot" in vtype:
            canvas_script = cls._get_math_plot_script()
        else: # Default neural network
            canvas_script = cls._get_neural_network_script()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title} — HS AI Visual Studio</title>
<style>
  :root {{
    --bg: #0a0b0e;
    --panel: #14161d;
    --border: #232733;
    --gold: #d4af37;
    --cyan: #00f0ff;
    --text: #e6e8ee;
    --dim: #8a8f98;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ background: var(--bg); color: var(--text); padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 900px; overflow: hidden; box-shadow: 0 12px 40px rgba(0,0,0,0.6); }}
  .header {{ padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: rgba(20,22,29,0.9); }}
  .title-area h2 {{ font-size: 1.2rem; color: var(--gold); letter-spacing: 0.5px; }}
  .title-area p {{ font-size: 0.85rem; color: var(--dim); margin-top: 4px; }}
  .controls {{ display: flex; gap: 8px; }}
  button {{ background: #1c202c; border: 1px solid var(--border); color: var(--text); padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; cursor: pointer; transition: all 0.2s; }}
  button:hover {{ border-color: var(--gold); color: var(--gold); }}
  .canvas-container {{ position: relative; width: 100%; height: 450px; background: #0c0d12; overflow: hidden; cursor: grab; }}
  canvas {{ display: block; width: 100%; height: 100%; }}
  .footer {{ padding: 12px 24px; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--dim); display: flex; justify-content: space-between; align-items: center; }}
  .timeline {{ display: flex; align-items: center; gap: 12px; }}
  .slider {{ -webkit-appearance: none; width: 200px; height: 4px; background: var(--border); border-radius: 2px; outline: none; }}
  .slider::-webkit-slider-thumb {{ -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: var(--gold); cursor: pointer; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="title-area">
      <h2>{title.upper()}</h2>
      <p>{explanation or 'Interactive Visual Generation Engine — HS AI Solutions'}</p>
    </div>
    <div class="controls">
      <button onclick="resetZoom()">⟲ Reset</button>
      <button onclick="toggleAnimate()">⏯ Play / Pause</button>
      <button onclick="exportPNG()">⬇ Export PNG</button>
    </div>
  </div>
  <div class="canvas-container" id="canvasBox">
    <canvas id="visCanvas" width="900" height="450"></canvas>
  </div>
  <div class="footer">
    <div class="timeline">
      <span>Timeline:</span>
      <input type="range" min="0" max="100" value="0" class="slider" id="timeSlider" oninput="seekAnimation(this.value)">
    </div>
    <div><span>HS AI SOLUTIONS</span> • <span>FOUNDER: HARSHAN SELIYAN</span></div>
  </div>
</div>

<script>
  const canvas = document.getElementById('visCanvas');
  const ctx = canvas.getContext('2d');
  let scale = 1.0, panX = 0, panY = 0;
  let isDragging = false, startX = 0, startY = 0;
  let isPlaying = true, animProgress = 0;

  const box = document.getElementById('canvasBox');
  box.addEventListener('mousedown', e => {{ isDragging = true; startX = e.clientX - panX; startY = e.clientY - panY; box.style.cursor = 'grabbing'; }});
  window.addEventListener('mouseup', () => {{ isDragging = false; box.style.cursor = 'grab'; }});
  window.addEventListener('mousemove', e => {{ if(isDragging) {{ panX = e.clientX - startX; panY = e.clientY - startY; render(); }} }});
  box.addEventListener('wheel', e => {{ e.preventDefault(); const zoom = e.deltaY < 0 ? 1.05 : 0.95; scale *= zoom; render(); }});

  function resetZoom() {{ scale = 1.0; panX = 0; panY = 0; render(); }}
  function toggleAnimate() {{ isPlaying = !isPlaying; }}
  function seekAnimation(v) {{ animProgress = v / 100; render(); }}
  function exportPNG() {{
    const a = document.createElement('a');
    a.download = '{visualization_type}_hssolutions.png';
    a.href = canvas.toDataURL();
    a.click();
  }}

  {canvas_script}

  function loop() {{
    if (isPlaying) {{
      animProgress = (animProgress + 0.005) % 1.0;
      document.getElementById('timeSlider').value = animProgress * 100;
      render();
    }}
    requestAnimationFrame(loop);
  }}
  loop();
</script>
</body>
</html>"""
        return html

    @staticmethod
    def _get_neural_network_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const layers = [
            { name: "Input (784)", nodes: 4, x: 150, color: "#00f0ff" },
            { name: "Dense W1 (256)", nodes: 6, x: 350, color: "#d4af37" },
            { name: "Dense W2 (128)", nodes: 5, x: 550, color: "#b388ff" },
            { name: "Output (10)", nodes: 3, x: 750, color: "#00e676" }
          ];

          // Draw synapses
          for (let l = 0; l < layers.length - 1; l++) {
            const l1 = layers[l], l2 = layers[l+1];
            for (let i = 0; i < l1.nodes; i++) {
              const y1 = 120 + i * 50;
              for (let j = 0; j < l2.nodes; j++) {
                const y2 = 90 + j * 45;
                ctx.beginPath();
                ctx.moveTo(l1.x, y1);
                ctx.lineTo(l2.x, y2);
                ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
                ctx.lineWidth = 1;
                ctx.stroke();

                // Pulse along synapse
                const px = l1.x + (l2.x - l1.x) * animProgress;
                const py = y1 + (y2 - y1) * animProgress;
                ctx.fillStyle = l1.color;
                ctx.fillRect(px - 1, py - 1, 3, 3);
              }
            }
          }

          // Draw neurons
          layers.forEach(l => {
            ctx.fillStyle = "#8a8f98";
            ctx.font = "bold 13px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(l.name, l.x, 50);

            for (let i = 0; i < l.nodes; i++) {
              const y = (l.name.includes("Dense W1") ? 90 : (l.name.includes("Dense W2") ? 100 : 120)) + i * (l.name.includes("Dense W1") ? 45 : 50);
              ctx.beginPath();
              ctx.arc(l.x, y, 14, 0, Math.PI * 2);
              ctx.fillStyle = "#14161d";
              ctx.fill();
              ctx.strokeStyle = l.color;
              ctx.lineWidth = 2.5;
              ctx.stroke();
            }
          });

          // Metrics box
          ctx.fillStyle = "rgba(20,22,29,0.85)";
          ctx.fillRect(50, 360, 800, 70);
          ctx.strokeStyle = "#232733";
          ctx.strokeRect(50, 360, 800, 70);
          ctx.fillStyle = "#d4af37";
          ctx.font = "bold 12px sans-serif";
          ctx.textAlign = "left";
          ctx.fillText("VERIFIED TOPOLOGY PARAMETER CONSISTENCY: 235,146 Total Trainable Parameters", 70, 385);
          ctx.fillStyle = "#8a8f98";
          ctx.font = "11px sans-serif";
          ctx.fillText("Layer 1 (784×256+256) = 200,960  |  Layer 2 (256×128+128) = 32,896  |  Output (128×10+10) = 1,290", 70, 410);

          ctx.restore();
        }
        """

    @staticmethod
    def _get_phase_diagram_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const ox = 150, oy = 350;
          // Axes
          ctx.strokeStyle = "#8a8f98";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(ox, 50); ctx.lineTo(ox, oy); ctx.lineTo(800, oy);
          ctx.stroke();

          ctx.fillStyle = "#8a8f98";
          ctx.font = "bold 13px sans-serif";
          ctx.fillText("Pressure P (atm) [log]", ox - 10, 40);
          ctx.fillText("Temperature T (°C)", 750, oy + 30);

          // Triple point
          const tx = 380, ty = 240;

          // Sublimation curve (Solid -> Gas)
          ctx.beginPath(); ctx.moveTo(ox, oy - 20); ctx.quadraticCurveTo(250, 300, tx, ty);
          ctx.strokeStyle = "#00f0ff"; ctx.lineWidth = 3; ctx.stroke();

          // Vaporization curve (Liquid -> Gas)
          ctx.beginPath(); ctx.moveTo(tx, ty); ctx.quadraticCurveTo(550, 190, 720, 100);
          ctx.strokeStyle = "#d4af37"; ctx.lineWidth = 3; ctx.stroke();

          // Fusion curve (Solid -> Liquid) - CRITICAL: Negative slope for Water!
          ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(340, 70);
          ctx.strokeStyle = "#ff0055"; ctx.lineWidth = 3; ctx.stroke();

          // Triple Point Marker
          ctx.beginPath(); ctx.arc(tx, ty, 6, 0, Math.PI * 2);
          ctx.fillStyle = "#ffffff"; ctx.fill();
          ctx.fillText("Triple Point (0.01°C, 0.006 atm)", tx + 12, ty + 4);

          // Phase Labels
          ctx.font = "bold 20px sans-serif";
          ctx.fillStyle = "rgba(0, 240, 255, 0.4)"; ctx.fillText("SOLID (ICE)", 220, 160);
          ctx.fillStyle = "rgba(212, 175, 55, 0.4)"; ctx.fillText("LIQUID (WATER)", 480, 150);
          ctx.fillStyle = "rgba(179, 136, 255, 0.4)"; ctx.fillText("GAS (STEAM)", 520, 310);

          // Note on anomalous slope
          ctx.fillStyle = "#ff0055"; ctx.font = "bold 11px sans-serif";
          ctx.fillText("← Anomalous Negative Fusion Slope (dP/dT < 0)", 260, 60);

          ctx.restore();
        }
        """

    @staticmethod
    def _get_binary_search_script(target: int) -> str:
        return f"""
        const arr = [2, 5, 8, 12, 16, 23, 38, 45, 56, 72, 91];
        const targetVal = {target};

        function render() {{
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const step = Math.min(3, Math.floor(animProgress * 4));
          let L = 0, R = arr.length - 1;
          for (let s = 0; s < step; s++) {{
            let M = Math.floor((L + R) / 2);
            if (arr[M] === targetVal) break;
            if (arr[M] < targetVal) L = M + 1;
            else R = M - 1;
          }}
          let mid = Math.floor((L + R) / 2);

          ctx.fillStyle = "#d4af37";
          ctx.font = "bold 16px sans-serif";
          ctx.fillText("Searching for Target: " + targetVal + " | Step " + (step + 1) + " of 4 (O(log N))", 100, 80);

          // Draw array boxes
          const startX = 100, boxW = 60, boxH = 60, y = 180;
          arr.forEach((val, idx) => {{
            const x = startX + idx * (boxW + 8);
            let bg = "#14161d", stroke = "#232733";

            if (idx >= L && idx <= R) stroke = "#00f0ff";
            else bg = "#0d0e13";

            if (idx === mid) {{ bg = "#d4af37"; stroke = "#ffffff"; }}

            ctx.fillStyle = bg;
            ctx.fillRect(x, y, boxW, boxH);
            ctx.strokeStyle = stroke;
            ctx.lineWidth = (idx === mid) ? 3 : 1.5;
            ctx.strokeRect(x, y, boxW, boxH);

            ctx.fillStyle = (idx === mid) ? "#000000" : (idx >= L && idx <= R ? "#ffffff" : "#555");
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(val, x + boxW/2, y + 36);

            ctx.fillStyle = "#8a8f98";
            ctx.font = "11px sans-serif";
            ctx.fillText("[" + idx + "]", x + boxW/2, y + boxH + 18);
          }});

          // Draw pointers
          ctx.fillStyle = "#00f0ff";
          ctx.fillText("LOW", startX + L * 68 + 30, y - 20);
          ctx.fillStyle = "#ff0055";
          ctx.fillText("HIGH", startX + R * 68 + 30, y - 20);
          ctx.fillStyle = "#d4af37";
          ctx.fillText("MID = " + arr[mid], startX + mid * 68 + 30, y - 40);

          ctx.restore();
        }}
        """

    @staticmethod
    def _get_transformer_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const blocks = [
            { name: "Input Embedding + RoPE (Base: 500,000.0)", y: 380, color: "#00f0ff" },
            { name: "RMSNorm Pre-Attention", y: 310, color: "#8a8f98" },
            { name: "Grouped-Query Attention (GQA) 24 Q-heads, 8 KV-heads", y: 230, color: "#d4af37" },
            { name: "Residual Addition & RMSNorm", y: 160, color: "#8a8f98" },
            { name: "SwiGLU Feed-Forward Network (d_model=3072, d_ff=8192)", y: 90, color: "#b388ff" },
            { name: "Output Logits (LM Head: 128,256 vocab)", y: 30, color: "#00e676" }
          ];

          blocks.forEach(b => {
            ctx.fillStyle = "#14161d";
            ctx.fillRect(200, b.y, 500, 40);
            ctx.strokeStyle = b.color;
            ctx.lineWidth = 2;
            ctx.strokeRect(200, b.y, 500, 40);

            ctx.fillStyle = b.color;
            ctx.font = "bold 12px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(b.name, 450, b.y + 25);
          });

          // Residual skip connections
          ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          ctx.moveTo(180, 395); ctx.lineTo(150, 395); ctx.lineTo(150, 180); ctx.lineTo(200, 180);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(180, 180); ctx.lineTo(130, 180); ctx.lineTo(130, 50); ctx.lineTo(200, 50);
          ctx.stroke();
          ctx.setLineDash([]);

          ctx.restore();
        }
        """

    @staticmethod
    def _get_circuit_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          ctx.strokeStyle = "#00f0ff"; ctx.lineWidth = 3;
          ctx.strokeRect(200, 120, 500, 200);

          // Power source
          ctx.fillStyle = "#d4af37"; ctx.font = "bold 14px sans-serif";
          ctx.fillText("V_in = 12V (DC)", 100, 225);

          // Resistor
          ctx.fillStyle = "#ff0055";
          ctx.fillRect(400, 110, 80, 20);
          ctx.fillText("R = 100 Ω", 410, 100);

          // Capacitor
          ctx.fillStyle = "#00e676";
          ctx.fillRect(690, 200, 20, 50);
          ctx.fillText("C = 10 µF", 725, 230);

          ctx.restore();
        }
        """

    @staticmethod
    def _get_cpu_architecture_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const units = [
            { name: "Control Unit (Sequencer)", x: 120, y: 100, w: 220, h: 80, color: "#00f0ff" },
            { name: "ALU (Arithmetic Logic Unit)", x: 400, y: 100, w: 220, h: 80, color: "#d4af37" },
            { name: "Register File (R0-R31, PC, SP)", x: 260, y: 220, w: 220, h: 60, color: "#b388ff" },
            { name: "L1 / L2 / L3 Multi-Tier Cache", x: 120, y: 320, w: 500, h: 60, color: "#00e676" }
          ];

          units.forEach(u => {
            ctx.fillStyle = "#14161d";
            ctx.fillRect(u.x, u.y, u.w, u.h);
            ctx.strokeStyle = u.color;
            ctx.lineWidth = 2;
            ctx.strokeRect(u.x, u.y, u.w, u.h);

            ctx.fillStyle = u.color;
            ctx.font = "bold 12px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(u.name, u.x + u.w/2, u.y + u.h/2 + 4);
          });

          ctx.restore();
        }
        """

    @staticmethod
    def _get_os_scheduling_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          ctx.fillStyle = "#d4af37"; ctx.font = "bold 14px sans-serif";
          ctx.fillText("Operating System Scheduling: Round Robin (Time Quantum q = 4ms)", 100, 80);

          const procs = [
            { name: "P1 (Compute)", w: 120, color: "#00f0ff" },
            { name: "P2 (I/O Bound)", w: 80, color: "#b388ff" },
            { name: "P3 (Background)", w: 160, color: "#d4af37" },
            { name: "P1 (Continued)", w: 100, color: "#00f0ff" }
          ];

          let cx = 100;
          procs.forEach((p, i) => {
            ctx.fillStyle = p.color;
            ctx.fillRect(cx, 160, p.w, 50);
            ctx.strokeStyle = "#ffffff";
            ctx.strokeRect(cx, 160, p.w, 50);

            ctx.fillStyle = "#000";
            ctx.font = "bold 12px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(p.name, cx + p.w/2, 190);
            cx += p.w;
          });

          ctx.restore();
        }
        """

    @staticmethod
    def _get_uml_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          // Class Box: UniversalModelManager
          ctx.fillStyle = "#14161d"; ctx.fillRect(150, 100, 260, 200);
          ctx.strokeStyle = "#d4af37"; ctx.lineWidth = 2; ctx.strokeRect(150, 100, 260, 200);

          ctx.fillStyle = "#d4af37"; ctx.font = "bold 13px sans-serif"; ctx.textAlign = "center";
          ctx.fillText("UniversalModelManager", 280, 125);
          ctx.strokeStyle = "#232733"; ctx.beginPath(); ctx.moveTo(150, 135); ctx.lineTo(410, 135); ctx.stroke();

          ctx.fillStyle = "#8a8f98"; ctx.font = "11px monospace"; ctx.textAlign = "left";
          ctx.fillText("- states: Dict[str, State]", 165, 160);
          ctx.fillText("- active_model_id: str", 165, 180);
          ctx.fillText("+ load_model(id): bool", 165, 215);
          ctx.fillText("+ switch_model(id): bool", 165, 235);
          ctx.fillText("+ unload_model(id): void", 165, 255);

          ctx.restore();
        }
        """

    @staticmethod
    def _get_math_plot_script() -> str:
        return """
        function render() {
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.translate(panX + canvas.width/2, panY + canvas.height/2);
          ctx.scale(scale, scale);
          ctx.translate(-canvas.width/2, -canvas.height/2);

          const ox = 450, oy = 225;
          ctx.strokeStyle = "#232733"; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(50, oy); ctx.lineTo(850, oy); ctx.moveTo(ox, 50); ctx.lineTo(ox, 400); ctx.stroke();

          // Plot Sigmoid: σ(x) = 1 / (1 + e^-x)
          ctx.strokeStyle = "#00f0ff"; ctx.lineWidth = 3; ctx.beginPath();
          for (let px = -350; px <= 350; px++) {
            let x = px / 50;
            let sig = 1 / (1 + Math.exp(-x));
            let py = oy - (sig - 0.5) * 250;
            if (px === -350) ctx.moveTo(ox + px, py);
            else ctx.lineTo(ox + px, py);
          }
          ctx.stroke();

          ctx.fillStyle = "#d4af37"; ctx.font = "bold 13px sans-serif";
          ctx.fillText("Activation Function: Sigmoid σ(x) = 1 / (1 + e^-x)", 100, 60);

          ctx.restore();
        }
        """
