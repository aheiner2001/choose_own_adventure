from __future__ import annotations

import hashlib
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from google import genai
from supabase import Client, create_client

ROOT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

MAP_BUCKET = "dnd-maps"


@dataclass
class AppConfig:
    supabase_url: str
    supabase_key: str
    gemini_api_key: str | None


CHARACTER_ARCHETYPES: dict[str, dict[str, Any]] = {
    "Fighter": {"hp": 28, "strength": 5, "agility": 2, "arcana": 0},
    "Rogue": {"hp": 22, "strength": 2, "agility": 5, "arcana": 1},
    "Wizard": {"hp": 18, "strength": 0, "agility": 2, "arcana": 6},
    "Cleric": {"hp": 24, "strength": 3, "agility": 2, "arcana": 4},
    "Ranger": {"hp": 23, "strength": 3, "agility": 4, "arcana": 1},
}

TURN_ACTIONS = ["attack", "defend", "investigate", "cast", "negotiate", "rest"]


def get_config() -> AppConfig:
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip() or None
    return AppConfig(
        supabase_url=os.getenv("SUPABASE_URL", "").strip(),
        supabase_key=os.getenv("SUPABASE_KEY", "").strip(),
        gemini_api_key=gemini_key,
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_rows(result: Any) -> list[dict[str, Any]]:
    data = getattr(result, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def require_supabase(config: AppConfig) -> Client:
    if not config.supabase_url or not config.supabase_key:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY in .env")
        st.stop()
    return create_client(config.supabase_url, config.supabase_key)


def campaign_code(name: str) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return digest.upper()


def get_or_create_campaign(client: Client, name: str) -> dict[str, Any]:
    code = campaign_code(name)
    try:
        existing = as_rows(client.table("campaigns").select("*").eq("join_code", code).limit(1).execute())
        if existing:
            return existing[0]
    except Exception:
        # Backward compatibility: older schemas may not have join_code.
        try:
            existing_legacy = as_rows(client.table("campaigns").select("*").eq("code", code).limit(1).execute())
            if existing_legacy:
                return existing_legacy[0]
        except Exception:
            pass

    payload: dict[str, Any] = {"name": name, "join_code": code, "created_at": now_iso()}

    # Backward compatibility for legacy schemas with extra NOT NULL columns.
    for _ in range(12):
        try:
            inserted = as_rows(client.table("campaigns").insert(payload).execute())
            if inserted:
                return inserted[0]
            raise RuntimeError("Campaign insert returned no row.")
        except Exception as exc:
            message = str(exc)
            missing_col = _extract_missing_not_null_column(message)
            if not missing_col:
                raise
            payload[missing_col] = _legacy_campaign_default(missing_col, name, code)

    raise RuntimeError("Unable to create campaign after legacy-schema compatibility retries.")


def _extract_missing_not_null_column(error_message: str) -> str | None:
    match = re.search(r'null value in column "([^"]+)"', error_message)
    if not match:
        return None
    return match.group(1)


def _legacy_campaign_default(column_name: str, campaign_name: str, code: str) -> Any:
    col = column_name.lower()
    explicit_defaults: dict[str, Any] = {
        "code": code,
        "join_code": code,
        "name": campaign_name,
        "creator_prompt": f"Campaign seed for {campaign_name}",
        "status": "lobby",
        "current_turn": 0,
        "turn_index": 0,
    }
    if col in explicit_defaults:
        return explicit_defaults[col]
    if col.endswith("_at"):
        return now_iso()
    if "count" in col or "turn" in col or "round" in col or "index" in col:
        return 0
    if "active" in col or col.startswith("is_") or col.startswith("has_"):
        return False
    return f"auto_{col}"


def create_character(
    client: Client,
    campaign_id: str,
    player_name: str,
    character_name: str,
    archetype: str,
    notes: str,
) -> dict[str, Any]:
    stats = CHARACTER_ARCHETYPES[archetype]
    payload = {
        "campaign_id": campaign_id,
        "player_name": player_name,
        "name": character_name,
        "archetype": archetype,
        "max_hp": stats["hp"],
        "hp": stats["hp"],
        "strength": stats["strength"],
        "agility": stats["agility"],
        "arcana": stats["arcana"],
        "notes": notes,
        "created_at": now_iso(),
    }
    inserted = as_rows(client.table("characters").insert(payload).execute())
    return inserted[0]


def list_characters(client: Client, campaign_id: str) -> list[dict[str, Any]]:
    return as_rows(
        client.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=False)
        .execute()
    )


def update_character_hp(client: Client, character_id: str, next_hp: int) -> None:
    client.table("characters").update({"hp": next_hp}).eq("id", character_id).execute()


def upload_map_image(
    client: Client,
    campaign_id: str,
    uploaded_name: str,
    mime_type: str,
    bytes_data: bytes,
    uploaded_by: str,
) -> None:
    suffix = uploaded_name.split(".")[-1].lower() if "." in uploaded_name else "bin"
    object_path = f"{campaign_id}/{uuid4().hex}.{suffix}"
    client.storage.from_(MAP_BUCKET).upload(
        object_path,
        bytes_data,
        {"content-type": mime_type, "upsert": "false"},
    )
    public_url = client.storage.from_(MAP_BUCKET).get_public_url(object_path)
    client.table("map_assets").insert(
        {
            "campaign_id": campaign_id,
            "uploaded_by": uploaded_by,
            "filename": uploaded_name,
            "mime_type": mime_type,
            "storage_path": object_path,
            "public_url": public_url,
            "created_at": now_iso(),
        }
    ).execute()


def list_maps(client: Client, campaign_id: str) -> list[dict[str, Any]]:
    return as_rows(
        client.table("map_assets")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .execute()
    )


def add_story_idea(client: Client, campaign_id: str, submitted_by: str, title: str, idea_text: str) -> None:
    client.table("story_ideas").insert(
        {
            "campaign_id": campaign_id,
            "submitted_by": submitted_by,
            "title": title,
            "idea_text": idea_text,
            "created_at": now_iso(),
        }
    ).execute()


def list_story_ideas(client: Client, campaign_id: str) -> list[dict[str, Any]]:
    return as_rows(
        client.table("story_ideas")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )


def save_session_brief(client: Client, campaign_id: str, prepared_by: str, brief_text: str) -> None:
    client.table("session_briefs").insert(
        {
            "campaign_id": campaign_id,
            "prepared_by": prepared_by,
            "brief_text": brief_text,
            "created_at": now_iso(),
        }
    ).execute()


def latest_session_brief(client: Client, campaign_id: str) -> str:
    rows = as_rows(
        client.table("session_briefs")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not rows:
        return ""
    return rows[0]["brief_text"]


def generate_ai_session_brief(
    campaign_name: str,
    recent_ideas: list[dict[str, Any]],
    gm_notes: str,
    gemini_api_key: str | None,
) -> str:
    if not gemini_api_key:
        return ""
    idea_lines: list[str] = []
    for idea in recent_ideas[:10]:
        idea_lines.append(f"- {idea['title']} (by {idea['submitted_by']}): {idea['idea_text']}")
    ideas_block = "\n".join(idea_lines) or "- No ideas submitted yet."
    prompt = (
        "You are helping a tabletop DM prepare one campaign session.\n"
        f"Campaign: {campaign_name}\n\n"
        "Player ideas:\n"
        f"{ideas_block}\n\n"
        "GM notes:\n"
        f"{gm_notes or 'No additional GM notes.'}\n\n"
        "Return a concise prep brief with these sections:\n"
        "1) Session Hook (3-5 sentences)\n"
        "2) Scenes (3 bullet points)\n"
        "3) NPCs (3 bullet points)\n"
        "4) Twists (2 bullet points)\n"
        "5) If players go off-rails (2 bullet points)\n"
        "Tone: fantasy adventure, practical for 60-90 minutes of play."
    )
    client = genai.Client(api_key=gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    text = getattr(response, "text", None)
    return text.strip() if text else ""


def ability_bonus(character: dict[str, Any], action: str) -> int:
    if action in {"attack", "defend"}:
        return int(character["strength"])
    if action in {"cast", "investigate"}:
        return int(character["arcana"])
    if action in {"negotiate", "rest"}:
        return int(character["agility"])
    return 0


def compute_turn_effect(character: dict[str, Any], action: str, raw_roll: int) -> tuple[int, int, str]:
    bonus = ability_bonus(character, action)
    total_roll = raw_roll + bonus
    hp_delta = 0
    if action == "attack":
        if total_roll >= 18:
            hp_delta = -8
            result = "critical hit"
        elif total_roll >= 13:
            hp_delta = -5
            result = "solid hit"
        elif total_roll >= 10:
            hp_delta = -2
            result = "glancing hit"
        else:
            hp_delta = 0
            result = "miss"
    elif action == "rest":
        if total_roll >= 12:
            hp_delta = +4
            result = "strong recovery"
        else:
            hp_delta = +2
            result = "minor recovery"
    elif action in {"cast", "investigate", "negotiate"}:
        if total_roll >= 15:
            hp_delta = -3
            result = "major progress"
        elif total_roll >= 10:
            hp_delta = -1
            result = "partial progress"
        else:
            hp_delta = 0
            result = "setback"
    else:
        result = "defensive stance"
    return total_roll, hp_delta, result


def build_narration(
    campaign_name: str,
    character_name: str,
    action: str,
    raw_roll: int,
    total_roll: int,
    hp_delta: int,
    result: str,
) -> str:
    if hp_delta < 0:
        impact = f"Threat reduced by {abs(hp_delta)}."
    elif hp_delta > 0:
        impact = f"{character_name} recovers {hp_delta} HP."
    else:
        impact = "No direct HP swing."
    return (
        f"[{campaign_name}] {character_name} chooses {action}. "
        f"d20={raw_roll}, total={total_roll} -> {result}. {impact}"
    )


def add_turn(
    client: Client,
    campaign_id: str,
    character_id: str,
    action: str,
    raw_roll: int,
    total_roll: int,
    hp_delta: int,
    narration: str,
) -> None:
    client.table("turns").insert(
        {
            "campaign_id": campaign_id,
            "character_id": character_id,
            "action": action,
            "dice_roll": raw_roll,
            "total_roll": total_roll,
            "effect_hp_delta": hp_delta,
            "narration": narration,
            "created_at": now_iso(),
        }
    ).execute()


def list_turns(client: Client, campaign_id: str) -> list[dict[str, Any]]:
    return as_rows(
        client.table("turns")
        .select("id, action, dice_roll, total_roll, effect_hp_delta, narration, created_at, characters(name)")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )


def idea_panel() -> None:
    st.subheader("4 Persona Design Debate")
    st.markdown(
        """
        - **Dungeon Master:** D&D needs turn cadence, stakes, and shared imagination.
        - **Systems Engineer:** Keep data model small, reliable, and easy to operate.
        - **Story Crafter:** Encourage player prompts between sessions for richer arcs.
        - **Product Pragmatist:** Manual story prep beats expensive live AI for MVP.
        """
    )
    st.info(
        "Chosen approach: simple access, storage bucket images, stronger dice mechanics, "
        "and human-curated story prep (optional AI offline)."
    )


def story_prep_panel(
    client: Client,
    campaign_id: str,
    campaign_name: str,
    player_name: str,
    gemini_api_key: str | None,
) -> None:
    st.subheader("Story Prep Workflow (Campaign Between Nights)")
    st.caption("Players submit ideas now; the DM compiles a brief before next session.")

    with st.container(border=True):
        idea_title = st.text_input("Idea title", placeholder="The old mine wakes again")
        idea_text = st.text_area("Idea details", placeholder="What twists, villains, or goals should happen next?")
        if st.button("Submit Story Idea"):
            if idea_title.strip() and idea_text.strip():
                add_story_idea(client, campaign_id, player_name, idea_title.strip(), idea_text.strip())
                st.success("Idea saved.")
            else:
                st.warning("Add both title and details.")

    ideas = list_story_ideas(client, campaign_id)
    if ideas:
        st.markdown("**Recent player ideas**")
        for item in ideas[:8]:
            st.write(f"- **{item['title']}** by {item['submitted_by']}: {item['idea_text']}")

    with st.container(border=True):
        gm_notes = st.text_area(
            "GM optional notes for AI (constraints, desired villains, pacing)",
            placeholder="Keep tone dark fantasy, include a moral dilemma, avoid heavy combat this week.",
            height=100,
        )
        if st.button("Draft Session Brief with Gemini"):
            if not gemini_api_key:
                st.warning("No GEMINI_API_KEY found in .env")
            else:
                try:
                    generated = generate_ai_session_brief(
                        campaign_name=campaign_name,
                        recent_ideas=ideas,
                        gm_notes=gm_notes.strip(),
                        gemini_api_key=gemini_api_key,
                    )
                    if generated:
                        st.session_state["generated_session_brief"] = generated
                        st.success("Draft created. Review/edit it before saving.")
                    else:
                        st.warning("Gemini returned an empty draft. Try adding more notes.")
                except Exception as exc:
                    st.error(f"Gemini draft failed: {exc}")

        draft_prompt = st.text_area(
            "DM prep text (paste your manual summary or AI-generated story setup)",
            value=st.session_state.get("generated_session_brief", latest_session_brief(client, campaign_id)),
            height=180,
        )
        if st.button("Save Session Brief"):
            if draft_prompt.strip():
                save_session_brief(client, campaign_id, player_name, draft_prompt.strip())
                st.success("Session brief saved for next campaign night.")
            else:
                st.warning("Session brief is empty.")


def main() -> None:
    st.set_page_config(page_title="D&D Story Table", page_icon="🐉", layout="wide")
    st.title("D&D Story Table - Streamlit + Supabase")
    st.caption("Turn-based campaign play, map uploads, and collaborative story prep.")

    idea_panel()
    config = get_config()
    client = require_supabase(config)

    with st.sidebar:
        st.header("Campaign Access (MVP)")
        st.caption("No login yet. Players join by campaign name and share code.")
        campaign_name = st.text_input("Campaign Name", placeholder="Shadows of Emberfall")
        player_name = st.text_input("Your Player Name", placeholder="Avery")
        join = st.button("Start / Join")

    if "campaign" not in st.session_state:
        st.session_state["campaign"] = None
    if "player_name" not in st.session_state:
        st.session_state["player_name"] = ""

    if join:
        if not campaign_name.strip() or not player_name.strip():
            st.warning("Enter both campaign name and player name.")
        else:
            st.session_state["campaign"] = get_or_create_campaign(client, campaign_name.strip())
            st.session_state["player_name"] = player_name.strip()
            st.success(f"Joined campaign {st.session_state['campaign']['name']}")

    campaign = st.session_state.get("campaign")
    if not campaign:
        st.info("Join a campaign from the sidebar to begin.")
        return

    campaign_id = campaign["id"]
    st.markdown(f"### Campaign: `{campaign['name']}` | Join Code: `{campaign['join_code']}`")

    tab1, tab2, tab3 = st.tabs(["Characters & Maps", "Turns", "Story Prep"])

    with tab1:
        left, right = st.columns(2)
        with left:
            st.subheader("Character Creation")
            character_name = st.text_input("Character Name", placeholder="Thorin Ironhide")
            archetype = st.selectbox("Archetype", list(CHARACTER_ARCHETYPES.keys()))
            notes = st.text_area("Backstory / Notes", placeholder="Former guard seeking redemption.")
            if st.button("Create Character", use_container_width=True):
                if character_name.strip():
                    create_character(
                        client=client,
                        campaign_id=campaign_id,
                        player_name=st.session_state["player_name"],
                        character_name=character_name.strip(),
                        archetype=archetype,
                        notes=notes.strip(),
                    )
                    st.success("Character created.")
                else:
                    st.warning("Character name is required.")

            st.subheader("Party")
            for row in list_characters(client, campaign_id):
                st.write(
                    f"**{row['name']}** ({row['archetype']}) "
                    f"| HP {row['hp']}/{row['max_hp']} "
                    f"| STR {row['strength']} AGI {row['agility']} ARC {row['arcana']}"
                )

        with right:
            st.subheader("Map Uploads (Supabase Storage)")
            uploaded = st.file_uploader("Upload map image", type=["png", "jpg", "jpeg", "webp"])
            if st.button("Save Map", use_container_width=True):
                if uploaded is None:
                    st.warning("Select an image first.")
                else:
                    upload_map_image(
                        client=client,
                        campaign_id=campaign_id,
                        uploaded_name=uploaded.name,
                        mime_type=uploaded.type or "application/octet-stream",
                        bytes_data=uploaded.getvalue(),
                        uploaded_by=st.session_state["player_name"],
                    )
                    st.success("Map uploaded.")

            maps = list_maps(client, campaign_id)
            for item in maps[:8]:
                st.caption(f"{item['filename']} - by {item['uploaded_by']}")
                st.image(item["public_url"])

    with tab2:
        st.subheader("Turn Engine")
        characters = list_characters(client, campaign_id)
        if not characters:
            st.info("Create at least one character before taking turns.")
        else:
            char_lookup = {f"{c['name']} ({c['archetype']})": c for c in characters}
            selected_label = st.selectbox("Character Taking Turn", list(char_lookup.keys()))
            action = st.selectbox("Action", TURN_ACTIONS)
            if st.button("Roll d20 + Submit Turn", use_container_width=True):
                character = char_lookup[selected_label]
                raw_roll = random.randint(1, 20)
                total_roll, hp_delta, result = compute_turn_effect(character, action, raw_roll)

                # hp_delta < 0 means damage against scene pressure; hp_delta > 0 heals character
                if hp_delta > 0:
                    healed_hp = min(int(character["max_hp"]), int(character["hp"]) + hp_delta)
                    update_character_hp(client, character["id"], healed_hp)

                narration = build_narration(
                    campaign_name=campaign["name"],
                    character_name=character["name"],
                    action=action,
                    raw_roll=raw_roll,
                    total_roll=total_roll,
                    hp_delta=hp_delta,
                    result=result,
                )
                add_turn(
                    client=client,
                    campaign_id=campaign_id,
                    character_id=character["id"],
                    action=action,
                    raw_roll=raw_roll,
                    total_roll=total_roll,
                    hp_delta=hp_delta,
                    narration=narration,
                )
                st.success(f"Turn submitted. Roll {raw_roll} (+bonus) -> total {total_roll}.")

            st.markdown("**Recent Turns**")
            for turn in list_turns(client, campaign_id):
                actor = turn.get("characters") or {}
                name = actor.get("name", "Unknown")
                st.write(
                    f"- **{name}** `{turn['action']}` | d20={turn['dice_roll']} "
                    f"total={turn['total_roll']} | effect={turn['effect_hp_delta']} | {turn['narration']}"
                )

    with tab3:
        story_prep_panel(
            client=client,
            campaign_id=campaign_id,
            campaign_name=campaign["name"],
            player_name=st.session_state["player_name"],
            gemini_api_key=config.gemini_api_key,
        )


if __name__ == "__main__":
    main()
