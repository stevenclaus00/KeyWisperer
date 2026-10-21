from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import tempfile
import aiofiles
import json
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import OpenAI STT from emergentintegrations
from emergentintegrations.llm.openai import OpenAISpeechToText

# Initialize STT with Emergent LLM Key
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")
stt = None
if EMERGENT_LLM_KEY:
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    logger.info("OpenAI Speech-to-Text initialized successfully")
else:
    logger.warning("EMERGENT_LLM_KEY not found - transcription will not work")

# WebSocket connection manager for PC clients
class PCConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"PC client connected: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"PC client disconnected: {client_id}")
    
    async def send_to_pc(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
            return True
        return False
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

pc_manager = PCConnectionManager()

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class TranscriptionResponse(BaseModel):
    text: str
    success: bool
    error: Optional[str] = None
    history_id: Optional[str] = None

class VoiceCommand(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger: str
    action: str
    action_type: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class VoiceCommandCreate(BaseModel):
    trigger: str
    action: str
    action_type: str
    enabled: bool = True

# Legacy settings model (kept for backward compatibility)
class AppSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    immediate_insertion: bool = True
    chunk_duration_ms: int = 3000
    language: str = "en"
    auto_punctuation: bool = True
    pc_connection_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AppSettingsUpdate(BaseModel):
    immediate_insertion: Optional[bool] = None
    chunk_duration_ms: Optional[int] = None
    language: Optional[str] = None
    auto_punctuation: Optional[bool] = None
    pc_connection_enabled: Optional[bool] = None

# ─────── Profile Models ───────

class Profile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    custom_vocabulary: List[str] = []
    immediate_insertion: bool = True
    chunk_duration_ms: int = 3000
    language: str = "en"
    auto_punctuation: bool = True
    pc_connection_enabled: bool = True
    # Smart formatting toggles
    auto_capitalize: bool = True
    paragraph_breaks: bool = True
    number_formatting: bool = True
    smart_quotes: bool = False
    is_active: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProfileCreate(BaseModel):
    name: str
    custom_vocabulary: List[str] = []
    immediate_insertion: bool = True
    chunk_duration_ms: int = 3000
    language: str = "en"
    auto_punctuation: bool = True
    pc_connection_enabled: bool = True
    auto_capitalize: bool = True
    paragraph_breaks: bool = True
    number_formatting: bool = True
    smart_quotes: bool = False

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    custom_vocabulary: Optional[List[str]] = None
    immediate_insertion: Optional[bool] = None
    chunk_duration_ms: Optional[int] = None
    language: Optional[str] = None
    auto_punctuation: Optional[bool] = None
    pc_connection_enabled: Optional[bool] = None
    auto_capitalize: Optional[bool] = None
    paragraph_breaks: Optional[bool] = None
    number_formatting: Optional[bool] = None
    smart_quotes: Optional[bool] = None

# ─────── Transcription History Models ───────

class TranscriptionHistoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    profile_id: str = ""
    profile_name: str = "Default"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = 0
    duration_seconds: Optional[float] = None

class TranscriptionHistoryCreate(BaseModel):
    text: str
    profile_id: str = ""
    profile_name: str = "Default"
    duration_seconds: Optional[float] = None

class TranscriptionHistoryUpdate(BaseModel):
    text: Optional[str] = None

class PCCommand(BaseModel):
    command_type: str
    payload: dict

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@api_router.get("/")
async def root():
    return {"message": "VoiceKey AI Backend", "version": "2.0.0"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "stt_available": stt is not None,
        "pc_connections": len(pc_manager.active_connections)
    }

# ─────── Transcription ───────

@api_router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    profile_id: Optional[str] = Form(None),
    save_to_history: Optional[bool] = Form(True),
    duration_seconds: Optional[float] = Form(None),
):
    if not stt:
        raise HTTPException(status_code=500, detail="Speech-to-text service not configured")
    
    try:
        file_ext = audio.filename.split('.')[-1] if audio.filename else 'wav'
        if file_ext not in ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']:
            file_ext = 'wav'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"Processing audio file: {tmp_path}, size: {len(content)} bytes")
        
        # Build custom vocabulary prompt from active profile
        prompt = None
        profile_name = "Default"
        if profile_id:
            profile_doc = await db.profiles.find_one({"id": profile_id})
            if profile_doc:
                vocab = profile_doc.get("custom_vocabulary", [])
                if vocab:
                    prompt = ", ".join(vocab)
                profile_name = profile_doc.get("name", "Default")
        
        # Transcribe using Whisper with optional vocabulary prompt
        transcribe_kwargs: Dict[str, Any] = {
            "model": "whisper-1",
            "response_format": "json",
            "language": "en",
        }
        if prompt:
            transcribe_kwargs["prompt"] = prompt
        
        with open(tmp_path, "rb") as audio_file:
            response = await stt.transcribe(file=audio_file, **transcribe_kwargs)
        
        os.unlink(tmp_path)
        
        transcribed_text = response.text if hasattr(response, 'text') else str(response)
        logger.info(f"Transcription successful: {transcribed_text[:100]}")
        
        return TranscriptionResponse(text=transcribed_text, success=True)
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return TranscriptionResponse(text="", success=False, error=str(e))

