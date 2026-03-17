"""
DDR Report Generator — AI-Powered Detailed Diagnostic Report System
====================================================================
Streamlit application that reads Inspection + Thermal PDFs, extracts
text & images via PyMuPDF, analyses them with Groq AI (Llama 3.3 70B),
and produces a structured, client-ready DDR report with embedded images.

Author : Sunil Pandey
Stack  : Python · Streamlit · PyMuPDF · Groq (Llama 3.3 70B)
"""

import streamlit as st
import fitz  # PyMuPDF
import requests
import json
import base64
import io
import re
import time
from datetime import datetime
from PIL import Image

# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DDR Report Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# CUSTOM CSS — Premium dark theme
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global ────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp { background: #0a0a0f; color: #e8e8ec; }
    section[data-testid="stSidebar"] {
        background: #101018 !important;
        border-right: 1px solid #1e1e28;
    }

    /* ── Hero header ──────────────────────────────────────── */
    .hero { text-align: center; padding: 2.5rem 1rem 1.5rem; }
    .hero h1 {
        font-family: 'Inter', sans-serif;
        font-size: 2.6rem; font-weight: 800;
        background: linear-gradient(135deg, #e8c547 0%, #4fd1a5 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: .4rem;
    }
    .hero p { color: #7a7a88; font-size: 1.05rem; max-width: 640px; margin: 0 auto; }
    .badge {
        display: inline-block; background: rgba(232,197,71,.12);
        color: #e8c547; font-family: 'JetBrains Mono', monospace;
        font-size: .7rem; font-weight: 500; letter-spacing: .12em;
        padding: 4px 12px; border-radius: 4px; border: 1px solid rgba(232,197,71,.25);
        text-transform: uppercase; margin-bottom: 1rem;
    }

    /* ── Cards ─────────────────────────────────────────────── */
    .card {
        background: #12121a; border: 1px solid #1e1e28;
        border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 1rem;
    }
    .card-title {
        font-family: 'JetBrains Mono', monospace; font-size: .7rem;
        font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
        color: #e8c547; margin-bottom: .8rem;
    }

    /* ── Report sections ──────────────────────────────────── */
    .report-section {
        background: #12121a; border: 1px solid #1e1e28;
        border-left: 3px solid #e8c547; border-radius: 12px;
        padding: 1.6rem; margin-bottom: 1.2rem;
        position: relative; overflow: hidden;
    }
    .report-section.sev-high { border-left-color: #f07070; }
    .report-section.sev-low  { border-left-color: #4fd1a5; }

    .sec-num {
        font-family: 'JetBrains Mono', monospace; font-size: .65rem;
        color: #7a7a88; letter-spacing: .1em; margin-bottom: .4rem;
    }
    .sec-heading {
        font-size: 1.15rem; font-weight: 800; color: #e8e8ec;
        margin-bottom: .8rem; font-family: 'Inter', sans-serif;
    }
    .sec-body { font-size: .92rem; line-height: 1.75; color: #c0c0cc; }
    .sec-body ul { padding-left: 1.2rem; }
    .sec-body li { margin-bottom: .35rem; }
    .sec-body strong { color: #e8e8ec; }

    /* ── Badges ────────────────────────────────────────────── */
    .sev-badge {
        display: inline-flex; align-items: center; padding: 4px 14px;
        border-radius: 20px; font-size: .75rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; letter-spacing: .06em;
        text-transform: uppercase;
    }
    .sev-badge.high   { background: rgba(240,112,112,.15); color: #f07070; border: 1px solid rgba(240,112,112,.3); }
    .sev-badge.medium { background: rgba(232,197,71,.12);  color: #e8c547; border: 1px solid rgba(232,197,71,.3); }
    .sev-badge.low    { background: rgba(79,209,165,.12);  color: #4fd1a5; border: 1px solid rgba(79,209,165,.3); }

    .na-badge {
        display: inline-block; background: rgba(122,122,136,.12);
        color: #7a7a88; font-family: 'JetBrains Mono', monospace;
        font-size: .72rem; padding: 2px 10px; border-radius: 4px;
        border: 1px solid #2a2a30;
    }

    /* ── Conflict note ────────────────────────────────────── */
    .conflict-note {
        background: rgba(240,112,112,.06); border: 1px solid rgba(240,112,112,.2);
        border-radius: 8px; padding: .7rem 1rem; margin: .6rem 0;
        font-size: .85rem; color: #e8a0a0;
    }

    /* ── Image grid ───────────────────────────────────────── */
    .img-grid { display: flex; flex-wrap: wrap; gap: 10px; margin: 1rem 0; }
    .img-grid img {
        width: 180px; height: 135px; object-fit: cover;
        border-radius: 8px; border: 1px solid #2a2a30;
        transition: transform .2s, box-shadow .2s; cursor: pointer;
    }
    .img-grid img:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 20px rgba(232,197,71,.2);
    }
    .img-caption {
        font-family: 'JetBrains Mono', monospace; font-size: .65rem;
        color: #7a7a88; text-align: center; margin-top: 3px;
    }

    /* ── Report meta ──────────────────────────────────────── */
    .report-meta {
        font-family: 'JetBrains Mono', monospace; font-size: .78rem;
        color: #7a7a88; padding: .8rem 0; border-bottom: 1px solid #1e1e28;
        margin-bottom: 1.5rem;
    }

    /* ── Thermal data ─────────────────────────────────────── */
    .thermal-tag {
        display: inline-block; background: rgba(79,209,165,.1);
        color: #4fd1a5; font-size: .78rem; padding: 3px 10px;
        border-radius: 5px; border: 1px solid rgba(79,209,165,.25);
        font-family: 'JetBrains Mono', monospace; margin-top: .4rem;
    }

    /* ── Priority labels ──────────────────────────────────── */
    .priority-immediate { color: #f07070; font-weight: 700; }
    .priority-short     { color: #e8c547; font-weight: 700; }
    .priority-long      { color: #4fd1a5; font-weight: 700; }

    /* ── Hide default streamlit ───────────────────────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Print styles ─────────────────────────────────────── */
    @media print {
        .stApp { background: #fff !important; color: #222 !important; }
        .report-section { border: 1px solid #ddd; background: #fff; page-break-inside: avoid; }
        .sec-body { color: #333; }
        .sev-badge { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# PDF EXTRACTION — text + images
# ──────────────────────────────────────────────────────────────

def extract_text_and_images(pdf_bytes: bytes) -> dict:
    """
    Extract all text and images from a PDF using PyMuPDF.
    Returns {
        'text': str,                     # Full extracted text
        'page_texts': [str, ...],        # Text per page
        'images': [                      # Extracted embedded images
            {'page': int, 'data_url': str, 'width': int, 'height': int},
            ...
        ],
        'page_images': [str, ...],       # Each page rendered as data_url
        'num_pages': int,
    }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = {
        'text': '',
        'page_texts': [],
        'images': [],
        'page_images': [],
        'num_pages': len(doc),
    }

    for page_num in range(len(doc)):
        page = doc[page_num]

        # ── Text extraction ──
        page_text = page.get_text("text")
        result['page_texts'].append(page_text)
        result['text'] += f"\n--- Page {page_num + 1} ---\n{page_text}"

        # ── Extract embedded images ──
        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image.get("image"):
                    img_data = base_image["image"]
                    img_ext = base_image.get("ext", "png")
                    mime = f"image/{img_ext}" if img_ext != "jpg" else "image/jpeg"
                    b64 = base64.b64encode(img_data).decode()
                    # Get dimensions
                    try:
                        pil_img = Image.open(io.BytesIO(img_data))
                        w, h = pil_img.size
                    except Exception:
                        w, h = 0, 0
                    # Skip tiny images (icons, artifacts) — only keep meaningful ones
                    if w >= 50 and h >= 50:
                        result['images'].append({
                            'page': page_num + 1,
                            'data_url': f"data:{mime};base64,{b64}",
                            'width': w,
                            'height': h,
                            'index': img_index,
                        })
            except Exception:
                pass

        # ── Render page as image (for thermal pages that ARE images) ──
        mat = fitz.Matrix(2, 2)  # 2x zoom for quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        b64 = base64.b64encode(img_data).decode()
        result['page_images'].append(f"data:image/png;base64,{b64}")

    doc.close()
    return result


# ──────────────────────────────────────────────────────────────
# GROQ AI — DDR report generation
# ──────────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DDR_PROMPT = """You are an expert building diagnostics engineer. You must analyse TWO documents and generate a Detailed Diagnostic Report (DDR).

=== INSPECTION REPORT ===
{inspection_text}

=== THERMAL REPORT ===
{thermal_text}

=== INSPECTION REPORT IMAGE INFO ===
The inspection report has {insp_pages} pages. Pages with images: {insp_image_pages}.

=== THERMAL REPORT IMAGE INFO ===
The thermal report has {therm_pages} pages. Each page contains one thermal image with hotspot/coldspot readings.

RULES:
- Do NOT invent facts. Only use what is in the documents.
- If information is missing, use exactly: "Not Available"
- If information conflicts between documents, describe the conflict.
- No duplicate observations across different areas.
- Use simple, client-friendly language. Avoid unnecessary technical jargon.
- Map each area observation to the inspection report page numbers and thermal report page numbers that correspond to it.

Return ONLY a valid JSON object (no markdown fences, no explanation), with this exact structure:

{{
  "property_name": "string or Not Available",
  "report_date": "string or Not Available",
  "inspected_by": "string or Not Available",
  "property_type": "string or Not Available",
  "property_age": "string or Not Available",
  "floors": "string or Not Available",
  "property_issue_summary": "2-4 sentence overview of main issues found",
  "area_observations": [
    {{
      "area": "location/room name",
      "observations": ["observation 1", "observation 2"],
      "thermal_findings": "thermal data summary or Not Available",
      "inspection_image_pages": [3, 4],
      "thermal_image_pages": [1, 2],
      "has_conflict": false,
      "conflict_note": ""
    }}
  ],
  "probable_root_causes": [
    {{"cause": "description", "related_areas": ["area1", "area2"]}}
  ],
  "severity_assessment": {{
    "overall": "High or Medium or Low",
    "reasoning": "explanation",
    "breakdown": [
      {{"area": "name", "severity": "High or Medium or Low", "reason": "reason"}}
    ]
  }},
  "recommended_actions": [
    {{"priority": "Immediate or Short-term or Long-term", "action": "description", "area": "area name"}}
  ],
  "additional_notes": ["note 1", "note 2"],
  "missing_or_unclear": ["item 1", "item 2"]
}}"""


def call_groq(api_key: str, insp_data: dict, therm_data: dict,
              progress_callback=None) -> dict:
    """Call Groq API with extracted PDF data and return parsed DDR JSON."""

    if progress_callback:
        progress_callback("Building AI prompt…")

    # Determine which pages have images
    insp_img_pages = sorted(set(img['page'] for img in insp_data['images']))
    therm_img_pages = sorted(set(img['page'] for img in therm_data['images']))

    prompt = DDR_PROMPT.format(
        inspection_text=insp_data['text'][:15000],
        thermal_text=therm_data['text'][:15000],
        insp_pages=insp_data['num_pages'],
        insp_image_pages=insp_img_pages if insp_img_pages else "No embedded images detected",
        therm_pages=therm_data['num_pages'],
    )

    if progress_callback:
        progress_callback("Sending to Groq AI (Llama 3.3 70B)…")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        error_msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        raise Exception(f"Groq API error: {error_msg}")

    if progress_callback:
        progress_callback("Parsing AI response…")

    raw = resp.json()["choices"][0]["message"]["content"]

    # Clean markdown fences if present
    clean = re.sub(r"```json|```", "", raw).strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to extract JSON object
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            return json.loads(match.group(0))
        raise Exception(f"AI returned invalid JSON.\n\nRaw response:\n{raw[:500]}")


# ──────────────────────────────────────────────────────────────
# HTML REPORT BUILDER — downloadable standalone report
# ──────────────────────────────────────────────────────────────

def build_downloadable_html(ddr: dict, insp_data: dict, therm_data: dict) -> str:
    """Build a standalone, beautiful HTML report with embedded images."""

    sev = (ddr.get("severity_assessment", {}).get("overall", "")).lower()

    def na(val):
        if not val or val == "Not Available":
            return '<span class="na-badge">Not Available</span>'
        return val

    def sev_badge(s):
        c = (s or "").lower()
        return f'<span class="sev-badge {c}">{s or "N/A"}</span>'

    def get_images_html(area_obs):
        """Get images for a specific area observation."""
        html_parts = []
        insp_pages = area_obs.get("inspection_image_pages", [])
        therm_pages = area_obs.get("thermal_image_pages", [])

        if insp_pages:
            html_parts.append('<h4 style="color:#e8c547;font-size:.8rem;margin:1rem 0 .5rem;">📋 Inspection Photos</h4>')
            html_parts.append('<div class="img-grid">')
            for pg in insp_pages:
                if 1 <= pg <= len(insp_data['page_images']):
                    html_parts.append(
                        f'<div><img src="{insp_data["page_images"][pg-1]}" '
                        f'alt="Inspection Page {pg}" />'
                        f'<div class="img-caption">Page {pg}</div></div>'
                    )
            html_parts.append('</div>')
        elif not insp_pages:
            html_parts.append('<p><span class="na-badge">Inspection Images: Not Available</span></p>')

        if therm_pages:
            html_parts.append('<h4 style="color:#4fd1a5;font-size:.8rem;margin:1rem 0 .5rem;">🌡️ Thermal Images</h4>')
            html_parts.append('<div class="img-grid">')
            for pg in therm_pages:
                if 1 <= pg <= len(therm_data['page_images']):
                    html_parts.append(
                        f'<div><img src="{therm_data["page_images"][pg-1]}" '
                        f'alt="Thermal Page {pg}" />'
                        f'<div class="img-caption">Thermal #{pg}</div></div>'
                    )
            html_parts.append('</div>')
        elif not therm_pages:
            html_parts.append('<p><span class="na-badge">Thermal Images: Not Available</span></p>')

        return "\n".join(html_parts)

    # ── Build area observations HTML ──
    areas_html = ""
    for obs in ddr.get("area_observations", []):
        conflict = ""
        if obs.get("has_conflict"):
            conflict = f'<div class="conflict-note">⚠️ {obs.get("conflict_note", "")}</div>'

        obs_list = "".join(f"<li>{o}</li>" for o in obs.get("observations", []))
        thermal = obs.get("thermal_findings", "Not Available")
        thermal_html = f'<div class="thermal-tag">🌡️ {thermal}</div>' if thermal and thermal != "Not Available" else '<span class="na-badge">Thermal: Not Available</span>'
        images_html = get_images_html(obs)

        areas_html += f"""
        <div style="margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid #1e1e28;">
            <h4 style="color:#4fd1a5;font-size:1rem;margin-bottom:.5rem;">📍 {obs.get('area', 'Unknown')}</h4>
            {conflict}
            <ul>{obs_list}</ul>
            {thermal_html}
            {images_html}
        </div>"""

    # ── Root causes ──
    causes_html = ""
    for c in ddr.get("probable_root_causes", []):
        areas = ", ".join(c.get("related_areas", []))
        causes_html += f'<li><strong>{c["cause"]}</strong> <span style="color:#7a7a88;font-size:.8rem;">({areas})</span></li>'

    # ── Severity breakdown table ──
    sev_rows = ""
    for b in ddr.get("severity_assessment", {}).get("breakdown", []):
        sev_rows += f"""<tr>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;">{b['area']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;">{sev_badge(b['severity'])}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;color:#7a7a88;font-size:.85rem;">{b['reason']}</td>
        </tr>"""

    # ── Recommended actions ──
    actions_by_priority = {"Immediate": [], "Short-term": [], "Long-term": []}
    for a in ddr.get("recommended_actions", []):
        priority = a.get("priority", "Short-term")
        if priority not in actions_by_priority:
            priority = "Short-term"
        actions_by_priority[priority].append(a)

    actions_html = ""
    priority_colors = {"Immediate": "#f07070", "Short-term": "#e8c547", "Long-term": "#4fd1a5"}
    priority_classes = {"Immediate": "priority-immediate", "Short-term": "priority-short", "Long-term": "priority-long"}
    for pri, items in actions_by_priority.items():
        if items:
            items_html = "".join(f'<li><strong>{i["area"]}:</strong> {i["action"]}</li>' for i in items)
            actions_html += f'<h4 class="{priority_classes[pri]}" style="font-size:.85rem;margin:1rem 0 .4rem;">{pri}</h4><ul>{items_html}</ul>'

    # ── Additional notes ──
    notes = ddr.get("additional_notes", [])
    notes_html = "".join(f"<li>{n}</li>" for n in notes) if notes else '<span class="na-badge">Not Available</span>'

    # ── Missing info ──
    missing = ddr.get("missing_or_unclear", [])
    missing_html = "".join(f"<li>{m}</li>" for m in missing) if missing else "<p>No missing information identified.</p>"

    sa = ddr.get("severity_assessment", {})
    generated_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>DDR Report — {na(ddr.get('property_name'))}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
    :root {{ --bg: #0a0a0f; --surface: #12121a; --border: #1e1e28; --accent: #e8c547; --accent2: #4fd1a5; --danger: #f07070; --text: #e8e8ec; --muted: #7a7a88; }}
    * {{ box-sizing: border-box; margin:0; padding:0; }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; padding: 2rem; max-width: 960px; margin: 0 auto; }}
    .report-section {{ background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 12px; padding: 1.6rem; margin-bottom: 1.2rem; }}
    .report-section.sev-high {{ border-left-color: var(--danger); }}
    .report-section.sev-low {{ border-left-color: var(--accent2); }}
    .sec-num {{ font-family: 'JetBrains Mono', monospace; font-size: .65rem; color: var(--muted); letter-spacing: .1em; }}
    .sec-heading {{ font-size: 1.15rem; font-weight: 800; margin: .3rem 0 .8rem; }}
    .sec-body {{ font-size: .92rem; line-height: 1.75; color: #c0c0cc; }}
    .sec-body ul {{ padding-left: 1.2rem; }} .sec-body li {{ margin-bottom: .35rem; }} .sec-body strong {{ color: var(--text); }}
    .sev-badge {{ display: inline-flex; padding: 4px 14px; border-radius: 20px; font-size: .75rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; letter-spacing: .06em; text-transform: uppercase; }}
    .sev-badge.high {{ background: rgba(240,112,112,.15); color: var(--danger); border: 1px solid rgba(240,112,112,.3); }}
    .sev-badge.medium {{ background: rgba(232,197,71,.12); color: var(--accent); border: 1px solid rgba(232,197,71,.3); }}
    .sev-badge.low {{ background: rgba(79,209,165,.12); color: var(--accent2); border: 1px solid rgba(79,209,165,.3); }}
    .na-badge {{ display: inline-block; background: rgba(122,122,136,.12); color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: .72rem; padding: 2px 10px; border-radius: 4px; border: 1px solid #2a2a30; }}
    .conflict-note {{ background: rgba(240,112,112,.06); border: 1px solid rgba(240,112,112,.2); border-radius: 8px; padding: .7rem 1rem; margin: .6rem 0; font-size: .85rem; color: #e8a0a0; }}
    .thermal-tag {{ display: inline-block; background: rgba(79,209,165,.1); color: var(--accent2); font-size: .78rem; padding: 3px 10px; border-radius: 5px; border: 1px solid rgba(79,209,165,.25); font-family: 'JetBrains Mono', monospace; margin-top: .4rem; }}
    .img-grid {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 1rem 0; }}
    .img-grid img {{ width: 200px; height: 150px; object-fit: cover; border-radius: 8px; border: 1px solid #2a2a30; }}
    .img-caption {{ font-family: 'JetBrains Mono', monospace; font-size: .65rem; color: var(--muted); text-align: center; margin-top: 3px; }}
    .report-meta {{ font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: var(--muted); padding: .8rem 0; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; }}
    .priority-immediate {{ color: var(--danger); font-weight: 700; }}
    .priority-short {{ color: var(--accent); font-weight: 700; }}
    .priority-long {{ color: var(--accent2); font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .85rem; margin-top: 1rem; }}
    h1 {{ font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #e8c547, #4fd1a5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    @media print {{
        body {{ background: #fff !important; color: #222 !important; }}
        .report-section {{ border: 1px solid #ddd; background: #fafafa; page-break-inside: avoid; }}
        .sec-body {{ color: #333; }}
    }}
</style>
</head>
<body>
<div style="text-align:center;padding:1.5rem 0;margin-bottom:1rem;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:.7rem;letter-spacing:.12em;color:#e8c547;margin-bottom:.8rem;">GENERATED DDR · AI-ASSISTED ANALYSIS · POWERED BY GROQ</div>
    <h1>Detailed Diagnostic Report</h1>
</div>
<div class="report-meta">
    Property: {ddr.get('property_name','N/A')} &nbsp;|&nbsp;
    Type: {ddr.get('property_type','N/A')} &nbsp;|&nbsp;
    Date: {ddr.get('report_date','N/A')} &nbsp;|&nbsp;
    Inspected By: {ddr.get('inspected_by','N/A')} &nbsp;|&nbsp;
    Generated: {generated_time}
</div>

<div class="report-section">
    <div class="sec-num">SECTION 01</div>
    <div class="sec-heading">Property Issue Summary</div>
    <div class="sec-body"><p>{na(ddr.get('property_issue_summary'))}</p></div>
</div>

<div class="report-section">
    <div class="sec-num">SECTION 02</div>
    <div class="sec-heading">Area-wise Observations</div>
    <div class="sec-body">{areas_html if areas_html else na(None)}</div>
</div>

<div class="report-section">
    <div class="sec-num">SECTION 03</div>
    <div class="sec-heading">Probable Root Causes</div>
    <div class="sec-body"><ul>{causes_html if causes_html else na(None)}</ul></div>
</div>

<div class="report-section sev-{sev}">
    <div class="sec-num">SECTION 04</div>
    <div class="sec-heading">Severity Assessment</div>
    <div class="sec-body">
        <p>Overall: {sev_badge(sa.get('overall'))}</p>
        <p style="margin-top:.6rem;">{na(sa.get('reasoning'))}</p>
        {"<table>" + sev_rows + "</table>" if sev_rows else ""}
    </div>
</div>

<div class="report-section">
    <div class="sec-num">SECTION 05</div>
    <div class="sec-heading">Recommended Actions</div>
    <div class="sec-body">{actions_html if actions_html else na(None)}</div>
</div>

<div class="report-section">
    <div class="sec-num">SECTION 06</div>
    <div class="sec-heading">Additional Notes</div>
    <div class="sec-body"><ul>{notes_html}</ul></div>
</div>

<div class="report-section">
    <div class="sec-num">SECTION 07</div>
    <div class="sec-heading">Missing or Unclear Information</div>
    <div class="sec-body">{missing_html}</div>
</div>

<div style="text-align:center;padding:2rem 0;font-family:'JetBrains Mono',monospace;font-size:.75rem;color:#7a7a88;border-top:1px solid #1e1e28;margin-top:2rem;">
    DDR Report Generator · Groq (Llama 3.3 70B) · AI Generalist Assignment · Generated {generated_time}
</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# STREAMLIT UI
# ──────────────────────────────────────────────────────────────

def main():
    # ── Hero ──
    st.markdown("""
    <div class="hero">
        <div class="badge">DDR System · AI-Powered</div>
        <h1>Detailed Diagnostic<br>Report Generator</h1>
        <p>Upload your Inspection Report and Thermal Report. The AI extracts text & images,
           merges data, and generates a complete client-ready DDR automatically.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.markdown("---")

        # API Key
        st.markdown('<div class="card-title">Step 1 — Groq API Key</div>', unsafe_allow_html=True)
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Get a free key at https://console.groq.com/keys",
            label_visibility="collapsed",
        )
        if api_key and not api_key.startswith("gsk_"):
            st.error("Key must start with `gsk_`")
            api_key = None
        elif api_key:
            st.success("✓ API key set")

        st.markdown("---")

        # File uploads
        st.markdown('<div class="card-title">Step 2 — Upload Documents</div>', unsafe_allow_html=True)
        insp_file = st.file_uploader("📋 Inspection Report", type=["pdf"], key="insp")
        therm_file = st.file_uploader("🌡️ Thermal Report", type=["pdf"], key="therm")

        st.markdown("---")
        st.markdown(
            '<div style="font-size:.75rem;color:#7a7a88;font-family:\'JetBrains Mono\',monospace;">'
            '100% free · No billing required<br>'
            '<a href="https://console.groq.com/keys" target="_blank" style="color:#e8c547;">Get API key →</a>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Main content ──
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
            <div class="card-title">📋 Inspection Report</div>
        """, unsafe_allow_html=True)
        if insp_file:
            st.markdown(f'<span style="color:#4fd1a5;font-size:.85rem;">✓ {insp_file.name}</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#7a7a88;font-size:.85rem;">No file uploaded</span>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-title">🌡️ Thermal Report</div>
        """, unsafe_allow_html=True)
        if therm_file:
            st.markdown(f'<span style="color:#4fd1a5;font-size:.85rem;">✓ {therm_file.name}</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#7a7a88;font-size:.85rem;">No file uploaded</span>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Generate button ──
    st.markdown("<br>", unsafe_allow_html=True)
    ready = bool(api_key and insp_file and therm_file)
    generate = st.button(
        "⚡ Generate DDR Report",
        disabled=not ready,
        use_container_width=True,
        type="primary",
    )

    if not ready:
        st.info("Upload both PDFs and enter your Groq API key to generate the report.")
        return

    if generate:
        with st.spinner(""):
            progress = st.empty()
            status_area = st.empty()

            try:
                # Step 1: Extract from Inspection PDF
                status_area.markdown("""
                <div class="card">
                    <div class="card-title">⏳ Processing</div>
                    <p style="color:#e8c547;">Extracting text & images from Inspection Report…</p>
                </div>
                """, unsafe_allow_html=True)
                insp_data = extract_text_and_images(insp_file.read())
                insp_file.seek(0)

                # Step 2: Extract from Thermal PDF
                status_area.markdown(f"""
                <div class="card">
                    <div class="card-title">⏳ Processing</div>
                    <p style="color:#4fd1a5;">✓ Inspection: {insp_data['num_pages']} pages, {len(insp_data['images'])} images extracted</p>
                    <p style="color:#e8c547;">Extracting text & images from Thermal Report…</p>
                </div>
                """, unsafe_allow_html=True)
                therm_data = extract_text_and_images(therm_file.read())
                therm_file.seek(0)

                # Step 3: Call Groq AI
                def update_status(msg):
                    status_area.markdown(f"""
                    <div class="card">
                        <div class="card-title">⏳ Processing</div>
                        <p style="color:#4fd1a5;">✓ Inspection: {insp_data['num_pages']} pages, {len(insp_data['images'])} images</p>
                        <p style="color:#4fd1a5;">✓ Thermal: {therm_data['num_pages']} pages, {len(therm_data['images'])} images</p>
                        <p style="color:#e8c547;">{msg}</p>
                    </div>
                    """, unsafe_allow_html=True)

                ddr = call_groq(api_key, insp_data, therm_data, update_status)

                # Clear status
                status_area.empty()

                # ── Store results in session state ──
                st.session_state['ddr'] = ddr
                st.session_state['insp_data'] = insp_data
                st.session_state['therm_data'] = therm_data

            except Exception as e:
                status_area.empty()
                st.error(f"**Error:** {str(e)}")
                return

    # ── Render DDR Report ──
    if 'ddr' in st.session_state:
        ddr = st.session_state['ddr']
        insp_data = st.session_state['insp_data']
        therm_data = st.session_state['therm_data']
        sev = (ddr.get("severity_assessment", {}).get("overall", "")).lower()

        st.markdown("---")

        # ── Download / Print buttons ──
        report_html = build_downloadable_html(ddr, insp_data, therm_data)
        col_dl1, col_dl2 = st.columns([1, 1])
        with col_dl1:
            st.download_button(
                label="📥 Download Full HTML Report",
                data=report_html,
                file_name=f"DDR_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                use_container_width=True,
            )
        with col_dl2:
            # Download raw JSON
            st.download_button(
                label="📋 Download Raw JSON Data",
                data=json.dumps(ddr, indent=2),
                file_name=f"DDR_Data_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
            )

        # ── Report Header ──
        st.markdown(f"""
        <div style="text-align:center;padding:1.5rem 0;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:.7rem;letter-spacing:.12em;color:#e8c547;margin-bottom:.6rem;">
                GENERATED DDR · AI-ASSISTED ANALYSIS · POWERED BY GROQ
            </div>
            <h2 style="font-size:1.8rem;font-weight:800;color:#e8e8ec;">Detailed Diagnostic Report</h2>
        </div>
        <div class="report-meta">
            Property: {ddr.get('property_name','N/A')} &nbsp;|&nbsp;
            Type: {ddr.get('property_type','N/A')} &nbsp;|&nbsp;
            Date: {ddr.get('report_date','N/A')} &nbsp;|&nbsp;
            Inspected By: {ddr.get('inspected_by','N/A')} &nbsp;|&nbsp;
            Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 01: Property Issue Summary ──
        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 01</div>
            <div class="sec-heading">Property Issue Summary</div>
            <div class="sec-body"><p>{ddr.get('property_issue_summary', '<span class="na-badge">Not Available</span>')}</p></div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 02: Area-wise Observations ──
        areas_html_parts = []
        for obs in ddr.get("area_observations", []):
            conflict = ""
            if obs.get("has_conflict"):
                conflict = f'<div class="conflict-note">⚠️ {obs.get("conflict_note", "")}</div>'

            obs_list = "".join(f"<li>{o}</li>" for o in obs.get("observations", []))
            thermal = obs.get("thermal_findings", "Not Available")
            thermal_html = (
                f'<div class="thermal-tag">🌡️ {thermal}</div>'
                if thermal and thermal != "Not Available"
                else '<span class="na-badge">Thermal: Not Available</span>'
            )

            # Images
            img_html_parts = []
            insp_pages = obs.get("inspection_image_pages", [])
            therm_pages = obs.get("thermal_image_pages", [])

            if insp_pages:
                img_html_parts.append('<h4 style="color:#e8c547;font-size:.8rem;margin:1rem 0 .4rem;">📋 Inspection Photos</h4><div class="img-grid">')
                for pg in insp_pages:
                    if 1 <= pg <= len(insp_data['page_images']):
                        img_html_parts.append(
                            f'<div><img src="{insp_data["page_images"][pg-1]}" alt="Page {pg}"/>'
                            f'<div class="img-caption">Page {pg}</div></div>'
                        )
                img_html_parts.append('</div>')
            else:
                img_html_parts.append('<p><span class="na-badge">Inspection Images: Image Not Available</span></p>')

            if therm_pages:
                img_html_parts.append('<h4 style="color:#4fd1a5;font-size:.8rem;margin:1rem 0 .4rem;">🌡️ Thermal Images</h4><div class="img-grid">')
                for pg in therm_pages:
                    if 1 <= pg <= len(therm_data['page_images']):
                        img_html_parts.append(
                            f'<div><img src="{therm_data["page_images"][pg-1]}" alt="Thermal {pg}"/>'
                            f'<div class="img-caption">Thermal #{pg}</div></div>'
                        )
                img_html_parts.append('</div>')
            else:
                img_html_parts.append('<p><span class="na-badge">Thermal Images: Image Not Available</span></p>')

            areas_html_parts.append(f"""
            <div style="margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid #1e1e28;">
                <h4 style="color:#4fd1a5;font-size:1rem;margin-bottom:.5rem;">📍 {obs.get('area', 'Unknown')}</h4>
                {conflict}
                <ul>{obs_list}</ul>
                {thermal_html}
                {"".join(img_html_parts)}
            </div>""")

        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 02</div>
            <div class="sec-heading">Area-wise Observations</div>
            <div class="sec-body">{"".join(areas_html_parts) if areas_html_parts else '<span class="na-badge">Not Available</span>'}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 03: Probable Root Causes ──
        causes = ddr.get("probable_root_causes", [])
        causes_html = ""
        for c in causes:
            areas = ", ".join(c.get("related_areas", []))
            causes_html += f'<li><strong>{c["cause"]}</strong> <span style="color:#7a7a88;font-size:.8rem;">({areas})</span></li>'
        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 03</div>
            <div class="sec-heading">Probable Root Causes</div>
            <div class="sec-body"><ul>{causes_html if causes_html else '<span class="na-badge">Not Available</span>'}</ul></div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 04: Severity Assessment ──
        sa = ddr.get("severity_assessment", {})
        sev_rows = ""
        for b in sa.get("breakdown", []):
            bc = (b.get("severity", "")).lower()
            sev_rows += f"""<tr>
                <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;">{b['area']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;"><span class="sev-badge {bc}">{b['severity']}</span></td>
                <td style="padding:8px 12px;border-bottom:1px solid #1e1e28;color:#7a7a88;font-size:.85rem;">{b['reason']}</td>
            </tr>"""
        overall_c = (sa.get('overall', '')).lower()
        st.markdown(f"""
        <div class="report-section sev-{sev}">
            <div class="sec-num">SECTION 04</div>
            <div class="sec-heading">Severity Assessment</div>
            <div class="sec-body">
                <p>Overall: <span class="sev-badge {overall_c}">{sa.get('overall', 'N/A')}</span></p>
                <p style="margin-top:.6rem;">{sa.get('reasoning', '<span class="na-badge">Not Available</span>')}</p>
                {"<table>" + sev_rows + "</table>" if sev_rows else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 05: Recommended Actions ──
        actions_by_priority = {"Immediate": [], "Short-term": [], "Long-term": []}
        for a in ddr.get("recommended_actions", []):
            pri = a.get("priority", "Short-term")
            if pri not in actions_by_priority:
                pri = "Short-term"
            actions_by_priority[pri].append(a)

        actions_html = ""
        priority_classes = {"Immediate": "priority-immediate", "Short-term": "priority-short", "Long-term": "priority-long"}
        for pri, items in actions_by_priority.items():
            if items:
                items_html = "".join(f'<li><strong>{i["area"]}:</strong> {i["action"]}</li>' for i in items)
                actions_html += f'<h4 class="{priority_classes[pri]}" style="font-size:.85rem;margin:1rem 0 .4rem;">{pri}</h4><ul>{items_html}</ul>'

        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 05</div>
            <div class="sec-heading">Recommended Actions</div>
            <div class="sec-body">{actions_html if actions_html else '<span class="na-badge">Not Available</span>'}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 06: Additional Notes ──
        notes = ddr.get("additional_notes", [])
        notes_html = "".join(f"<li>{n}</li>" for n in notes) if notes else '<span class="na-badge">Not Available</span>'
        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 06</div>
            <div class="sec-heading">Additional Notes</div>
            <div class="sec-body"><ul>{notes_html}</ul></div>
        </div>
        """, unsafe_allow_html=True)

        # ── SECTION 07: Missing or Unclear Information ──
        missing = ddr.get("missing_or_unclear", [])
        missing_html = "".join(f"<li>{m}</li>" for m in missing) if missing else "<p>No missing information identified.</p>"
        st.markdown(f"""
        <div class="report-section">
            <div class="sec-num">SECTION 07</div>
            <div class="sec-heading">Missing or Unclear Information</div>
            <div class="sec-body">{missing_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Extracted Images Gallery ──
        st.markdown("---")
        with st.expander("🖼️ All Extracted Inspection Images", expanded=False):
            if insp_data['images']:
                cols = st.columns(4)
                for i, img in enumerate(insp_data['images']):
                    with cols[i % 4]:
                        st.markdown(
                            f'<img src="{img["data_url"]}" style="width:100%;border-radius:8px;border:1px solid #2a2a30;margin-bottom:8px;" />'
                            f'<div style="font-size:.7rem;color:#7a7a88;text-align:center;">Page {img["page"]} · {img["width"]}×{img["height"]}</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info("No embedded images found in the inspection PDF. Page renders are used instead.")

        with st.expander("🌡️ All Thermal Page Renders", expanded=False):
            cols = st.columns(4)
            for i, page_img in enumerate(therm_data['page_images']):
                with cols[i % 4]:
                    st.markdown(
                        f'<img src="{page_img}" style="width:100%;border-radius:8px;border:1px solid #2a2a30;margin-bottom:8px;" />'
                        f'<div style="font-size:.7rem;color:#7a7a88;text-align:center;">Thermal #{i+1}</div>',
                        unsafe_allow_html=True,
                    )

        # ── Footer ──
        st.markdown(f"""
        <div style="text-align:center;padding:2rem 0;font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#7a7a88;border-top:1px solid #1e1e28;margin-top:2rem;">
            DDR Report Generator · Python + Streamlit · Groq (Llama 3.3 70B) · AI Generalist Assignment
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
