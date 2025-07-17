from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    experiment_id: str
    time_limit_seconds: int

    ssh_host: str
    ssh_port: int
    ssh_username: str
    ssh_password: str

    openai_api_key: str
    openai_model: str

    system_prompt_path: str

    summary_path: str
    history_path: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

load_dotenv()
settings = Settings()