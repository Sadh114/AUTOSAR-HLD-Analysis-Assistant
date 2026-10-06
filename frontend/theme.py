"""Custom 'Engineering Blueprint' theme injected as raw CSS into the
Streamlit app. Dark navy blueprint-grid background, cyan schematic-line
accents, monospace type for citations/technical text."""

BLUEPRINT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bp-bg: #0a1929;
    --bp-bg-alt: #0f2540;
    --bp-grid: rgba(90, 169, 230, 0.10);
    --bp-cyan: #4fd1ff;
    --bp-cyan-soft: rgba(79, 209, 255, 0.15);
    --bp-amber: #ffb454;
    --bp-green: #6ee7b7;
    --bp-red: #ff8080;
    --bp-text: #e6f1ff;
    --bp-text-dim: #9db4cc;
    --bp-border: rgba(79, 209, 255, 0.35);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        repeating-linear-gradient(0deg, var(--bp-grid) 0px, var(--bp-grid) 1px, transparent 1px, transparent 32px),
        repeating-linear-gradient(90deg, var(--bp-grid) 0px, var(--bp-grid) 1px, transparent 1px, transparent 32px),
        linear-gradient(180deg, var(--bp-bg) 0%, var(--bp-bg-alt) 100%);
    color: var(--bp-text);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #081827 0%, #0c1f36 100%);
    border-right: 1px solid var(--bp-border);
}

/* Streamlit's default top header bar + rainbow decoration line */
header[data-testid="stHeader"] {
    background: var(--bp-bg) !important;
    background-image: none !important;
}
div[data-testid="stDecoration"] {
    background: linear-gradient(90deg, var(--bp-cyan), #1c5079) !important;
    height: 3px !important;
}
[data-testid="stToolbar"] {
    background: transparent !important;
}

/* Streamlit's built-in hamburger menu (Rerun/Settings/Print/About) is
   rendered with a hardcoded white popover background; our global text-color
   override otherwise makes its light text invisible on that white panel. */
[data-testid="stMainMenuPopover"],
[data-testid="stMainMenuPopover"] > div {
    background: var(--bp-bg-alt) !important;
    border: 1px solid var(--bp-border) !important;
}
[data-testid="stMainMenuPopover"] * {
    color: var(--bp-text) !important;
    background: transparent !important;
}
[data-testid="main-menu-list"] li:hover {
    background: var(--bp-cyan-soft) !important;
}

/* Any Streamlit dialog/modal (e.g. "Record a screencast") renders on a
   hardcoded white surface; theme it to match instead of leaving our
   light global text color unreadable on white. */
div[role="dialog"] {
    background: var(--bp-bg-alt) !important;
    border: 1px solid var(--bp-border) !important;
}
div[role="dialog"] * {
    color: var(--bp-text) !important;
}
div[role="dialog"] button {
    background: linear-gradient(135deg, #0f2f4d, #143a5e) !important;
    border: 1px solid var(--bp-border) !important;
    color: var(--bp-cyan) !important;
}

/* st.link_button renders as an anchor styled like a button; give it the
   same treatment as our other buttons instead of Streamlit's default
   white pill (which made the label unreadable against this dark theme). */
[data-testid="stLinkButton"] a {
    background: linear-gradient(135deg, #0f2f4d, #143a5e) !important;
    color: var(--bp-cyan) !important;
    border: 1px solid var(--bp-border) !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}
[data-testid="stLinkButton"] a:hover {
    background: linear-gradient(135deg, #143a5e, #1c5079) !important;
    border-color: var(--bp-cyan) !important;
    color: #ffffff !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'JetBrains Mono', monospace;
    color: var(--bp-cyan) !important;
    letter-spacing: 0.5px;
}

h1 {
    text-shadow: 0 0 18px rgba(79, 209, 255, 0.35);
    border-bottom: 1px dashed var(--bp-border);
    padding-bottom: 12px;
}

/* Streamlit markdown body headings (h4 used for section titles) need
   full opacity + a visible weight, since the default theme renders
   them dim/translucent against a dark background. */
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5 {
    opacity: 1 !important;
    color: var(--bp-cyan) !important;
    font-weight: 700 !important;
}

p, span, label, div {
    color: var(--bp-text);
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, #0f2f4d, #143a5e);
    color: var(--bp-cyan);
    border: 1px solid var(--bp-border);
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.15s ease-in-out;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #143a5e, #1c5079);
    border-color: var(--bp-cyan);
    box-shadow: 0 0 12px rgba(79, 209, 255, 0.45);
    color: #ffffff;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid var(--bp-border);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(79, 209, 255, 0.06);
    border-radius: 6px 6px 0 0;
    font-family: 'JetBrains Mono', monospace;
    color: var(--bp-text-dim);
    padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
    background: var(--bp-cyan-soft) !important;
    color: var(--bp-cyan) !important;
    border-bottom: 2px solid var(--bp-cyan);
}

/* Inputs (text box, textarea, selects) — target both the wrapper and the
   actual <input>/<textarea> element, since Streamlit's BaseWeb widgets
   set their own inline background that otherwise wins over a looser rule. */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
div[data-baseweb="select"] > div {
    background-color: #0f2540 !important;
    border: 1px solid var(--bp-border) !important;
    border-radius: 6px !important;
}
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] span {
    background-color: transparent !important;
    color: var(--bp-text) !important;
    -webkit-text-fill-color: var(--bp-text) !important;
    caret-color: var(--bp-cyan) !important;
}
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: var(--bp-text-dim) !important;
    opacity: 1 !important;
}
/* Focused state: keep the cyan theme instead of Streamlit's default red */
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: var(--bp-cyan) !important;
    box-shadow: 0 0 0 1px var(--bp-cyan) !important;
}

/* Citation / evidence cards */
.bp-card {
    background: rgba(15, 47, 77, 0.55);
    border: 1px solid var(--bp-border);
    border-left: 3px solid var(--bp-cyan);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--bp-text-dim);
}
.bp-card .bp-card-title {
    color: var(--bp-cyan);
    font-weight: 700;
    margin-bottom: 6px;
    display: block;
}

