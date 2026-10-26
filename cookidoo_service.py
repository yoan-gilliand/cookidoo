"""
Cookidoo Service

Module to encapsulate all cookidoo-api logic for interacting with the Cookidoo platform.
"""

import logging

from aiohttp import ClientSession
from cookidoo_api import (
    Cookidoo,
    CookidooConfig,
    CookidooCreateCustomRecipe,
    CookidooException,
    CookidooInstruction,
    CookidooTTSAnnotation,
    CookidooTemperatureSetting,
    ThermomixDirection,
    ThermomixMachineType,
)
from cookidoo_api.helpers import get_localization_options

_LOGGER = logging.getLogger(__name__)


def settings_label(step: dict) -> str:
    """Human-readable Thermomix settings of a step, e.g. "5 min/100°C/sens inverse/vitesse 1"."""
    parts = []
    t = step.get("time_s") or 0
    if t:
        m, s = divmod(t, 60)
        parts.append(" ".join(filter(None, [f"{m} min" if m else "", f"{s} sec" if s else ""])))
    temp = step.get("temperature", "none")
    if temp != "none":
        parts.append("Varoma" if temp == "varoma" else f"{temp}°C")
    if step.get("reverse"):
        parts.append("sens inverse")
    speed = step.get("speed", "none")
    if speed != "none":
        parts.append("vitesse mijotage" if speed == "soft" else f"vitesse {speed}")
    return "/".join(parts)


def _instruction(step: dict) -> CookidooInstruction | str:
    """Step text with its settings appended as a guided-cooking (TTS) annotation."""
    label = settings_label(step)
    if not label:
        return step["text"]
    temp = step.get("temperature", "none")
    speed = step.get("speed", "none")
    return CookidooInstruction(
        text=f"{step['text']} {label}",
        annotations=[
            CookidooTTSAnnotation(
                slot=label,
                time=step.get("time_s") or None,
                temperature=CookidooTemperatureSetting(temp) if temp != "none" else None,
                speed=speed if speed != "none" else None,
                direction=ThermomixDirection.CCW if step.get("reverse") else None,
            )
        ],
    )


class CookidooService:
    """Service class for managing Cookidoo API interactions."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self._api_client: Cookidoo | None = None
        self._session: ClientSession | None = None

    async def login(self) -> Cookidoo:
        """Authenticate with Cookidoo and return the API client."""
        try:
            self._session = ClientSession()
            config = CookidooConfig(
                email=self.email,
                password=self.password,
                localization=(await get_localization_options(country="fr", language="fr-FR"))[0],
            )
            self._api_client = Cookidoo(session=self._session, cfg=config)
            await self._api_client.login()
            return self._api_client
        except Exception as e:
            await self.close()
            raise Exception(f"Failed to authenticate with Cookidoo: {str(e)}") from e

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()

    async def create_custom_recipe(self, recipe: dict) -> str:
        """
        Create a custom recipe on Cookidoo and return its URL.

        `recipe` is the dict produced by the app (name, servings, prep_min, total_min,
        ingredients, steps[{text, time_s, temperature, speed, reverse}], hints).
        Steps carry guided-cooking settings; if Cookidoo rejects them, falls back to plain text.
        """
        if not self._api_client:
            raise Exception("Not authenticated. Please call login() first.")

        def build(guided: bool) -> CookidooCreateCustomRecipe:
            return CookidooCreateCustomRecipe(
                name=recipe["name"],
                ingredients=recipe["ingredients"],
                instructions=[
                    _instruction(s) if guided else f"{s['text']} {settings_label(s)}".strip()
                    for s in recipe["steps"]
                ],
                serving_size=max(1, recipe["servings"]),
                active_time=min(recipe["prep_min"], recipe["total_min"]) * 60,  # seconds
                total_time=recipe["total_min"] * 60,
                tools=[ThermomixMachineType.TM6],
                hints=recipe.get("hints") or [],
            )

        try:
            try:
                created = await self._api_client.create_custom_recipe(build(guided=True))
            except CookidooException as e:
                _LOGGER.warning("Guided recipe rejected, retrying as plain text: %s", e)
                await self._remove_orphan(e)
                created = await self._api_client.create_custom_recipe(build(guided=False))
        except Exception as e:
            raise Exception(f"Failed to create custom recipe: {str(e)}") from e
        return created.url

    async def _remove_orphan(self, e: Exception) -> None:
        """Delete the empty stub left behind when the populate step failed."""
        for note in getattr(e, "__notes__", []):
            if note.startswith("Orphaned custom recipe stub id: "):
                try:
                    await self._api_client.remove_custom_recipe(note.rsplit(" ", 1)[-1])
                except CookidooException:
                    pass
