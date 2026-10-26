"""
Cookidoo Recipe Creator - Streamlit UI with Gemini AI

A chat interface for creating Thermomix recipes using Gemini AI, published to Cookidoo.
"""

import asyncio
import datetime
import hashlib
import hmac
import json
import re
import time
from enum import Enum

import extra_streamlit_components as stx
import httpx
import streamlit as st
from bs4 import BeautifulSoup
from cookidoo_api import ThermomixSpeed, ThermomixTemperature
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from cookidoo_service import CookidooService, settings_label

MODEL = "gemini-2.5-flash"
IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]

st.set_page_config(page_title="Cookidoo", page_icon="🍳", layout="centered")

# Theme lives in .streamlit/config.toml; only hide Streamlit chrome here.
st.markdown("""
<style>
    #MainMenu, footer, [data-testid="stHeader"] {display: none;}
    [data-testid="stMainBlockContainer"] {padding-top: 1.5rem; padding-bottom: 6rem;}
</style>
""", unsafe_allow_html=True)


# ==================== RESPONSE SCHEMA ====================

# Only values the Thermomix accepts, taken from cookidoo-api.
Temperature = Enum("Temperature", {"NONE": "none"} | {t.name: t.value for t in ThermomixTemperature}, type=str)
Speed = Enum("Speed", {"NONE": "none"} | {s.name: s.value for s in ThermomixSpeed}, type=str)


class Step(BaseModel):
    text: str = Field(description="Instruction sans les réglages Thermomix")
    time_s: int = Field(description="Durée en secondes, 0 si aucun réglage")
    temperature: Temperature
    speed: Speed
    reverse: bool = Field(description="Sens inverse")


class Recipe(BaseModel):
    name: str
    servings: int
    prep_min: int
    total_min: int
    ingredients: list[str]
    steps: list[Step]
    hints: list[str]
    warnings: list[str]


class Reply(BaseModel):
    message: str
    recipe: Recipe | None


