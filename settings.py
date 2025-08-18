"""
Configuración de la aplicación Semantic Search
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # Buscar archivo .env en el directorio actual
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from: {env_path}")
    else:
        print("No .env file found, using system environment variables")
except ImportError:
    print("python-dotenv not installed, using system environment variables only")


class Settings(BaseModel):
    """Configuración de la aplicación"""
    
    # Configuración de Victor Database
    victor_table_socket: str = Field(
        default="/tmp/victor_default_table.sock",
        description="Path al socket Unix de VictorDB Table"
    )
    
    victor_index_socket: str = Field(
        default="/tmp/victor_default_index.sock", 
        description="Path al socket Unix de VictorDB Index"
    )
    
    # Configuración de la API
    api_host: str = Field(default="0.0.0.0", description="Host de la API")
    api_port: int = Field(default=8000, description="Puerto de la API")
    api_reload: bool = Field(default=True, description="Auto-reload en desarrollo")
    api_log_level: str = Field(default="info", description="Nivel de logging")
    
    # Configuración CORS
    cors_origins: list[str] = Field(
        default=["*"], 
        description="Orígenes permitidos para CORS"
    )
    
    # Configuración de búsqueda
    max_search_results: int = Field(
        default=50, 
        description="Máximo número de resultados de búsqueda"
    )
    default_search_results: int = Field(
        default=10,
        description="Número por defecto de resultados de búsqueda"
    )


def load_settings_from_env() -> Settings:
    """Carga la configuración desde variables de entorno"""
    return Settings(
        victor_table_socket=os.getenv("SEMANTIC_VICTOR_TABLE_SOCKET", "/tmp/victor_default_table.sock"),
        victor_index_socket=os.getenv("SEMANTIC_VICTOR_INDEX_SOCKET", "/tmp/victor_default_index.sock"),
        api_host=os.getenv("SEMANTIC_API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("SEMANTIC_API_PORT", "8000")),
        api_reload=os.getenv("SEMANTIC_API_RELOAD", "true").lower() == "true",
        api_log_level=os.getenv("SEMANTIC_API_LOG_LEVEL", "info"),
        cors_origins=os.getenv("SEMANTIC_CORS_ORIGINS", "*").split(","),
        max_search_results=int(os.getenv("SEMANTIC_MAX_SEARCH_RESULTS", "50")),
        default_search_results=int(os.getenv("SEMANTIC_DEFAULT_SEARCH_RESULTS", "10"))
    )


# Instancia global de configuración
settings = load_settings_from_env()


def get_settings() -> Settings:
    """Obtiene la configuración de la aplicación"""
    return settings
