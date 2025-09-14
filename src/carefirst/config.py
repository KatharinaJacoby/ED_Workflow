from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_backend: str = "mock"  # "mock" or "ollama"
    ollama_url: str = "http://localhost:11434"
    model_name: str = "llama3.2:3b-instruct"
    temperature: float = 0.3
    top_p: float = 0.9
    max_tokens: int = 160

    class Config:
        env_file = ".env"

settings = Settings()
