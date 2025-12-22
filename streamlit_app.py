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

# Page configuration
st.set_page_config(
    page_title="Cookidoo Recipe Creator",
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
        margin-bottom: 1rem !important;
    }
    
    .welcome-card p {
        color: rgba(255,255,255,0.6);
        font-size: 0.9rem;
        line-height: 1.6;
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
    
    /* Chat input */
    .stChatInput {
        border-radius: 16px !important;
    }
    
    .stChatInput > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
    }
    
    .stChatInput input {
        color: #ffffff !important;
    }
    
    .stChatInput input::placeholder {
        color: rgba(255,255,255,0.4) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: rgba(255, 255, 255, 0.05) !important;
        color: rgba(255,255,255,0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px dashed rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: rgba(255,255,255,0.6) !important;
    }
    
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
    }
    
    /* Success/Info/Error */
    .stSuccess, .stInfo {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.8) !important;
    }
    
    .stError {
        background: rgba(255, 100, 100, 0.1) !important;
        border: 1px solid rgba(255, 100, 100, 0.2) !important;
        border-radius: 12px !important;
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

SYSTEM_PROMPT = """Tu es un expert culinaire spécialisé dans la création de recettes pour le Thermomix. Tu as une parfaite compréhension de ses modes, accessoires et comment écrire des instructions claires et précises.

## Directives pour écrire des recettes Thermomix

Chaque étape doit utiliser le vocabulaire spécifique du Thermomix :
- **Vitesse** : vitesse 1, vitesse 5, vitesse 🥄 (mijotage), sens inverse 🔄
- **Température** : 50°C, 100°C, 120°C, Varoma
- **Temps** : 5 min, 30 sec
- **Fonctions** : Mode pétrissage 🌾, Turbo, Mixer
- **Accessoires** : fouet papillon, panier de cuisson, spatule

Exemples de bonnes instructions :
- "Mettre l'oignon coupé en deux dans le bol, puis mixer 5 sec / vitesse 5. Racler les parois du bol avec la spatule."
- "Ajouter l'huile d'olive et faire revenir 3 min / 120°C / sens inverse 🔄 / vitesse 1."

## Processus de travail

1. Quand l'utilisateur te donne un lien de recette, utilise l'outil `scrape_recipe` pour récupérer les détails
2. Analyse la recette et ADAPTE-LA pour le Thermomix avec les instructions appropriées
3. Montre la recette adaptée à l'utilisateur et demande confirmation
4. Une fois approuvé, utilise `upload_recipe` pour publier sur Cookidoo

IMPORTANT : Tu dois TOUJOURS adapter les étapes pour le Thermomix, pas juste copier les étapes originales !"""


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
    
    if st.session_state.authenticated:
        return True
    
    st.markdown("# 🍳 Cookidoo")
    st.markdown('<p class="subtitle">AI-powered Thermomix recipe creator</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="welcome-card">
        <h3>🔐 Enter to continue</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password...",
            label_visibility="collapsed"
        )
        
        if st.button("Continue →", use_container_width=True):
            if password == st.secrets.get("app_password", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
    
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
    st.markdown('<p class="subtitle">AI-powered Thermomix recipe creator</p>', unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_image" not in st.session_state:
        st.session_state.pending_image = None
    
    # Show welcome card if no messages
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-card">
            <h3>How it works</h3>
            <p>
                <span class="step">1. Paste a recipe URL</span>
                <span class="step">2. Or upload an image</span>
                <span class="step">3. AI adapts for Thermomix</span>
                <span class="step">4. Say OK to upload</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Image upload section (always visible above chat input)
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "📷 Upload recipe image",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            key="image_upload"
        )
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_image = None
            st.rerun()
    
    # Process uploaded image
    if uploaded_file is not None and st.session_state.pending_image != uploaded_file.name:
        st.session_state.pending_image = uploaded_file.name
        
        with st.spinner("📷 Reading recipe from image..."):
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
                st.session_state.messages.append({"role": "user", "content": user_msg})
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Chat input
    if prompt := st.chat_input("Paste a recipe URL or describe what you want..."):
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
