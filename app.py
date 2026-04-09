import streamlit as st
import json
import os
from openai import OpenAI

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gold Standard Document Finder",
    page_icon="🌿",
    layout="wide"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8faf8; }
    .stApp { font-family: 'Segoe UI', sans-serif; }

    .hero-box {
        background: linear-gradient(135deg, #1a6b3c, #2d9e5f);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
    }
    .hero-box h1 { font-size: 2rem; margin-bottom: 0.3rem; }
    .hero-box p  { font-size: 1rem; opacity: 0.9; margin: 0; }

    .section-red {
        background: #fff5f5;
        border-left: 5px solid #e53e3e;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .section-yellow {
        background: #fffbeb;
        border-left: 5px solid #d69e2e;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .section-green {
        background: #f0fff4;
        border-left: 5px solid #38a169;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
        color: #2d3748;
    }
    .doc-card {
        background: white;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .doc-title { font-weight: 600; color: #2d3748; font-size: 0.92rem; }
    .doc-desc  { color: #718096; font-size: 0.82rem; margin-top: 2px; }

    .confidence-badge-high {
        background: #c6f6d5; color: #22543d;
        padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .confidence-badge-medium {
        background: #fefcbf; color: #744210;
        padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .confidence-badge-low {
        background: #fed7d7; color: #742a2a;
        padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .result-header {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #e2e8f0;
    }
    .activity-tag {
        background: #e6fffa; color: #234e52;
        padding: 4px 12px; border-radius: 20px;
        font-size: 0.85rem; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─── Load JSON DB ───────────────────────────────────────────────────────────────
@st.cache_data
def load_db():
    with open("gs_documents.json", "r") as f:
        return json.load(f)

db = load_db()

# ─── OpenAI Key from env ────────────────────────────────────────────────────────
env_api_key = os.getenv("OPENAI_API_KEY", "")

# ─── LLM Mapping Function ───────────────────────────────────────────────────────
def analyze_project(user_input: str, api_key: str) -> dict:
    import httpx
    client = OpenAI(api_key=api_key, http_client=httpx.Client())

    system_prompt = """You are an expert in carbon markets and Gold Standard certification.

Your job is to analyze a project description and extract structured information.

You MUST respond with ONLY valid JSON — no explanation, no markdown, no extra text.

Return exactly this structure:
{
  "activity_type": "<one of: agriculture, forestry, renewable_energy, community_services, blue_carbon, engineered_removals, waste>",
  "secondary_activity_type": "<optional second type or null>",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "confidence": <number between 0.0 and 1.0>,
  "project_summary": "<1 sentence summary of what the project does>",
  "low_confidence_reason": "<if confidence < 0.7, explain why, else null>"
}

Activity type definitions:
- agriculture: farming, crops, livestock, soil carbon, rice, dairy, biochar from agricultural waste
- forestry: tree planting, afforestation, reforestation, REDD+, forest conservation
- renewable_energy: solar, wind, hydro, bioenergy, electrification, fuel switch, EV, transport
- community_services: cookstoves, clean cooking, safe water, WASH, household energy
- blue_carbon: mangroves, wetlands, seagrass, coastal ecosystems, macroalgae
- engineered_removals: biochar (industrial scale), CCS, BECCS, DAC, carbon mineralisation
- waste: landfill, recycling, solid waste, organic waste processing, composting"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Project description: {user_input}"}
        ],
        temperature=0.1,
        max_tokens=400
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)

# ─── Document Bundle Builder ────────────────────────────────────────────────────
def build_document_bundle(analysis: dict) -> dict:
    activity_type = analysis.get("activity_type")
    secondary = analysis.get("secondary_activity_type")
    keywords = [k.lower() for k in analysis.get("keywords", [])]
    keyword_string = " ".join(keywords)

    # Activity requirements
    activity_req = []
    if activity_type and activity_type in db["activity_requirements"]:
        activity_req.append(db["activity_requirements"][activity_type])
    if secondary and secondary in db["activity_requirements"] and secondary != activity_type:
        activity_req.append(db["activity_requirements"][secondary])

    # Methodology matching — BOTH activity_type AND keywords must match
    matched_methodologies = []
    for m in db["methodologies"]:
        m_keywords = [k.lower() for k in m.get("keywords", [])]
        m_types = m.get("activity_types", [])
        keyword_match = any(kw in keyword_string for kw in m_keywords)
        type_match = activity_type in m_types or (secondary and secondary in m_types)
        # Require BOTH to match — prevents wrong cross-type suggestions
        if keyword_match and type_match:
            matched_methodologies.append(m)
        # Fallback: if no keyword match but type matches strongly, still include
        # (handles generic descriptions like "solar project")
        elif type_match and not matched_methodologies:
            matched_methodologies.append(m)

    # Product requirements
    product_reqs = []
    for pr in db["product_requirements"]:
        applicable = pr.get("applicable_to", [])
        if "all" in applicable or activity_type in applicable or (secondary and secondary in applicable):
            product_reqs.append(pr)

    return {
        "core_documents": db["core_documents"],
        "sdg_tools": db["sdg_tools"],
        "methodology_procedures": db["methodology_procedures"],
        "activity_requirements": activity_req,
        "methodologies": matched_methodologies,
        "product_requirements": product_reqs
    }

# ─── Render Doc Card ───────────────────────────────────────────────────────────
def render_doc(doc):
    title = doc.get("title", "")
    link = doc.get("link", "#")
    desc = doc.get("description", "")
    st.markdown(f"""
    <div class="doc-card">
        <div class="doc-title">📄 {title}</div>
        <div class="doc-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"[🔗 Open Document]({link})")

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>🌿 Gold Standard Document Finder</h1>
    <p>Describe your carbon project — get every Gold Standard document you need, instantly.</p>
</div>
""", unsafe_allow_html=True)

# ─── Input ─────────────────────────────────────────────────────────────────────
col_input, col_key = st.columns([3, 1])

with col_input:
    user_input = st.text_area(
        "📝 Describe your project",
        placeholder="e.g. I want to distribute improved cookstoves to rural households in Kenya...\ne.g. Solar mini-grid electrification in rural India\ne.g. Afforestation using native trees in degraded land in Brazil",
        height=130
    )

with col_key:
    st.markdown("<br>", unsafe_allow_html=True)
    api_key_input = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        value=env_api_key,
        help="Your OpenAI API key. Starts with sk-"
    )
    find_btn = st.button("🔍 Find My Documents", type="primary", use_container_width=True)

st.markdown("---")

# ─── Results ───────────────────────────────────────────────────────────────────
if find_btn:
    if not user_input.strip():
        st.warning("⚠️ Please describe your project first!")
    elif not api_key_input.strip():
        st.warning("⚠️ Please enter your OpenAI API key!")
    else:
        with st.spinner("🤔 Analyzing your project and finding relevant documents..."):
            try:
                analysis = analyze_project(user_input, api_key_input.strip())
                bundle = build_document_bundle(analysis)

                confidence = analysis.get("confidence", 0)
                activity_type_raw = analysis.get("activity_type", "Unknown")
                activity_type = activity_type_raw.replace("_", " ").title()
                secondary = analysis.get("secondary_activity_type")
                summary = analysis.get("project_summary", "")

                # ── Confidence-based methodology limiting ──
                # High confidence (≥0.7) → top 2 (precise, no noise)
                # Low confidence  (<0.7) → top 3 + review warning
                all_methodologies = bundle["methodologies"]
                if confidence >= 0.7:
                    methodologies_to_show = all_methodologies[:2]
                    show_review_warning = False
                else:
                    methodologies_to_show = all_methodologies[:3]
                    show_review_warning = True

                # Confidence badge
                if confidence >= 0.75:
                    badge = f'<span class="confidence-badge-high">✅ High Confidence {int(confidence*100)}%</span>'
                elif confidence >= 0.5:
                    badge = f'<span class="confidence-badge-medium">⚠️ Medium Confidence {int(confidence*100)}%</span>'
                else:
                    badge = f'<span class="confidence-badge-low">❗ Low Confidence {int(confidence*100)}%</span>'

                secondary_tag = ""
                secondary_label = ""
                if secondary:
                    secondary_tag = f' + <span class="activity-tag">{secondary.replace("_"," ").title()}</span>'
                    secondary_label = f" – {secondary.replace('_',' ').title()}"

                # ── Trust Line ──
                st.markdown(f"""
                <div class="result-header">
                    <div style="font-weight:700; font-size:1.05rem; color:#2d3748; margin-bottom:6px;">
                        ✅ We've identified your project as: 
                        <span class="activity-tag">{activity_type}{secondary_label}</span>
                        &nbsp;&nbsp;{badge}
                    </div>
                    <div style="color:#718096; font-size:0.88rem; margin-top:4px;">{summary}</div>
                </div>
                """, unsafe_allow_html=True)

                if show_review_warning:
                    reason = analysis.get("low_confidence_reason", "")
                    st.warning(f"⚠️ Low confidence match — {reason}\n\nWe're showing you 3 methodology options. Please review carefully and pick the one that fits your project.")

                # 🔴 MUST READ
                st.markdown('<div class="section-red"><div class="section-title">🔴 Must Read — Required for ALL Projects</div><div style="color:#718096;font-size:0.85rem;">These documents apply to every Gold Standard project regardless of type.</div></div>', unsafe_allow_html=True)

                with st.expander("📚 Core Documents", expanded=True):
                    for doc in bundle["core_documents"]:
                        render_doc(doc)

                with st.expander("🛠️ SDG Impact Tools", expanded=True):
                    for doc in bundle["sdg_tools"]:
                        render_doc(doc)

                with st.expander("📐 Additionality, Baseline & Leakage Requirements", expanded=False):
                    for doc in bundle["methodology_procedures"]:
                        render_doc(doc)

                # 🟡 BASED ON YOUR PROJECT
                st.markdown('<div class="section-yellow"><div class="section-title">🟡 Based On Your Project — Filtered for You</div><div style="color:#718096;font-size:0.85rem;">These documents are selected based on your project type and activity.</div></div>', unsafe_allow_html=True)

                with st.expander("📋 Activity Requirements", expanded=True):
                    if bundle["activity_requirements"]:
                        for doc in bundle["activity_requirements"]:
                            render_doc(doc)
                    else:
                        st.info("No specific activity requirement matched. Check the full list at globalgoals.goldstandard.org")

                method_label = "top 2 — high confidence" if confidence >= 0.7 else "top 3 — please review carefully"
                with st.expander(f"🔬 Suggested Methodologies ({len(methodologies_to_show)} shown — {method_label})", expanded=True):
                    if methodologies_to_show:
                        for doc in methodologies_to_show:
                            render_doc(doc)
                    else:
                        st.info("No specific methodology matched. Try adding more detail — e.g. crop type, technology used, or scale of project.")

                # 🟢 FOR PROJECT COMPLETION
                st.markdown('<div class="section-green"><div class="section-title">🟢 For Project Completion — Review Which Apply</div><div style="color:#718096;font-size:0.85rem;">These may be required depending on your project stage and structure.</div></div>', unsafe_allow_html=True)

                with st.expander("📦 Product Requirements", expanded=False):
                    if bundle["product_requirements"]:
                        st.caption("ℹ️ Review which of these apply to your specific project stage.")
                        for doc in bundle["product_requirements"]:
                            render_doc(doc)

                st.markdown("---")
                st.caption("📌 This tool provides guidance only. Always verify with official Gold Standard documentation at [globalgoals.goldstandard.org](https://globalgoals.goldstandard.org).")

            except json.JSONDecodeError:
                st.error("❌ Could not parse AI response. Try rephrasing your project description.")
            except Exception as e:
                st.error(f"❌ Something went wrong: {str(e)}")

# ─── Empty State ───────────────────────────────────────────────────────────────
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("💡 **Example Projects**\n\n- Cookstoves in Kenya\n- Solar mini-grid India\n- Mangrove restoration\n- Biochar from rice husk")
    with c2:
        st.info("📂 **What You'll Get**\n\n- 🔴 Core docs (always required)\n- 🟡 Activity & methodology docs\n- 🟢 Product completion docs")
    with c3:
        st.info("⚡ **How It Works**\n\n1. Describe your project\n2. AI identifies type\n3. Relevant docs shown\n4. Click to open each doc")
