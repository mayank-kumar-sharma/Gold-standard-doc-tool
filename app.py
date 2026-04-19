import streamlit as st
import json
import re
import os
from datetime import datetime
from openai import OpenAI
import httpx

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carbon Standards Document Finder",
    page_icon="🌿",
    layout="wide"
)

# ─── Session State Init ──────────────────────────────────────────────────────
if "show_results" not in st.session_state:
    st.session_state["show_results"] = False
if "ai_summary" not in st.session_state:
    st.session_state["ai_summary"] = None
if "registry_key" not in st.session_state:
    st.session_state["registry_key"] = "gold_standard"
if "project_type_key" not in st.session_state:
    st.session_state["project_type_key"] = "afforestation_reforestation"
if "registry_display" not in st.session_state:
    st.session_state["registry_display"] = ""
if "project_type_display" not in st.session_state:
    st.session_state["project_type_display"] = ""

# ─── Load Database ───────────────────────────────────────────────────────────
@st.cache_data
def load_db():
    try:
        with open("documents_db.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"⚠️ Could not load document database: {e}")
        return {}

db = load_db()

# ─── Styling ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a4731 0%, #2d7a4f 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .doc-card {
        background: #f8f9fa;
        border-left: 4px solid #2d7a4f;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    .template-card {
        background: #fff8e1;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    .methodology-card {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    .core-card {
        background: #fce4ec;
        border-left: 4px solid #e91e63;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        padding: 8px 0;
        margin: 16px 0 8px 0;
        border-bottom: 2px solid #e0e0e0;
    }
    .ai-analysis {
        background: #e3f2fd;
        border: 1px solid #90caf9;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }
    .export-box {
        background: #f0fdf4;
        border: 1px solid #86efac;
        padding: 16px 20px;
        border-radius: 10px;
        margin: 20px 0 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌿 Carbon Standards Document Finder</h1>
    <p style="margin:0; opacity:0.9;">Find the exact documents you need for your nature-based carbon project</p>
    <p style="margin:4px 0 0 0; opacity:0.75; font-size:0.85rem;">Supports Gold Standard · Verra/VCS · ICR</p>
</div>
""", unsafe_allow_html=True)

# ─── Load API Key from Secrets ───────────────────────────────────────────────
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = None

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("**🌿 Nature-Based Project Types:**")
    st.markdown("• Afforestation / Reforestation")
    st.markdown("• Soil Organic Carbon")
    st.markdown("• Blue Carbon / Mangrove")
    st.markdown("• REDD+ / Forest Conservation")
    st.markdown("• Agriculture")
    st.markdown("---")
    st.markdown("**📚 Registries Covered:**")
    st.markdown("• Gold Standard (GS4GG)")
    st.markdown("• Verra / VCS")
    st.markdown("• ICR")

# ─── Main Interface ───────────────────────────────────────────────────────────
st.markdown("## 🔍 Find Your Documents")

input_mode = st.radio(
    "How do you want to find documents?",
    ["📋 Select from dropdowns", "💬 Describe your project (AI-powered)"],
    horizontal=True
)

# ─── Registry + Project Type Maps ─────────────────────────────────────────────
REGISTRY_MAP = {
    "🌟 Gold Standard (GS4GG)": "gold_standard",
    "✅ Verra / VCS": "verra",
    "🔷 International Carbon Registry (ICR)": "icr"
}

PROJECT_TYPE_MAP = {
    "🌳 Afforestation / Reforestation (A/R)": "afforestation_reforestation",
    "🌱 Soil Organic Carbon (SOC)": "soil_organic_carbon",
    "🌊 Blue Carbon / Mangrove": "blue_carbon",
    "🌲 REDD+ / Forest Conservation": "redd_plus",
    "🌾 Agriculture (General)": "agriculture"
}

# ─── Mode 1: Dropdown ─────────────────────────────────────────────────────────
if input_mode == "📋 Select from dropdowns":
    col1, col2 = st.columns(2)
    with col1:
        registry_display = st.selectbox("1️⃣ Select Registry", list(REGISTRY_MAP.keys()))
    with col2:
        project_type_display = st.selectbox("2️⃣ Select Project Type", list(PROJECT_TYPE_MAP.keys()))

    registry_key = REGISTRY_MAP[registry_display]
    project_type_key = PROJECT_TYPE_MAP[project_type_display]

    if st.button("🔍 Find Documents", type="primary", use_container_width=True):
        st.session_state["show_results"] = True
        st.session_state["registry_key"] = registry_key
        st.session_state["project_type_key"] = project_type_key
        st.session_state["registry_display"] = registry_display
        st.session_state["project_type_display"] = project_type_display
        st.session_state["ai_summary"] = None

# ─── Mode 2: AI Description ───────────────────────────────────────────────────
else:
    project_description = st.text_area(
        "Describe your project in plain English",
        placeholder="E.g., Mangrove restoration project in coastal Odisha, India...",
        height=100
    )

    col_reg, col_hint = st.columns([1, 2])
    with col_reg:
        override_registry = st.selectbox(
            "Registry (optional)",
            ["🤖 Auto-detect (recommended)", "🌟 Gold Standard (GS4GG)", "✅ Verra / VCS", "🔷 ICR"],
            help="Leave on Auto-detect to let AI pick the best registry. Select manually if you already know."
        )
    with col_hint:
        st.markdown("<div style='padding-top:32px; color:#555; font-size:0.85rem;'>💡 If you don't select a registry, our AI will automatically choose the most suitable one based on your project description.</div>", unsafe_allow_html=True)

    OVERRIDE_REGISTRY_MAP = {
        "🌟 Gold Standard (GS4GG)": "gold_standard",
        "✅ Verra / VCS": "verra",
        "🔷 ICR": "icr"
    }

    if st.button("🤖 Analyse & Find Documents", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ AI analysis is temporarily unavailable. Please use the dropdown mode or contact support.")
        elif not project_description.strip():
            st.warning("⚠️ Please describe your project first.")
        else:
            with st.spinner("🤖 Analysing your project..."):
                success = False
                last_error = None

                client = OpenAI(
                    api_key=api_key,
                    http_client=httpx.Client(timeout=10.0)
                )

                for attempt in range(2):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4.1",
                            messages=[
                                {
                                    "role": "system",
                                    "content": """You are an expert in carbon standards and nature-based climate projects.

Your job is to classify the project into the best registry and correct project type.

### Registry Selection Rules:
- Use "gold_standard" for:
  - community-based or smallholder projects
  - SDG-focused or social impact projects
  - blue carbon / mangrove restoration
  - soil organic carbon / agriculture (small to mid scale)

- Use "verra" for:
  - large-scale forestry or REDD+ projects
  - corporate or industrial carbon projects
  - avoided deforestation at scale
  - tidal wetland / seagrass restoration (large scale)

- Use "icr" for:
  - smaller or flexible projects
  - when project does not clearly fit GS or Verra criteria
  - projects needing simpler registration process

### Project Type Rules:
- "afforestation_reforestation" → planting trees, forest restoration, revegetation
- "soil_organic_carbon" → farming practices, soil improvement, tillage, cover crops
- "blue_carbon" → mangroves, coastal wetlands, seagrass, tidal ecosystems
- "redd_plus" → avoided deforestation, forest conservation, protecting existing forests
- "agriculture" → general farming, rice cultivation, biochar, microbial soil methods

### Output Format (STRICT — RAW JSON ONLY, NO MARKDOWN):
{
  "registry": "gold_standard" | "verra" | "icr",
  "project_type": "afforestation_reforestation" | "soil_organic_carbon" | "blue_carbon" | "redd_plus" | "agriculture",
  "confidence": <float 0.0 to 1.0>,
  "reasoning": "<one sentence: why this registry and type>",
  "suggested_registry_display": "<human readable registry name>",
  "suggested_type_display": "<human readable project type>"
}"""
                                },
                                {
                                    "role": "user",
                                    "content": "Mangrove restoration project in coastal Odisha, India with community involvement and SDG targets"
                                },
                                {
                                    "role": "assistant",
                                    "content": '{"registry": "gold_standard", "project_type": "blue_carbon", "confidence": 0.95, "reasoning": "Community-based mangrove restoration with SDG focus aligns best with Gold Standard blue carbon methodology.", "suggested_registry_display": "Gold Standard (GS4GG)", "suggested_type_display": "Blue Carbon / Mangrove"}'
                                },
                                {
                                    "role": "user",
                                    "content": "Large scale avoided deforestation project in Amazon basin, corporate funded"
                                },
                                {
                                    "role": "assistant",
                                    "content": '{"registry": "verra", "project_type": "redd_plus", "confidence": 0.95, "reasoning": "Large-scale corporate avoided deforestation in Amazon is a classic Verra REDD+ use case.", "suggested_registry_display": "Verra / VCS", "suggested_type_display": "REDD+ / Forest Conservation"}'
                                },
                                {
                                    "role": "user",
                                    "content": "Smallholder farmers adopting zero tillage and cover crops in Madhya Pradesh"
                                },
                                {
                                    "role": "assistant",
                                    "content": '{"registry": "gold_standard", "project_type": "soil_organic_carbon", "confidence": 0.90, "reasoning": "Smallholder soil carbon project using zero tillage and cover crops fits Gold Standard SOC methodology.", "suggested_registry_display": "Gold Standard (GS4GG)", "suggested_type_display": "Soil Organic Carbon (SOC)"}'
                                },
                                {
                                    "role": "user",
                                    "content": "Tree plantation project on degraded land in Rajasthan"
                                },
                                {
                                    "role": "assistant",
                                    "content": '{"registry": "gold_standard", "project_type": "afforestation_reforestation", "confidence": 0.90, "reasoning": "Tree plantation on degraded land aligns with afforestation under Gold Standard.", "suggested_registry_display": "Gold Standard (GS4GG)", "suggested_type_display": "Afforestation / Reforestation (A/R)"}'
                                },
                                {
                                    "role": "user",
                                    "content": "Rice paddy methane reduction through alternate wetting and drying in Punjab"
                                },
                                {
                                    "role": "assistant",
                                    "content": '{"registry": "gold_standard", "project_type": "agriculture", "confidence": 0.88, "reasoning": "Rice cultivation methane reduction via water management is covered under Gold Standard agriculture methodology.", "suggested_registry_display": "Gold Standard (GS4GG)", "suggested_type_display": "Agriculture (General)"}'
                                },
                                {
                                    "role": "user",
                                    "content": project_description
                                }
                            ],
                            temperature=0.1
                        )

                        raw = response.choices[0].message.content.strip()
                        raw = raw.replace("```json", "").replace("```", "").strip()
                        raw = re.sub(r",\s*}", "}", raw)
                        raw = re.sub(r",\s*]", "]", raw)
                        result = json.loads(raw)

                        registry_key = result.get("registry", "gold_standard")
                        project_type_key = result.get("project_type", "afforestation_reforestation")

                        # Override registry if user manually selected one
                        if override_registry != "🤖 Auto-detect (recommended)":
                            registry_key = OVERRIDE_REGISTRY_MAP.get(override_registry, registry_key)

                        if registry_key not in db:
                            registry_key = "gold_standard"
                        project_types = db[registry_key].get("project_types", {})
                        if project_type_key not in project_types:
                            project_type_key = list(project_types.keys())[0] if project_types else "afforestation_reforestation"

                        st.session_state["show_results"] = True
                        st.session_state["registry_key"] = registry_key
                        st.session_state["project_type_key"] = project_type_key
                        # If user overrode registry, show that name; else use AI suggestion
                        if override_registry != "🤖 Auto-detect (recommended)":
                            st.session_state["registry_display"] = override_registry
                        else:
                            st.session_state["registry_display"] = result.get("suggested_registry_display", registry_key)
                        st.session_state["project_type_display"] = result.get("suggested_type_display", project_type_key)
                        st.session_state["ai_summary"] = result
                        success = True
                        break

                    except json.JSONDecodeError:
                        last_error = "AI returned invalid response."
                    except Exception as e:
                        last_error = str(e)

                if not success:
                    st.warning(f"⚠️ AI analysis failed ({last_error}). Showing default documents — please refine manually.")
                    st.session_state["show_results"] = True
                    st.session_state["registry_key"] = "gold_standard"
                    st.session_state["project_type_key"] = "afforestation_reforestation"
                    st.session_state["registry_display"] = "🌟 Gold Standard (GS4GG)"
                    st.session_state["project_type_display"] = "🌳 Afforestation / Reforestation (A/R)"
                    st.session_state["ai_summary"] = None

# ─── Safe Card Renderer ───────────────────────────────────────────────────────
def render_doc_card(doc, card_type="doc"):
    title = doc.get("title", "Untitled Document")
    link = doc.get("link", "#")
    desc = doc.get("description", "")

    css_class = {
        "core": "core-card",
        "methodology": "methodology-card",
        "template": "template-card",
        "other": "doc-card"
    }.get(card_type, "doc-card")

    st.markdown(f"""
    <div class="{css_class}">
        <strong><a href="{link}" target="_blank">{title}</a></strong><br>
        <small style="color:#666">{desc}</small>
    </div>
    """, unsafe_allow_html=True)


# ─── Export Builder — HTML Only ──────────────────────────────────────────────
def build_checklist_html(registry_display, project_type_display, registry_data, project_data, registry_key, db):
    """Build a beautiful HTML checklist that opens directly in any browser."""
    now = datetime.now().strftime("%d %b %Y, %H:%M")

    def section_html(icon, title, docs, color, doc_type="link"):
        if not docs:
            return ""
        rows = ""
        for doc in docs:
            t = doc.get("title", "Untitled")
            l = doc.get("link", "#")
            d = doc.get("description", "")
            rows += f"""
            <tr>
                <td style="padding:12px 16px; vertical-align:top; width:28px;">
                    <input type="checkbox" style="width:16px;height:16px;cursor:pointer;accent-color:{color};">
                </td>
                <td style="padding:12px 8px 12px 0;">
                    <a href="{l}" target="_blank" style="color:#1a4731;font-weight:600;text-decoration:none;font-size:0.95rem;">{t}</a><br>
                    <span style="color:#666;font-size:0.82rem;">{d}</span>
                </td>
            </tr>"""
        return f"""
        <div style="margin-bottom:28px;">
            <div style="background:{color};color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:700;font-size:1rem;">
                {icon} {title} &nbsp;<span style="font-weight:400;font-size:0.85rem;opacity:0.85;">({len(docs)} documents)</span>
            </div>
            <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;overflow:hidden;">
                {rows}
            </table>
        </div>"""

    # Build all sections
    sections = ""

    # SDG Tool (GS only)
    if registry_key == "gold_standard" and "sdg_tool" in db.get("gold_standard", {}):
        sdg = db["gold_standard"]["sdg_tool"]
        sections += section_html("🎯", "SDG Impact Tool — Required for ALL GS Projects", [sdg], "#7b1fa2")

    sections += section_html("🔴", f"Core Documents — Required for ALL {registry_data.get('display_name','')} Projects",
                             registry_data.get("core_documents", []), "#c62828")

    sections += section_html("🟡", "Activity Requirements — Specific to This Project Type",
                             project_data.get("activity_requirements", []), "#f57f17")

    sections += section_html("🟢", "Methodologies",
                             project_data.get("methodologies", []), "#2e7d32")

    sections += section_html("📋", "Templates",
                             project_data.get("templates", []), "#f59e0b")

    sections += section_html("📎", "Other Important Documents",
                             project_data.get("other_docs", []), "#1565c0")

    registry_website = registry_data.get("website", "#")
    reg_name = registry_data.get("display_name", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Carbon Project Checklist — {project_type_display}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f6f4; color: #222; }}
  .container {{ max-width: 860px; margin: 0 auto; padding: 32px 20px; }}
  .header {{ background: linear-gradient(135deg, #1a4731 0%, #2d7a4f 100%); color: white; padding: 28px 32px; border-radius: 12px; margin-bottom: 28px; }}
  .header h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
  .meta {{ display: flex; gap: 24px; flex-wrap: wrap; margin-top: 12px; font-size: 0.88rem; opacity: 0.9; }}
  .meta span {{ background: rgba(255,255,255,0.15); padding: 4px 12px; border-radius: 20px; }}
  .print-btn {{ background: white; color: #1a4731; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.9rem; float: right; margin-top: -4px; }}
  .print-btn:hover {{ background: #e8f5e9; }}
  .tip {{ background: #e8f5e9; border-left: 4px solid #2d7a4f; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 28px; font-size: 0.9rem; color: #1a4731; }}
  table tr:hover {{ background: #fafafa; }}
  .footer {{ text-align: center; color: #888; font-size: 0.82rem; margin-top: 32px; padding-top: 16px; border-top: 1px solid #ddd; }}
  a:hover {{ text-decoration: underline !important; }}
  @media print {{
    .print-btn {{ display: none; }}
    body {{ background: white; }}
    .container {{ padding: 0; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <button class="print-btn" onclick="window.print()">🖨️ Print / Save PDF</button>
    <h1>📋 Carbon Project Document Checklist</h1>
    <div class="meta">
      <span>🏛️ {registry_display}</span>
      <span>🌿 {project_type_display}</span>
      <span>📅 Generated: {now}</span>
    </div>
  </div>

  <div class="tip">
    ✅ <strong>How to use:</strong> Click each checkbox as you review and collect the document. Click any document title to open it directly.
    &nbsp;·&nbsp; <a href="{registry_website}" target="_blank" style="color:#1a4731;font-weight:600;">🌐 Visit {reg_name} Official Website</a>
  </div>

  {sections}

  <div class="footer">
    Generated by <strong>Carbon Standards Document Finder</strong> · Flora Carbon<br>
    All links open the latest publicly available version from the official registry website.
  </div>
</div>
</body>
</html>"""
    return html


def count_total_docs(registry_data, project_data, registry_key, db):
    """Count total documents for this selection."""
    total = 0
    if registry_key == "gold_standard" and "sdg_tool" in db.get("gold_standard", {}):
        total += 1
    total += len(registry_data.get("core_documents", []))
    total += len(project_data.get("activity_requirements", []))
    total += len(project_data.get("methodologies", []))
    total += len(project_data.get("templates", []))
    total += len(project_data.get("other_docs", []))
    return total


# ─── Results ──────────────────────────────────────────────────────────────────
if st.session_state.get("show_results"):
    with st.spinner("📄 Loading documents..."):
        registry_key = st.session_state["registry_key"]
        project_type_key = st.session_state["project_type_key"]
        registry_data = db.get(registry_key, {})
        project_data = registry_data.get("project_types", {}).get(project_type_key, {})

    st.markdown("---")
    st.markdown(f"## 📄 Documents for: **{st.session_state['project_type_display']}** under **{st.session_state['registry_display']}**")

    # #1 Registry website link
    registry_website = registry_data.get("website", "#")
    st.markdown(f"🌐 [Visit Official Registry Website]({registry_website})", unsafe_allow_html=False)

    # #2 Empty state check
    if not project_data:
        st.warning("⚠️ No documents found for this selection. Please try another combination.")
        st.stop()

    # AI Summary box
    if st.session_state.get("ai_summary"):
        ai = st.session_state["ai_summary"]
        confidence_pct = int(float(ai.get("confidence", 0)) * 100)
        confidence_color = "#4caf50" if confidence_pct >= 70 else "#ff9800"
        st.markdown(f"""
        <div class="ai-analysis">
            🤖 <strong>AI Analysis</strong> &nbsp;|&nbsp;
            Confidence: <span style="color:{confidence_color}; font-weight:bold">{confidence_pct}%</span><br>
            <small>{ai.get('reasoning', '')}</small>
        </div>
        """, unsafe_allow_html=True)
        if confidence_pct < 70:
            st.warning("⚠️ Confidence is below 70%. Please review the document selection carefully.")
        st.info("📌 These documents are required based on the registry standards and methodology for your selected project type. Core documents apply to all projects; methodologies and templates are specific to this activity.")
    else:
        st.info("📌 Documents shown are based on your selected registry and project type. Core documents are required for all projects under this registry; methodologies and templates are specific to this activity type.")

    # ─── Export / Checklist Section ───────────────────────────────────────────
    total_docs = count_total_docs(registry_data, project_data, registry_key, db)
    registry_display_clean = st.session_state["registry_display"].replace("🌟 ", "").replace("✅ ", "").replace("🔷 ", "")
    project_display_clean = st.session_state["project_type_display"].replace("🌳 ", "").replace("🌱 ", "").replace("🌊 ", "").replace("🌲 ", "").replace("🌾 ", "")
    safe_name = f"{registry_display_clean}_{project_display_clean}".replace(" ", "_").replace("/", "-").replace("(", "").replace(")", "")

    st.markdown(f"""
    <div class="export-box">
        <strong>📥 Export Your Document Checklist</strong> &nbsp;·&nbsp;
        <span style="color:#166534">{total_docs} documents found</span><br>
        <small style="color:#555">Download as Markdown checklist or CSV spreadsheet to track your project documentation.</small>
    </div>
    """, unsafe_allow_html=True)

    html_content = build_checklist_html(
        st.session_state["registry_display"],
        st.session_state["project_type_display"],
        registry_data, project_data, registry_key, db
    )
    st.download_button(
        label="⬇️ Download Checklist (opens in browser)",
        data=html_content,
        file_name=f"checklist_{safe_name}.html",
        mime="text/html",
        use_container_width=True,
        type="primary"
    )

    # ─── Document Sections ────────────────────────────────────────────────────

    # SDG Tool (GS only)
    if registry_key == "gold_standard" and "sdg_tool" in db["gold_standard"]:
        sdg = db["gold_standard"]["sdg_tool"]
        st.markdown("""<div class="section-header">🎯 SDG Impact Tool (Required for ALL GS Projects)</div>""", unsafe_allow_html=True)
        render_doc_card(sdg, "core")

    # Core Documents
    core_docs = registry_data.get("core_documents", [])
    if core_docs:
        st.markdown(f"""<div class="section-header">🔴 Core Documents — Required for ALL {registry_data.get('display_name', '')} Projects ({len(core_docs)})</div>""", unsafe_allow_html=True)
        for doc in core_docs:
            render_doc_card(doc, "core")
    else:
        st.info("No core documents found for this registry.")

    # Activity Requirements
    activity_reqs = project_data.get("activity_requirements", [])
    if activity_reqs:
        st.markdown(f"""<div class="section-header">🟡 Activity Requirements — Specific to This Project Type ({len(activity_reqs)})</div>""", unsafe_allow_html=True)
        for doc in activity_reqs:
            render_doc_card(doc, "doc")

    # Methodologies
    methodologies = project_data.get("methodologies", [])
    if methodologies:
        st.markdown(f"""<div class="section-header">🟢 Methodologies ({len(methodologies)})</div>""", unsafe_allow_html=True)
        for doc in methodologies:
            render_doc_card(doc, "methodology")
    else:
        st.info("No methodologies listed for this project type.")

    # Templates
    templates = project_data.get("templates", [])
    if templates:
        st.markdown(f"""<div class="section-header">📋 Templates ({len(templates)})</div>""", unsafe_allow_html=True)
        with st.expander(f"View {len(templates)} Templates", expanded=False):
            for doc in templates:
                render_doc_card(doc, "template")
    else:
        st.info("No templates found for this project type.")

    # Other Docs
    other_docs = project_data.get("other_docs", [])
    if other_docs:
        st.markdown(f"""<div class="section-header">📎 Other Important Documents ({len(other_docs)})</div>""", unsafe_allow_html=True)
        for doc in other_docs:
            render_doc_card(doc, "other")

    st.markdown("---")
    st.caption("💡 All links open the latest publicly available version from the official registry website.")

    # Reset button
    if st.button("🔄 Search Again", use_container_width=True):
        st.session_state["show_results"] = False
        st.session_state["ai_summary"] = None
        st.rerun()