# ─────── Voice Commands ───────

@api_router.get("/voice-commands", response_model=List[VoiceCommand])
async def get_voice_commands():
    commands = await db.voice_commands.find().to_list(100)
    return [VoiceCommand(**cmd) for cmd in commands]

@api_router.post("/voice-commands", response_model=VoiceCommand)
async def create_voice_command(command: VoiceCommandCreate):
    cmd_obj = VoiceCommand(**command.dict())
    await db.voice_commands.insert_one(cmd_obj.dict())
    return cmd_obj

@api_router.put("/voice-commands/{command_id}", response_model=VoiceCommand)
async def update_voice_command(command_id: str, command: VoiceCommandCreate):
    result = await db.voice_commands.find_one_and_update(
        {"id": command_id},
        {"$set": command.dict()},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Command not found")
    return VoiceCommand(**result)

@api_router.delete("/voice-commands/{command_id}")
async def delete_voice_command(command_id: str):
    result = await db.voice_commands.delete_one({"id": command_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"message": "Command deleted"}

@api_router.post("/voice-commands/init-defaults")
async def init_default_commands():
    defaults = [
        {"trigger": "new line", "action": "ENTER", "action_type": "key"},
        {"trigger": "newline", "action": "ENTER", "action_type": "key"},
        {"trigger": "period", "action": ".", "action_type": "text"},
        {"trigger": "comma", "action": ",", "action_type": "text"},
        {"trigger": "question mark", "action": "?", "action_type": "text"},
        {"trigger": "exclamation", "action": "!", "action_type": "text"},
        {"trigger": "tab", "action": "TAB", "action_type": "key"},
        {"trigger": "backspace", "action": "BACKSPACE", "action_type": "key"},
        {"trigger": "delete that", "action": "SELECT_ALL_DELETE", "action_type": "macro"},
        {"trigger": "select all", "action": "CTRL+A", "action_type": "key"},
        {"trigger": "copy", "action": "CTRL+C", "action_type": "key"},
        {"trigger": "paste", "action": "CTRL+V", "action_type": "key"},
    ]
    created = []
    for default in defaults:
        existing = await db.voice_commands.find_one({"trigger": default["trigger"]})
        if not existing:
            cmd = VoiceCommand(**default)
            await db.voice_commands.insert_one(cmd.dict())
            created.append(cmd)
    return {"message": f"Created {len(created)} default commands", "commands": created}

# ─────── Legacy Settings (backward compat) ───────

@api_router.get("/settings", response_model=AppSettings)
async def get_settings():
    settings = await db.app_settings.find_one()
    if not settings:
        default_settings = AppSettings()
        await db.app_settings.insert_one(default_settings.dict())
        return default_settings
    return AppSettings(**settings)

@api_router.put("/settings", response_model=AppSettings)
async def update_settings(settings_update: AppSettingsUpdate):
    current_settings = await db.app_settings.find_one()
    if not current_settings:
        current_settings = AppSettings().dict()
    update_data = {k: v for k, v in settings_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db.app_settings.update_one(
        {"id": current_settings.get("id")},
        {"$set": update_data},
        upsert=True
    )
    updated = await db.app_settings.find_one()
    return AppSettings(**updated)

# ─────── Profiles ───────

@api_router.get("/profiles", response_model=List[Profile])
async def get_profiles():
    profiles = await db.profiles.find().sort("created_at", 1).to_list(100)
    if not profiles:
        # Create default profile if none exist
        default_profile = Profile(name="Default", is_active=True)
        await db.profiles.insert_one(default_profile.dict())
        return [default_profile]
    return [Profile(**p) for p in profiles]

@api_router.post("/profiles", response_model=Profile)
async def create_profile(profile_data: ProfileCreate):
    profile = Profile(**profile_data.dict())
    # If this is the first profile, make it active
    count = await db.profiles.count_documents({})
    if count == 0:
        profile.is_active = True
    await db.profiles.insert_one(profile.dict())
    return profile

@api_router.get("/profiles/active", response_model=Profile)
async def get_active_profile():
    profile = await db.profiles.find_one({"is_active": True})
    if not profile:
        # Return first profile or create default
        profile = await db.profiles.find_one()
        if not profile:
            default_profile = Profile(name="Default", is_active=True)
            await db.profiles.insert_one(default_profile.dict())
            return default_profile
        # Activate the first profile
        await db.profiles.update_one({"id": profile["id"]}, {"$set": {"is_active": True}})
    return Profile(**profile)

@api_router.put("/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str):
    # Deactivate all profiles
    await db.profiles.update_many({}, {"$set": {"is_active": False}})
    # Activate the target profile
    result = await db.profiles.find_one_and_update(
        {"id": profile_id},
        {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Profile(**result)

@api_router.put("/profiles/{profile_id}", response_model=Profile)
async def update_profile(profile_id: str, profile_update: ProfileUpdate):
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    result = await db.profiles.find_one_and_update(
        {"id": profile_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Profile(**result)

@api_router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    # Don't delete if it's the only profile
    count = await db.profiles.count_documents({})
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last profile")
    
    profile = await db.profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    was_active = profile.get("is_active", False)
    await db.profiles.delete_one({"id": profile_id})
    
    # If deleted profile was active, activate the first remaining
    if was_active:
        first = await db.profiles.find_one()
        if first:
            await db.profiles.update_one({"id": first["id"]}, {"$set": {"is_active": True}})
    
    return {"message": "Profile deleted"}

# ─────── Transcription History ───────

@api_router.get("/history", response_model=List[TranscriptionHistoryItem])
async def get_history(limit: int = 50, skip: int = 0):
    items = await db.transcription_history.find().sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    return [TranscriptionHistoryItem(**item) for item in items]

@api_router.post("/history", response_model=TranscriptionHistoryItem)
async def save_to_history(item_data: TranscriptionHistoryCreate):
    word_count = len(item_data.text.split()) if item_data.text else 0
    item = TranscriptionHistoryItem(
        **item_data.dict(),
        word_count=word_count
    )
    await db.transcription_history.insert_one(item.dict())
    return item

@api_router.put("/history/{item_id}", response_model=TranscriptionHistoryItem)
async def update_history_item(item_id: str, update_data: TranscriptionHistoryUpdate):
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    if "text" in update_fields:
        update_fields["word_count"] = len(update_fields["text"].split())
    
    result = await db.transcription_history.find_one_and_update(
        {"id": item_id},
        {"$set": update_fields},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="History item not found")
    return TranscriptionHistoryItem(**result)

@api_router.delete("/history/{item_id}")
async def delete_history_item(item_id: str):
    result = await db.transcription_history.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"message": "History item deleted"}

@api_router.delete("/history")
async def clear_history():
    result = await db.transcription_history.delete_many({})
    return {"message": f"Deleted {result.deleted_count} history items"}

# ─────── PC Connection ───────

@app.websocket("/ws/pc/{client_id}")
async def websocket_pc_endpoint(websocket: WebSocket, client_id: str):
    await pc_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        pc_manager.disconnect(client_id)

@api_router.post("/send-to-pc/{client_id}")
async def send_to_pc(client_id: str, command: PCCommand):
    message = {"type": command.command_type, "payload": command.payload}
    success = await pc_manager.send_to_pc(client_id, message)
    if not success:
        raise HTTPException(status_code=404, detail="PC client not connected")
    return {"success": True}

@api_router.post("/broadcast-to-pcs")
async def broadcast_to_pcs(command: PCCommand):
    if not pc_manager.active_connections:
        raise HTTPException(status_code=404, detail="No PC clients connected")
    message = {"type": command.command_type, "payload": command.payload}
    await pc_manager.broadcast(message)
    return {"success": True, "clients": len(pc_manager.active_connections)}

@api_router.get("/connected-pcs")
async def get_connected_pcs():
    return {
        "count": len(pc_manager.active_connections),
        "client_ids": list(pc_manager.active_connections.keys())
    }

# Legacy
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**s) for s in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