/* Answer panel */
.bp-answer {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--bp-border);
    border-radius: 10px;
    padding: 18px 20px;
    margin: 10px 0 18px 0;
    line-height: 1.55;
}

/* Confidence badges */
.bp-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.bp-badge-high { background: rgba(110, 231, 183, 0.15); color: var(--bp-green); border: 1px solid var(--bp-green); }
.bp-badge-medium { background: rgba(255, 180, 84, 0.15); color: var(--bp-amber); border: 1px solid var(--bp-amber); }
.bp-badge-low, .bp-badge-error, .bp-badge-noevidence {
    background: rgba(255, 128, 128, 0.15); color: var(--bp-red); border: 1px solid var(--bp-red);
}

/* Status badges for comparison */
.bp-status-modified { color: var(--bp-amber); font-weight: 700; }
.bp-status-onlyina { color: var(--bp-cyan); font-weight: 700; }
.bp-status-onlyinb { color: #b18cff; font-weight: 700; }
.bp-status-added { color: var(--bp-green); font-weight: 700; }
.bp-status-removed { color: var(--bp-red); font-weight: 700; }

/* Header banner */
.bp-banner {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 22px;
    background: linear-gradient(90deg, rgba(79,209,255,0.10), transparent);
    border: 1px solid var(--bp-border);
    border-radius: 10px;
    margin-bottom: 18px;
}
.bp-banner .bp-icon {
    font-size: 2.2rem;
    filter: drop-shadow(0 0 8px rgba(79,209,255,0.6));
}
.bp-banner .bp-sub {
    color: var(--bp-text-dim);
    font-size: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Divider blueprint style */
.bp-divider {
    border: none;
    border-top: 1px dashed var(--bp-border);
    margin: 18px 0;
}

/* Document chips in sidebar */
.bp-doc-chip {
    background: rgba(79, 209, 255, 0.08);
    border: 1px solid var(--bp-border);
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(15, 47, 77, 0.45) !important;
    border: 1px dashed var(--bp-border) !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: var(--bp-text-dim) !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: linear-gradient(135deg, #0f2f4d, #143a5e) !important;
    color: var(--bp-cyan) !important;
    border: 1px solid var(--bp-border) !important;
}
[data-testid="stFileUploaderDropzone"] svg {
    fill: var(--bp-cyan) !important;
}

/* Alerts (success/error/info/warning) */
[data-testid="stAlertContainer"] {
    background: rgba(15, 47, 77, 0.55) !important;
    border: 1px solid var(--bp-border) !important;
    border-radius: 8px !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid var(--bp-border);
    border-radius: 8px;
    overflow: hidden;
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bp-bg); }
::-webkit-scrollbar-thumb { background: var(--bp-border); border-radius: 8px; }
</style>
"""
