from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vivaguard Broker"
    host: str = "0.0.0.0"
    port: int = 8000
    websocket_path: str = "/ws"
    max_connections: int = 100

    max_requests_per_minute: int = 60
    tokens_per_request: int = 1
    token_bucket_capacity: int = 50
    token_bucket_refill_rate: float = 5.0

    assemblyai_api_key: str = ""
    assemblyai_realtime_url: str = "wss://streaming.assemblyai.com/v3/ws?sample_rate=16000&speech_model=universal-3-5-pro"
    assemblyai_sample_rate: int = 16000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_fallback_model: str = "gemini-flash-latest"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
