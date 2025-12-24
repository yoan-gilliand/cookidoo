"""
Cookidoo Recipe Creator - Streamlit UI with Gemini AI

A chat interface for creating Thermomix recipes using Gemini AI with Cookidoo tools.
"""

import streamlit as st
import asyncio
import json
import re
import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
from cookidoo_service import CookidooService
from schemas import CustomRecipe
import extra_streamlit_components as stx
import datetime
import hashlib
import time

# Page configuration
st.set_page_config(
    page_title="Créateur de Recettes Cookidoo",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Modern minimalist liquid glass CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Dark theme base */
    .stApp {
        background: linear-gradient(145deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
    }
    
    .main .block-container {
        max-width: 800px;
        padding-top: 2rem;
        padding-bottom: 6rem;
    }
    
    /* Header */
    h1 {
        font-weight: 600 !important;
        font-size: 2rem !important;
        color: #ffffff !important;
        text-align: center;
        letter-spacing: -0.02em;
    }
    
    /* Subtext */
    .subtitle {
        text-align: center;
        color: rgba(255,255,255,0.5);
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    
    /* Glass card */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* Welcome card */
    .welcome-card {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
    }
    
    .welcome-card h3 {
        color: #ffffff !important;
        font-weight: 500 !important;
        margin-bottom: 1.5rem !important;
    }
    
    /* Steps grid - 2x2 layout */
    .steps-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .step-item {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 1.25rem;
        border-radius: 12px;
        text-align: left;
        transition: all 0.2s ease;
    }
    
    .step-item:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.12);
        transform: translateY(-2px);
    }
    
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
        border-radius: 50%;
        font-size: 0.85rem;
        font-weight: 600;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.75rem;
    }
    
    .step-text {
        color: rgba(255,255,255,0.75);
        font-size: 0.9rem;
        line-height: 1.4;
    }
    
    .welcome-card .step {
        display: inline-block;
        background: rgba(255,255,255,0.05);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.3rem;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.7);
    }
    
    /* Chat messages */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
    }
    
    [data-testid="stChatMessageContent"] {
        color: rgba(255,255,255,0.9) !important;
    }
    
    /* Chat input styles - Removed early definition to consolidate at the bottom */
    
    /* Chat input send button */
    [data-testid="stChatInput"] button {
        background: rgba(255, 255, 255, 0.08) !important;
        border: none !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stChatInput"] button:hover {
        background: rgba(255, 255, 255, 0.15) !important;
    }
    
    [data-testid="stChatInput"] button svg {
        fill: rgba(255,255,255,0.8) !important;
    }
    
    /* Buttons - consistent style */
    .stButton > button {
        background: rgba(255, 255, 255, 0.06) !important;
        color: rgba(255,255,255,0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.25s ease !important;
    }
    
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* File uploader - improved contrast for accessibility */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px dashed rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: rgba(255,255,255,0.8) !important;
    }
    
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 10px !important;
    }
    
    /* Fix contrast in file uploader dropzone text */
    [data-testid="stFileUploaderDropzone"] span {
        color: rgba(255,255,255,0.7) !important;
    }
    
    [data-testid="stFileUploaderDropzone"] small {
        color: rgba(255,255,255,0.5) !important;
    }
    
    /* File uploader button - consistent with other buttons */
    [data-testid="stFileUploaderDropzone"] button {
        background: rgba(255, 255, 255, 0.08) !important;
        color: rgba(255,255,255,0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
    }
    
    /* Upload section container */
    .upload-section {
        display: flex;
        align-items: stretch;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }
    
    /* Success/Info/Error */
    .stSuccess, .stInfo {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.8) !important;
    }
    
    .stError {
        background: rgba(255, 80, 80, 0.12) !important;
        border: 1px solid rgba(255, 80, 80, 0.25) !important;
        border-radius: 12px !important;
        color: rgba(255,200,200,0.95) !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: rgba(255,255,255,0.2) !important;
        border-top-color: rgba(255,255,255,0.8) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.8) !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Hide sidebar */
    [data-testid="stSidebar"] {display: none;}
    
    /* Image preview */
    .uploaded-image {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
        max-height: 200px;
        object-fit: cover;
    }
    
    /* Action buttons row */
    .action-row {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Login card specific styles */
    .login-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 2.5rem;
        margin: 2rem auto;
        max-width: 400px;
        text-align: center;
    }
    
    .login-card h3 {
        color: #ffffff !important;
        font-weight: 500 !important;
        margin-bottom: 0.5rem !important;
        font-size: 1.5rem !important;
    }
    
    .login-card p {
        color: rgba(255,255,255,0.5);
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    
    /* Password input styling */
    [data-testid="stTextInput"] input {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.95) !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
    }
    
    [data-testid="stTextInput"] input:focus {
        border-color: rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.05) !important;
    }
    
    [data-testid="stTextInput"] input::placeholder {
        color: rgba(255,255,255,0.4) !important;
    }
    
    /* Eye icon in password field */
    [data-testid="stTextInput"] button {
        color: rgba(255,255,255,0.5) !important;
    }
    
    [data-testid="stTextInput"] button:hover {
        color: rgba(255,255,255,0.8) !important;
    }
    
    /* Fix mobile UI issues */
    /* Force bottom container background to match theme (removes white gap on mobile) */
    [data-testid="stBottom"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    [data-testid="stBottom"] > div {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Force chat input container background to be distinct but integrated */
    .stChatInputContainer {
        bottom: 0px !important;
        background: rgba(10, 10, 15, 0.95);
        backdrop-filter: blur(20px);
        padding-bottom: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Ensure bot text is white even if mobile browser tries to style it */
    [data-testid="stMarkdownContainer"] p {
        color: rgba(255,255,255,0.9) !important;
    }
    
    /* Fix native mobile input styles */
    input, textarea {
        appearance: none;
        -webkit-appearance: none;
        background-color: transparent !important; 
    }
    
    /* Specific fix for footer overlapping or floating */
    footer {
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    
    /* Header container spacing fix */
    [data-testid="stHeader"] {
        display: none !important;
        height: 0px !important;
    }
    
    /* Force remove the massive default top padding */
    [data-testid="stMainBlockContainer"] {
        padding-top: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 6rem !important;
        max-width: 100% !important;
    }
    
    /* Mobile-specific adjustments */
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding-top: 0.5rem !important; /* Extremely minimal top padding */
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-bottom: 0.5rem !important; 
        }
        
        /* Reduce header size on mobile */
        h1 {
            font-size: 1.5rem !important;
            margin-bottom: 0.5rem !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        .subtitle {
            font-size: 0.85rem !important;
            margin-bottom: 1.5rem !important;
        }
        
        /* Anchor chat input to bottom */
        .stChatInputContainer {
            bottom: 0px !important;
            position: fixed !important;
            width: 100% !important;
            left: 0 !important;
            right: 0 !important;
            padding: 1rem 1rem 1rem 1rem !important;
            background: #0a0a0f !important; /* Solid completely opaque background */
            border-top: 1px solid rgba(255,255,255,0.1);
            z-index: 999999 !important;
        }
        
        [data-testid="stChatInput"] {
            padding-bottom: 0 !important;
        }
    }
    
    /* Chat input styles */
    [data-testid="stChatInput"] > div {
        background-color: #1e1e24 !important; 
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important; 
        padding-right: 0.5rem !important;
        padding-left: 0.5rem !important;
        align-items: center !important;
    }

    /* Chat input textarea */
    [data-testid="stChatInputTextArea"] {
        background-color: #1e1e24 !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0.4rem 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: 24px !important;
        color: #ffffff !important;
        caret-color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        background-image: none !important;
        color-scheme: dark !important;
    }

    /* Universal input styling */
    input, textarea, [data-testid="stTextInput"] input {
        background-color: #1e1e24 !important;
        color: #ffffff !important;
        caret-color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        appearance: none !important;
        -webkit-appearance: none !important;
    }
    
    [data-testid="stChatInputTextArea"] {
        border: none !important;
    }

    /* Focus states */
    input:focus, textarea:focus, [data-testid="stTextInput"] input:focus {
        background-color: #25252d !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        outline: none !important;
    }
    
    [data-testid="stChatInputTextArea"]:focus {
        background-color: #1e1e24 !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Placeholder styling */
    ::placeholder, [data-testid="stChatInputTextArea"]::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.5) !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ==================== TOOL FUNCTIONS ====================

def scrape_recipe_from_url(url: str) -> dict:
    """Scrape recipe details from any recipe website."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        result = {
            "name": "",
            "servings": 4,
            "total_time": 60,
            "ingredients": [],
            "steps": [],
            "source_url": url
        }
        
        # Try JSON-LD structured data first
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Recipe':
                            data = item
                            break
                    else:
                        continue
                
                if '@graph' in data:
                    for item in data['@graph']:
                        if isinstance(item, dict) and item.get('@type') == 'Recipe':
                            data = item
                            break
                    else:
                        continue
                
                if data.get('@type') == 'Recipe':
                    result['name'] = data.get('name', '')
                    
                    yield_val = data.get('recipeYield')
                    if yield_val:
                        if isinstance(yield_val, list):
                            yield_val = yield_val[0]
                        match = re.search(r'(\d+)', str(yield_val))
                        if match:
                            result['servings'] = int(match.group(1))
                    
                    total_time = data.get('totalTime') or data.get('cookTime')
                    if total_time:
                        hours = re.search(r'(\d+)H', str(total_time))
                        minutes = re.search(r'(\d+)M', str(total_time))
                        total_mins = 0
                        if hours:
                            total_mins += int(hours.group(1)) * 60
                        if minutes:
                            total_mins += int(minutes.group(1))
                        if total_mins > 0:
                            result['total_time'] = total_mins
                    
                    ingredients = data.get('recipeIngredient', [])
                    if isinstance(ingredients, list):
                        result['ingredients'] = [str(ing).strip() for ing in ingredients if ing]
                    
                    instructions = data.get('recipeInstructions', [])
                    if isinstance(instructions, list):
                        for step in instructions:
                            if isinstance(step, str):
                                result['steps'].append(step.strip())
                            elif isinstance(step, dict):
                                text = step.get('text') or step.get('name', '')
                                if text:
                                    result['steps'].append(str(text).strip())
                    
                    if result['name']:
                        return result
            except:
                continue
        
        # Fallback to HTML parsing
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            result['name'] = title_tag.get_text(strip=True)
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


async def upload_to_cookidoo(name: str, ingredients: list, steps: list, servings: int = 4, prep_time: int = 30, total_time: int = 60, hints: list = None) -> dict:
    """Upload a custom recipe to Cookidoo."""
    try:
        email = st.secrets["cookidoo_email"]
        password = st.secrets["cookidoo_password"]
        
        service = CookidooService(email, password)
        api = await service.login()
        
        recipe_id = await service.create_custom_recipe(
            name=name,
            ingredients=ingredients,
            steps=steps,
            servings=servings,
            prep_time=prep_time,
            total_time=total_time,
            hints=hints
        )
        
        localization = api.localization
        base_url = localization.url
        if not base_url.startswith('http'):
            base_url = f"https://{base_url}"
        if '/foundation/' in base_url:
            base_url = base_url.split('/foundation/')[0]
        recipe_url = f"{base_url}/created-recipes/{recipe_id}"
        
        await service.close()
        
        return {
            "success": True,
            "recipe_id": recipe_id,
            "url": recipe_url
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== GEMINI SETUP ====================

# Load system prompt
try:
    with open("system_prompt.md", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    st.error("System prompt file not found!")
    SYSTEM_PROMPT = "You are a helpful assistant."

# ==================== GEMINI SETUP ====================


def get_gemini_tools():
    """Create Gemini function declarations."""
    scrape_recipe = FunctionDeclaration(
        name="scrape_recipe",
        description="Récupère les détails d'une recette depuis n'importe quel site web (Marmiton, Cuisineaz, etc.)",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "L'URL de la recette à récupérer"
                }
            },
            "required": ["url"]
        }
    )
    
    upload_recipe = FunctionDeclaration(
        name="upload_recipe",
        description="Publie une recette personnalisée sur Cookidoo. N'utiliser qu'après confirmation de l'utilisateur.",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom de la recette"
                },
                "ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des ingrédients avec quantités"
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Étapes de préparation adaptées au Thermomix"
                },
                "servings": {
                    "type": "integer",
                    "description": "Nombre de portions (défaut: 4)"
                },
                "prep_time": {
                    "type": "integer",
                    "description": "Temps de préparation en minutes (défaut: 30)"
                },
                "total_time": {
                    "type": "integer",
                    "description": "Temps total en minutes (défaut: 60)"
                }
            },
            "required": ["name", "ingredients", "steps"]
        }
    )
    
    return Tool(function_declarations=[scrape_recipe, upload_recipe])


def execute_function_call(function_name: str, function_args: dict) -> str:
    """Execute a function call from Gemini."""
    if function_name == "scrape_recipe":
        result = scrape_recipe_from_url(function_args.get("url", ""))
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif function_name == "upload_recipe":
        result = asyncio.run(upload_to_cookidoo(
            name=function_args.get("name", "Recipe"),
            ingredients=function_args.get("ingredients", []),
            steps=function_args.get("steps", []),
            servings=function_args.get("servings", 4),
            prep_time=function_args.get("prep_time", 30),
            total_time=function_args.get("total_time", 60),
            hints=function_args.get("hints")
        ))
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    return json.dumps({"error": f"Unknown function: {function_name}"})


def check_password() -> bool:
    """Check if the user has entered the correct password."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Initialize cookie manager with a key to prevent key collisions and ensure stability
    cookie_manager = stx.CookieManager(key="auth_manager")
    
    # Check if already authenticated via session state
    if st.session_state.authenticated:
        return True
        
    # Check for auth cookie
    app_password = st.secrets.get("app_password", "")
    password_hash = hashlib.sha256(app_password.encode()).hexdigest()
    
    # Wait for cookies to be available
    cookies = cookie_manager.get_all()
    
    # If cookies are None, we might need to wait for the component to mount
    if cookies is None:
         # Initial component load
         st.spinner("Checking authentication...")
         # We return False here to stop execution but the component will trigger a rerun
         pass 
    else:
        auth_cookie = cookies.get("auth_token")
        if auth_cookie and auth_cookie == password_hash:
            st.session_state.authenticated = True
            return True
    
    st.markdown("# 🍳 Cookidoo")
    st.markdown('<p class="subtitle">Créateur de recettes Thermomix assisté par IA</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="login-card">
        <h3>🔐 Bon retour</h3>
        <p>Entrez votre mot de passe pour continuer</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="Entrez le mot de passe...",
            label_visibility="collapsed"
        )
        
        if st.button("Continuer →", use_container_width=True):
            if password == app_password:
                st.session_state.authenticated = True
                
                # Always set cookie with hashed password, expires in 30 days
                expires = datetime.datetime.now() + datetime.timedelta(days=30)
                cookie_manager.set("auth_token", password_hash, expires_at=expires)
                
                # Small delay to ensure cookie is set before rerun
                time.sleep(0.5)
                st.rerun()
            elif password == "":
                 st.warning("Veuillez entrer un mot de passe")
            else:
                st.error("Mot de passe incorrect")
    
    return False


def process_with_gemini(user_message: str, chat_history: list) -> tuple[str, list]:
    """Process a message with Gemini and handle function calls."""
    
    genai.configure(api_key=st.secrets["gemini_api_key"])
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[get_gemini_tools()],
        system_instruction=SYSTEM_PROMPT
    )
    
    # Build conversation history for Gemini
    gemini_history = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    chat = model.start_chat(history=gemini_history)
    
    response = chat.send_message(user_message)
    
    # Process function calls
    function_outputs = []
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Check for function calls
        if not response.candidates:
            break
            
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            break
        
        function_call = None
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call.name:
                function_call = part.function_call
                break
        
        if not function_call:
            break
        
        # Execute function
        function_name = function_call.name
        function_args = dict(function_call.args) if function_call.args else {}
        
        function_outputs.append(f"🔧 {function_name}")
        result = execute_function_call(function_name, function_args)
        function_outputs.append(f"✓ Done")
        
        # Send function result back
        response = chat.send_message(
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=function_name,
                        response={"result": result}
                    )
                )]
            )
        )
    
    # Get final text
    final_text = ""
    try:
        final_text = response.text
    except:
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    final_text += part.text
    
    if not final_text:
        final_text = "Done."
    
    return final_text, function_outputs


