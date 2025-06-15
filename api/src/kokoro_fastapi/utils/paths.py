"""Path resolution utilities for different installation methods."""

import os
from pathlib import Path
from typing import List, Optional


class PathResolver:
    """Resolve paths for different installation methods."""
    
    def __init__(self, models_dir: Optional[str] = None, voices_dir: Optional[str] = None):
        """Initialize path resolver.
        
        Args:
            models_dir: Optional models directory override
            voices_dir: Optional voices directory override
        """
        self.models_dir = self._resolve_models_dir(models_dir)
        self.voices_dir = self._resolve_voices_dir(voices_dir)
        self.project_root = self._find_project_root()
        self.api_src_dir = self._find_api_src_dir()
        self.web_player_path = self._find_web_player_path()
        
    def _resolve_models_dir(self, models_dir: Optional[str]) -> Path:
        """Resolve models directory from various sources.
        
        Priority:
        1. Provided argument
        2. KOKORO_MODELS_DIR environment variable
        3. MODEL_DIR environment variable (legacy)
        4. Default locations
        """
        # Priority 1: Direct argument
        if models_dir:
            return Path(models_dir).expanduser().absolute()
            
        # Priority 2: KOKORO_MODELS_DIR env var
        env_dir = os.environ.get("KOKORO_MODELS_DIR")
        if env_dir:
            return Path(env_dir).expanduser().absolute()
            
        # Priority 3: MODEL_DIR env var (legacy compatibility)
        legacy_dir = os.environ.get("MODEL_DIR")
        if legacy_dir:
            return Path(legacy_dir).expanduser().absolute()
            
        # Priority 4: Default locations
        default_locations = [
            # User home directory
            Path.home() / "models" / "kokoro",
            Path.home() / ".kokoro" / "models",
            # System locations
            Path("/opt/kokoro/models"),
            Path("/usr/local/share/kokoro/models"),
            # Docker location
            Path("/app/api/src/models"),
            # Local development
            self._find_project_root() / "api" / "src" / "models",
            Path("./api/src/models"),
        ]
        
        # Return first existing or first user location
        for loc in default_locations:
            if loc.exists():
                return loc.absolute()
                
        return default_locations[0].absolute()
    
    def _resolve_voices_dir(self, voices_dir: Optional[str]) -> Path:
        """Resolve voices directory."""
        # Priority 1: Direct argument
        if voices_dir:
            return Path(voices_dir).expanduser().absolute()
            
        # Priority 2: Environment variable
        env_dir = os.environ.get("KOKORO_VOICES_DIR") or os.environ.get("VOICES_DIR")
        if env_dir:
            return Path(env_dir).expanduser().absolute()
            
        # Priority 3: Relative to models directory
        return self.models_dir / "voices" / "v1_0"
    
    def _find_project_root(self) -> Path:
        """Find project root directory."""
        # Try various methods
        current = Path(__file__).resolve().parent
        
        # Look for marker files going up the directory tree
        markers = ["pyproject.toml", "setup.py", ".git"]
        max_levels = 10  # Prevent infinite loop
        
        for _ in range(max_levels):
            if any((current / marker).exists() for marker in markers):
                return current
            if current.parent == current:  # Reached root
                break
            current = current.parent
            
        # Fallback: assume we're in api/src/kokoro_fastapi/utils/
        # So project root is 5 levels up
        fallback = Path(__file__).resolve().parent.parent.parent.parent.parent
        if (fallback / "pyproject.toml").exists():
            return fallback
            
        # Last resort
        return Path.cwd()
    
    def _find_api_src_dir(self) -> Path:
        """Find the api/src directory."""
        candidates = [
            self.project_root / "api" / "src",
            Path(__file__).resolve().parent.parent.parent,  # Up from utils
            Path("/app/api/src"),  # Docker location
            Path.cwd() / "api" / "src",
        ]
        
        for candidate in candidates:
            if (candidate / "main.py").exists():
                return candidate.absolute()
                
        # Fallback
        return self.project_root / "api" / "src"
    
    def _find_web_player_path(self) -> Path:
        """Find web player directory."""
        candidates = [
            self.project_root / "web",
            Path("/app/web"),  # Docker location
            self.api_src_dir.parent.parent / "web",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate.absolute()
                
        return self.project_root / "web"
    
    def models_exist(self) -> bool:
        """Check if models are installed."""
        required_files = [
            "v1_0/kokoro-v1_0.pth",
            "v1_0/config.json",
        ]
        return all((self.models_dir / f).exists() for f in required_files)
    
    def voices_exist(self) -> bool:
        """Check if voice packs are installed."""
        return self.voices_dir.exists() and any(self.voices_dir.glob("*.pt"))
    
    def get_model_path(self, version: str = "v1_0") -> Path:
        """Get path to a specific model version."""
        return self.models_dir / version
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.voices_dir.mkdir(parents=True, exist_ok=True)
    
    def get_environment_vars(self) -> dict:
        """Get environment variables for the server."""
        return {
            "PROJECT_ROOT": str(self.project_root),
            "MODEL_DIR": str(self.models_dir),
            "VOICES_DIR": str(self.voices_dir),
            "WEB_PLAYER_PATH": str(self.web_player_path),
            "PYTHONPATH": f"{self.project_root}:{self.api_src_dir}",
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"""PathResolver:
  Project root: {self.project_root}
  API src dir: {self.api_src_dir}
  Models dir: {self.models_dir}
  Voices dir: {self.voices_dir}
  Web player: {self.web_player_path}
  Models exist: {self.models_exist()}
  Voices exist: {self.voices_exist()}"""


def resolve_paths(
    models_dir: Optional[str] = None, 
    voices_dir: Optional[str] = None
) -> PathResolver:
    """Convenience function to create a PathResolver."""
    return PathResolver(models_dir, voices_dir)