with open("system_prompt.md", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


# ==================== TOOLS ====================

@st.cache_data(ttl=3600)
def scrape_recipe_from_url(url: str) -> dict:
    """Scrape recipe details: JSON-LD first, raw page text as fallback."""
    try:
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            response.raise_for_status()
    except Exception as e:
        return {"error": str(e)}

    soup = BeautifulSoup(response.text, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if not isinstance(item, dict):
                continue
            kind = item.get("@type")
            if kind == "Recipe" or (isinstance(kind, list) and "Recipe" in kind):
                steps = []
                for step in item.get("recipeInstructions") or []:
                    if isinstance(step, str):
                        steps.append(step.strip())
                    elif isinstance(step, dict):
                        # HowToSection groups steps in itemListElement
                        for s in step.get("itemListElement", [step]):
                            if isinstance(s, dict) and (s.get("text") or s.get("name")):
                                steps.append(str(s.get("text") or s.get("name")).strip())
                if item.get("name") and (item.get("recipeIngredient") or steps):
                    return {
                        "name": item.get("name"),
                        "yield": item.get("recipeYield"),
                        "prepTime": item.get("prepTime"),
                        "totalTime": item.get("totalTime"),
                        "ingredients": item.get("recipeIngredient") or [],
                        "steps": steps,
                    }

    # No structured data: let Gemini read the page text.
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    return {"raw_text": soup.get_text(separator="\n", strip=True)[:6000]}


async def upload_to_cookidoo(recipe: dict) -> str:
    """Upload a recipe to Cookidoo and return its URL."""
    service = CookidooService(st.secrets["cookidoo_email"], st.secrets["cookidoo_password"])
    try:
        await service.login()
        return await service.create_custom_recipe(recipe)
    finally:
        await service.close()


# ==================== GEMINI ====================

@st.cache_resource
def gemini_client() -> genai.Client:
    return genai.Client(api_key=st.secrets["gemini_api_key"])


def ask_gemini(history: list, text: str, image=None, scraped: dict | None = None, recipe: dict | None = None) -> Reply:
    """One Gemini call returning a structured Reply.

    Past turns are sent as short text only; the current recipe is sent once, compactly.
    """
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
        for m in history
    ]
    prompt = text or "Extrais la recette de cette image et adapte-la pour le Thermomix TM6."
    if recipe:
        prompt += f"\n\n[Recette en cours]\n{json.dumps(recipe, ensure_ascii=False, separators=(',', ':'))}"
    if scraped:
        prompt += f"\n\n[Données extraites de l'URL]\n{json.dumps(scraped, ensure_ascii=False, separators=(',', ':'))}"
    parts = [types.Part.from_text(text=prompt)]
    if image is not None:
        parts.append(types.Part.from_bytes(data=image.getvalue(), mime_type=image.type))
    contents.append(types.Content(role="user", parts=parts))

    response = gemini_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Reply,
            # ponytail: no thinking = fastest/cheapest; raise (e.g. 1024) if adaptations get sloppy
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.parsed or Reply.model_validate_json(response.text)


# ==================== UI ====================

def check_password() -> bool:
    """Password gate, remembered for 30 days in a cookie."""
    if st.session_state.get("authenticated"):
        return True

    app_password = st.secrets.get("app_password", "")
    password_hash = hashlib.sha256(app_password.encode()).hexdigest()
    cookie_manager = stx.CookieManager(key="auth_manager")
    cookies = cookie_manager.get_all()  # None on first render, the component reruns once mounted
    if cookies and hmac.compare_digest(cookies.get("auth_token", ""), password_hash):
        st.session_state.authenticated = True
        return True

    header()
    with st.container(border=True):
        st.markdown("#### 🔐 Bon retour")
        with st.form("login", border=False):
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez le mot de passe…")
            if st.form_submit_button("Continuer", type="primary", width="stretch"):
                if hmac.compare_digest(password, app_password):
                    st.session_state.authenticated = True
                    cookie_manager.set("auth_token", password_hash,
                                       expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    time.sleep(0.5)  # let the cookie component write before rerun
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect")
    return False


def header():
    st.markdown("## 🍳 Cookidoo")
    st.caption("Vos recettes adaptées au Thermomix TM6, publiées sur Cookidoo.")


def render_recipe(recipe: dict):
    with st.container(border=True):
        st.markdown(f"### {recipe['name']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Portions", recipe["servings"])
        c2.metric("Préparation", f"{recipe['prep_min']} min")
        c3.metric("Total", f"{recipe['total_min']} min")
        for warning in recipe["warnings"]:
            st.warning(warning, icon="⚠️")

        labels = [f"Ingrédients ({len(recipe['ingredients'])})", f"Étapes ({len(recipe['steps'])})"]
        tabs = st.tabs(labels + (["Astuces"] if recipe["hints"] else []))
        with tabs[0]:
            st.markdown("\n".join(f"- {i}" for i in recipe["ingredients"]))
        with tabs[1]:
            for n, step in enumerate(recipe["steps"], 1):
                label = settings_label(step)
                st.markdown(f"**{n}.** {step['text']}" + (f"  \n:green-badge[⚙️ {label}]" if label else ""))
        if recipe["hints"]:
            with tabs[2]:
                st.markdown("\n".join(f"- {h}" for h in recipe["hints"]))

        if url := st.session_state.published_url:
            st.success("Recette publiée sur Cookidoo !", icon="✅")
            st.link_button("Ouvrir dans Cookidoo", url, icon=":material/open_in_new:", width="stretch")
        elif st.button("Publier sur Cookidoo", type="primary", icon=":material/upload:", width="stretch"):
            with st.spinner("Publication en cours…"):
                try:
                    st.session_state.published_url = asyncio.run(upload_to_cookidoo(recipe))
                    st.rerun()
                except Exception as e:
                    st.error(f"Échec de la publication : {e}")


def main_app():
    header()
    state = st.session_state
    state.setdefault("messages", [])
    state.setdefault("recipe", None)
    state.setdefault("published_url", None)

    if not state.messages:
        with st.container(border=True):
            st.markdown(
                "**Comment ça marche**\n"
                "1. Collez l'URL d'une recette, décrivez une envie ou joignez une photo 📷\n"
                "2. L'IA l'adapte pour le TM6 (temps, température, vitesse)\n"
                "3. Ajustez-la en discutant (« pour 6 personnes », « sans lactose »…)\n"
                "4. Publiez-la sur Cookidoo en un clic"
            )

    for message in state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if state.recipe:
        render_recipe(state.recipe)

    prompt = st.chat_input(
        "Collez une URL, décrivez une envie…", accept_file=True, file_type=IMAGE_TYPES
    )
    if not prompt:
        return

    text = (prompt.text or "").strip()
    image = prompt.files[0] if prompt.files else None
    user_content = text or "📷 Photo de recette"
    with st.chat_message("user"):
        st.markdown(user_content)
        if image:
            st.image(image, width=200)

    with st.chat_message("assistant"):
        try:
            with st.status("Je m'en occupe…") as status:
                scraped = None
                if url := re.search(r"https?://[^\s<>\"]+", text):
                    status.update(label="Récupération de la recette…")
                    scraped = scrape_recipe_from_url(url.group(0))
                status.update(label="Adaptation pour le Thermomix…")
                reply = ask_gemini(state.messages, text, image, scraped, state.recipe)
        except Exception as e:
            st.error(f"Erreur : {e}")
            return

    state.messages += [{"role": "user", "content": user_content}, {"role": "assistant", "content": reply.message}]
    if reply.recipe:
        state.recipe = reply.recipe.model_dump(mode="json")
        state.published_url = None
    st.rerun()


if __name__ == "__main__":
    if check_password():
        main_app()
