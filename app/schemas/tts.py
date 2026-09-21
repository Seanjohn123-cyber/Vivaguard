from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text content/prompt to be converted to speech audio or processed by LLM", example="Hello, welcome to VivaGuard.")
    voice: Optional[str] = Field("default", description="Voice identifier or style profile")
    sample_rate: Optional[int] = Field(24000, description="Audio sample rate in Hz (e.g. 16000, 24000)")
    format: Optional[str] = Field("wav", description="Target audio format (wav or pcm)")
    return_json: Optional[bool] = Field(False, description="If true, returns JSON with base64 encoded audio instead of binary audio stream")
    system_prompt: Optional[str] = Field(None, description="System prompt for the LLM voice agent")
    generate_reply: Optional[bool] = Field(True, description="Whether to run LLM reasoning to generate a reply before audio synthesis")


class TTSResponse(BaseModel):
    status: str = Field("success", description="Status of the text-to-audio operation")
    text: str = Field(..., description="Original input text prompt")
    reply_text: Optional[str] = Field(None, description="LLM generated response text spoken in audio")
    format: str = Field("wav", description="Audio format")
    sample_rate: int = Field(24000, description="Sample rate of generated audio")
    audio_base64: str = Field(..., description="Base64 encoded audio data")
    duration_seconds: float = Field(..., description="Estimated duration in seconds")


class ElevenLabsTTSRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    text: Optional[str] = Field("The first move is what sets everything in motion.", description="Text to convert to speech")
    voice_id: Optional[str] = Field("JBFqnCBsd6RMkjVDRZzb", description="ElevenLabs Voice ID (e.g. George)")
    model_id: Optional[str] = Field("eleven_v3", description="ElevenLabs Model ID (e.g. eleven_v3)")
    output_format: Optional[str] = Field("mp3_44100_128", description="Audio output format (e.g. mp3_44100_128)")
    return_json: Optional[bool] = Field(False, description="If true, returns JSON with base64 encoded audio instead of binary audio stream")


class ElevenLabsTTSResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str = Field("success", description="Status of the ElevenLabs TTS operation")
    text: str = Field(..., description="Text converted to speech")
    voice_id: str = Field(..., description="ElevenLabs Voice ID used")
    model_id: str = Field(..., description="ElevenLabs Model ID used")
    output_format: str = Field("mp3_44100_128", description="Audio format")
    audio_base64: str = Field(..., description="Base64 encoded audio data")
