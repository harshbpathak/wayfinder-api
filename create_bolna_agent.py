"""
Create the NITH Wayfinder voice agent on Bolna via the REST API.

Usage:
    python create_bolna_agent.py

Environment variables:
    BOLNA_API_KEY   — your Bolna API key (bn-...)
    LOCATE_API_URL  — your deployed /locate endpoint URL
    LOCATE_API_KEY  — the x-api-key for your deployed /locate endpoint
"""

import json
import os
import sys
from pathlib import Path

import httpx

# ── Configuration ──
BOLNA_API_URL = "https://api.bolna.ai"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# Read system prompt
PROMPT_PATH = Path(__file__).parent / "bolna-system-prompt.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()


def create_agent():
    """Create the NITH Wayfinder agent on Bolna."""
    bolna_api_key = required_env("BOLNA_API_KEY")
    locate_api_url = required_env("LOCATE_API_URL")
    locate_api_key = required_env("LOCATE_API_KEY")

    # Build the custom function tool for locate_place
    locate_tool = {
        "name": "locate_place",
        "description": (
            "Use this function whenever the caller asks where a NIT Hamirpur campus "
            "building, department, hostel, lecture hall, facility, or landmark is located."
        ),
        "pre_call_message": "Let me check that location for you.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The place the caller wants to find, such as CSE department, library, hostel, or lecture hall."
                },
                "origin": {
                    "type": "string",
                    "description": "Where the caller is starting from, such as gate 1, kailash hostel, or library. Optional."
                }
            },
            "required": ["query"]
        },
        "key": "custom_task",
        "value": {
            "method": "GET",
            "param": {
                "query": "%(query)s",
                "origin": "%(origin)s"
            },
            "url": locate_api_url,
            "headers": {"x-api-key": locate_api_key}
        }
    }

    # Agent payload (Bolna v2 API)
    agent_config = {
        "agent_name": "NITH Campus Wayfinder",
        "agent_type": "other",
        "agent_welcome_message": (
            "Hello! I'm the NIT Hamirpur campus wayfinder. "
            "Tell me which building, department, or hostel you're looking for, "
            "and I'll give you directions. Where are you starting from?"
        ),
        "tasks": [
            {
                "task_type": "conversation",
                "optimize_latency": True,
                "tools_config": {
                    "llm_agent": {
                        "model": "gpt-4o-mini",
                        "max_tokens": 256,
                        "temperature": 0.3,
                        "family": "openai",
                        "agent_flow_type": "streaming",
                        "use_fallback": True,
                    },
                    "synthesizer": {
                        "provider": "cartesia",
                        "provider_config": {
                            "voice": "a167e0f3-df7e-4277-976b-5b1c23c9b486",
                            "voice_name": "Classy British Man",
                        },
                        "audio_format": "pcm",
                        "stream": True,
                        "buffer_size": 100,
                    },
                    "transcriber": {
                        "model": "deepgram",
                        "stream": True,
                        "language": "en",
                        "endpointing": 300,
                        "keywords": (
                            "CSE:2,ECE:2,library:2,hostel:2,kailash:2,himadri:2,"
                            "dhauladhar:2,mega mess:2,placement:2,LHC:2,auditorium:2,"
                            "canteen:2,gate:2,NITH:2,vivekananda:2"
                        ),
                    },
                    "input": {
                        "provider": "default",
                        "format": "pcm",
                    },
                    "output": {
                        "provider": "default",
                        "format": "pcm",
                    },
                },
                "task_config": {
                    "hangup_after_silence": 15,
                    "optimize_latency": True,
                    "incremental_delay": 300,
                    "ambient_noise": False,
                    "number_of_words_for_interruption": 3,
                },
                "toolchain": {
                    "execution": "parallel",
                    "pipelines": [["transcriber", "llm", "synthesizer"]]
                },
            }
        ],
        "agent_prompts": {
            "task_1": {
                "system_prompt": SYSTEM_PROMPT,
            }
        },
    }
    agent_payload = {
        "agent_config": agent_config,
        "agent_prompts": agent_config.pop("agent_prompts"),
    }

    print("Creating NITH Wayfinder agent on Bolna...\n")
    print(f"API URL: {BOLNA_API_URL}")
    print(f"Locate endpoint: {locate_api_url}\n")

    try:
        # Create the agent
        response = httpx.post(
            f"{BOLNA_API_URL}/v2/agent",
            json=agent_payload,
            headers={
                "Authorization": f"Bearer {bolna_api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

        if response.status_code in (200, 201):
            result = response.json()
            agent_id = result.get("agent_id", result.get("id", "unknown"))
            print(f"✅ Agent created successfully!")
            print(f"   Agent ID: {agent_id}")
            print(f"\n📋 Next steps:")
            print(f"   1. Go to https://app.bolna.ai and find your agent")
            print(f"   2. Add the locate_place custom function tool")
            print(f"   3. Attach a phone number to the agent")
            print(f"   4. Test in the Bolna playground")
            print(f"\n📌 Custom function config (paste in Bolna Tools section):")
            print(json.dumps(locate_tool, indent=2))
            return result
        else:
            print(f"❌ Failed to create agent: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except httpx.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        return None


if __name__ == "__main__":
    create_agent()
