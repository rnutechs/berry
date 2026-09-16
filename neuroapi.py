# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "websockets",
#   "pydantic",
#   "python-dotenv",
# ]
# ///


from atexit import unregister
from argparse import Action
import sys
import asyncio
import os
from typing import Any

from dotenv import load_dotenv
from websockets.asyncio.server import serve, ServerConnection, Request
import pydantic


# data types
class ActionType(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True)
    name: str
    description: str
    schema_: dict[str, Any] | None = pydantic.Field(validation_alias="schema", serialization_alias="schema")
class CommandMessage(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True)
    command: str
    game: str
    data: dict[str, Any] | None
class GameSession:
    def __init__(self, websocket: ServerConnection):
        self.actions: list[ActionType] = []
        self.websocket: ServerConnection = websocket
        self.voice: bool = False
        self.speakers: dict[int, str] = {}


# handler for the server
game_sessions: dict[str, GameSession] = {}
game_sessions_lock: asyncio.Lock = asyncio.Lock()
async def neuroapi(websocket: ServerConnection) -> None:
    request = websocket.request
    if request == None: return
    path: str = request.path

    if path == "/":
        await json_handler(websocket)
        return

    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        for name, session in game_sessions.items():
            if session.voice != True or path != f"/game{name}/voice": continue
            await voice_handler(websocket)
            return
async def json_handler(websocket: ServerConnection) -> None:
    async for message in websocket:
        # message must be a string containing JSON
        if type(message) != str: continue

        # check for CommandMessage
        msg_json: CommandMessage | None = None
        try: msg_json: CommandMessage = CommandMessage.model_validate_json(message)
        except: continue

        # handle the CommandMessage
        match msg_json:
            case CommandMessage(command="startup"):
                await register_game(websocket, msg_json.game)
            case CommandMessage(command="context"):
                pass
            case CommandMessage(command=f"actions/register"):
                if msg_json.data == None or "actions" not in msg_json.data or type(msg_json.data["actions"]) != list[ActionType]: continue
                await register_action(msg_json.game, msg_json.data["actions"])
            case CommandMessage(command="actions/unregister"):
                if msg_json.data == None or "action_names" not in msg_json.data or type(msg_json.data["action_names"]) != list[str]: continue
                await unregister_action(msg_json.game, msg_json.data["action_names"])
            case CommandMessage(command="actions/force"):
                pass
            case CommandMessage(command="actions/result"):
                pass
            case CommandMessage(command="voice/start"):
                pass
            case CommandMessage(command="voice/speakers/register"):
                pass
            case CommandMessage(command="voice/speakers/unregister"):
                pass
            case _: continue
async def voice_handler(websocket: ServerConnection) -> None:
    async for message in websocket:
        if type(message) != bytes: continue

async def register_game(websocket: ServerConnection, game: str) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock: game_sessions[game] = GameSession(websocket)
async def register_action(game: str, actions: list[ActionType]) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        if game not in game_sessions: return
        session: GameSession = game_sessions[game]
        for action in actions:
            already_registered: bool = False
            for registered_action in session.actions:
                if action.name == registered_action.name:
                    already_registered = True
                    break
            if already_registered == True: continue
            session.actions.append(action)
async def unregister_action(game: str, action_names: list[str]) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        if game not in game_sessions: return
        session: GameSession = game_sessions[game]
        new_actions: list[ActionType] = []
        for action_name in action_names:
            for registered_action in session.actions:
                if action_name == registered_action.name: continue
                new_actions.append(registered_action)
        session.actions = new_actions
async def register_voice(game: str) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        if game not in game_sessions: return
        session: GameSession = game_sessions[game]
        session.voice = True
async def register_speaker(game: str, speakers: list[tuple[int, str]]) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        if game not in game_sessions or game_sessions[game].voice != True: return
        session: GameSession = game_sessions[game]
        for user in speakers: session.speakers[user[0]] = user[1]
async def unregister_speaker(game: str, speaker_ids: list[int]) -> None:
    global game_sessions, game_sessions_lock
    async with game_sessions_lock:
        if game not in game_sessions or game_sessions[game].voice != True: return
        session: GameSession = game_sessions[game]
        for speaker_id in speaker_ids:
            if speaker_id not in session.speakers: continue
            del session.speakers[speaker_id]


async def main() -> None:
    # load environment variables
    load_dotenv()
    ip_addr: str | None = os.getenv("NEURO_API_IP")
    if ip_addr == None:
        print("Could not find IP address environment variable NEURO_API_IP")
        sys.exit(1)
    port_str: str | None = os.getenv("NEURO_API_PORT")
    if port_str == None:
        print("Could not find port environment variable NEURO_API_PORT")
        sys.exit(1)
    port = None
    try: port: int = int(port_str)
    except Exception as e:
        print(f"Could not convert NEURO_API_PORT to integer: {str(e)}")
        sys.exit(1)

    # start server
    print(f"Running server on ws://{ip_addr}:{port}...")
    server = await serve(neuroapi, ip_addr, port)
    await server.serve_forever()
asyncio.run(main())