def main_app():
    """Main chat application."""
    
    # Header
    st.markdown("# 🍳 Cookidoo")
    st.markdown('<p class="subtitle">Créateur de recettes Thermomix assisté par IA</p>', unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_image" not in st.session_state:
        st.session_state.pending_image = None
    
    # Show welcome card if no messages
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-card">
            <h3>Comment ça marche</h3>
            <div class="steps-grid">
                <div class="step-item">
                    <div class="step-number">1</div>
                    <div class="step-text">Collez une URL de recette de n'importe quel site</div>
                </div>
                <div class="step-item">
                    <div class="step-number">2</div>
                    <div class="step-text">Ou importez une photo de recette</div>
                </div>
                <div class="step-item">
                    <div class="step-number">3</div>
                    <div class="step-text">L'IA l'adapte pour le Thermomix</div>
                </div>
                <div class="step-item">
                    <div class="step-number">4</div>
                    <div class="step-text">Validez pour publier sur Cookidoo</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Image upload section - only show when no messages yet
    if not st.session_state.messages:
        uploaded_file = st.file_uploader(
            "📷 Importer une photo de recette",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            key="image_upload"
        )
        
        # Process uploaded image
        if uploaded_file is not None and st.session_state.pending_image != uploaded_file.name:
            st.session_state.pending_image = uploaded_file.name
            
            with st.spinner("📷 Lecture et adaptation de la recette..."):
                try:
                    import PIL.Image
                    import io
                    
                    image_bytes = uploaded_file.getvalue()
                    image = PIL.Image.open(io.BytesIO(image_bytes))
                    
                    genai.configure(api_key=st.secrets["gemini_api_key"])
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    response = model.generate_content([
                        "Extrais la recette de cette image. Donne-moi le nom, les ingrédients et les étapes. Réponds en français de manière structurée.",
                        image
                    ])
                    
                    extracted_text = response.text
                    user_msg = f"📷 Recette extraite d'une image:\n\n{extracted_text}\n\nAdapte cette recette pour le Thermomix."
                    
                    # Process the extracted recipe with Gemini to adapt for Thermomix
                    # Don't add user message to history - just show the AI response
                    response_text, function_logs = process_with_gemini(user_msg, [])
                    
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Chat input
    if prompt := st.chat_input("Collez une URL ou décrivez votre envie..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(""):
                try:
                    history = st.session_state.messages[:-1]
                    response_text, function_logs = process_with_gemini(prompt, history)
                    
                    for log in function_logs:
                        st.caption(log)
                    
                    st.markdown(response_text)
                    
                    # Check for equipment warning
                    if "[[ATTENTION : ÉQUIPEMENT SUPPLÉMENTAIRE REQUIS]]" in response_text:
                        st.warning("⚠️ Attention : Cette recette nécessite un équipement supplémentaire (four, poêle, etc.) que le Thermomix ne peut pas remplacer.")
                        
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    import traceback
                    st.code(traceback.format_exc())
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


# Main entry point
if __name__ == "__main__":
    if check_password():
        main_app()
