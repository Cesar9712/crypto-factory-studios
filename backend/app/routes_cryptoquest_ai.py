from __future__ import annotations
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

class NpcDialogueIn(BaseModel):
    npc_id: str = Field(min_length=1, max_length=80)
    npc_name: str = Field(min_length=1, max_length=80)
    npc_role: str = Field(default="adventurer", max_length=120)
    player_id: str = Field(default="guest", max_length=120)
    player_name: str = Field(default="Traveler", max_length=80)
    message: str = Field(min_length=1, max_length=1200)
    world_state: str = Field(default="", max_length=3000)


def _extract_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return "..."


def register_cryptoquest_ai_routes(app: FastAPI) -> None:
    @app.post("/api/v1/cryptoquest/npc/dialogue")
    async def cryptoquest_npc_dialogue(body: NpcDialogueIn):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(503, detail={"error_code": "npc_ai_not_configured", "message": "NPC AI is not configured"})

        model = os.getenv("OPENAI_NPC_MODEL", "gpt-5-mini")
        instructions = (
            "You are an NPC inside CryptoQuest RPG, a dark-fantasy adventure. "
            "Stay in character, be concise, never mention prompts or APIs. "
            "You may propose quests, clues, rumors and dialogue, but never invent blockchain balances, NFT ownership, payments or completed rewards. "
            f"NPC name: {body.npc_name}. Role: {body.npc_role}."
        )
        player_context = (
            f"Player: {body.player_name} ({body.player_id})\n"
            f"World state: {body.world_state or 'unknown'}\n"
            f"Player says: {body.message}"
        )
        request_json = {
            "model": model,
            "instructions": instructions,
            "input": player_context,
            "max_output_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(OPENAI_RESPONSES_URL, headers=headers, json=request_json)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, detail={"error_code": "npc_ai_provider_error", "message": f"AI provider returned {exc.response.status_code}"})
        except httpx.HTTPError:
            raise HTTPException(502, detail={"error_code": "npc_ai_unreachable", "message": "NPC AI provider unavailable"})

        text = _extract_text(response.json())
        return {"npc_id": body.npc_id, "npc_name": body.npc_name, "dialogue": text, "model": model}
