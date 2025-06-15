"""Model download utilities."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List
from urllib.parse import urlparse

import requests
from tqdm import tqdm


class ModelDownloader:
    """Handle model downloading and verification."""
    
    # Default model URLs and metadata
    MODELS = {
        "v1_0": {
            "url": "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main",
            "files": [
                {
                    "name": "kokoro-v1_0.pth", 
                    "size": 327212226,  # ~312 MB (actual size on HuggingFace)
                    "sha256": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
                },
                {
                    "name": "config.json",
                    "size": 1439,
                    "sha256": None  # Small file, skip hash check
                },
            ],
            "voices": {
                "url": "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices",
                "files": [
                    # These are some of the available voices on HuggingFace
                    # The full list is much larger, but these provide a good starting set
                    "af_bella.pt", "af_nicole.pt", "af_sarah.pt", "af_sky.pt",
                    "am_adam.pt", "am_michael.pt", "bf_emma.pt", "bf_isabella.pt",
                    "bm_george.pt", "bm_lewis.pt",
                ]
            }
        }
    }
    
    def __init__(self, progress: bool = True):
        """Initialize downloader.
        
        Args:
            progress: Show progress bars
        """
        self.progress = progress
        
    def download(
        self, 
        output_dir: Path,
        version: str = "v1_0",
        url: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Download model files.
        
        Args:
            output_dir: Directory to save models
            version: Model version to download
            url: Optional custom URL
            force: Force redownload even if files exist
            
        Returns:
            True if successful
        """
        if version not in self.MODELS and not url:
            print(f"Unknown model version: {version}")
            return False
            
        model_info = self.MODELS.get(version, {})
        base_url = url or model_info.get("url")
        
        if not base_url:
            print("No download URL available")
            return False
            
        # Create output directory
        version_dir = output_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Check existing files
        if not force and self._check_existing_files(version_dir, model_info):
            print("✓ Models already downloaded")
            return True
            
        print(f"Downloading Kokoro {version} models...")
        
        # Download model files
        success = True
        for file_info in model_info.get("files", []):
            file_url = f"{base_url}/{file_info['name']}"
            file_path = version_dir / file_info["name"]
            
            if not self._download_file(file_url, file_path, file_info):
                success = False
                break
                
        # Download voice files
        if success and "voices" in model_info:
            voices_dir = output_dir / "voices" / version
            voices_dir.mkdir(parents=True, exist_ok=True)
            
            voice_info = model_info["voices"]
            print("\nDownloading voice packs...")
            
            for voice_file in voice_info["files"]:
                voice_url = f"{voice_info['url']}/{voice_file}"
                voice_path = voices_dir / voice_file
                
                if not force and voice_path.exists():
                    continue
                    
                if not self._download_file(voice_url, voice_path):
                    print(f"Warning: Failed to download voice {voice_file}")
                    # Don't fail completely if a voice fails
                    
        return success
    
    def _check_existing_files(self, version_dir: Path, model_info: Dict) -> bool:
        """Check if all required files exist."""
        for file_info in model_info.get("files", []):
            file_path = version_dir / file_info["name"]
            if not file_path.exists():
                return False
                
            # Check file size
            if "size" in file_info:
                actual_size = file_path.stat().st_size
                if abs(actual_size - file_info["size"]) > 1000:  # Allow small difference
                    print(f"File size mismatch for {file_info['name']}")
                    return False
                    
        return True
    
    def _download_file(
        self, 
        url: str, 
        output_path: Path,
        file_info: Optional[Dict] = None
    ) -> bool:
        """Download a single file with progress bar.
        
        Args:
            url: URL to download from
            output_path: Path to save file
            file_info: Optional file metadata
            
        Returns:
            True if successful
        """
        try:
            # Try using existing download script if available
            download_script = self._find_download_script()
            if download_script:
                return self._download_with_script(download_script, url, output_path)
                
            # Fallback to requests
            return self._download_with_requests(url, output_path, file_info)
            
        except Exception as e:
            print(f"Error downloading {output_path.name}: {e}")
            return False
    
    def _find_download_script(self) -> Optional[Path]:
        """Find the existing download_model.py script."""
        candidates = [
            Path(__file__).parent.parent.parent.parent.parent / "docker" / "scripts" / "download_model.py",
            Path.cwd() / "docker" / "scripts" / "download_model.py",
            Path("/app/docker/scripts/download_model.py"),
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
                
        return None
    
    def _download_with_script(self, script_path: Path, url: str, output_path: Path) -> bool:
        """Use existing download script."""
        try:
            # Extract filename from URL for the script
            filename = url.split("/")[-1]
            
            cmd = [
                sys.executable,
                str(script_path),
                "--output", str(output_path.parent),
                "--file", filename,
            ]
            
            if hasattr(self, "quiet") and self.quiet:
                cmd.append("--quiet")
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _download_with_requests(
        self, 
        url: str, 
        output_path: Path,
        file_info: Optional[Dict] = None
    ) -> bool:
        """Download using requests with progress bar."""
        headers = {"User-Agent": "kokoro-fastapi/1.0"}
        
        # Create temporary file
        temp_path = output_path.with_suffix(".tmp")
        
        try:
            with requests.get(url, headers=headers, stream=True) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                
                # Progress bar
                desc = f"Downloading {output_path.name}"
                progress_bar = None
                
                if self.progress and total_size > 0:
                    progress_bar = tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=desc,
                    )
                
                # Download
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            if progress_bar:
                                progress_bar.update(len(chunk))
                                
                if progress_bar:
                    progress_bar.close()
                    
            # Verify file
            if file_info:
                if not self._verify_file(temp_path, file_info):
                    temp_path.unlink(missing_ok=True)
                    return False
                    
            # Move to final location
            shutil.move(str(temp_path), str(output_path))
            return True
            
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            print(f"Download failed: {e}")
            return False
    
    def _verify_file(self, file_path: Path, file_info: Dict) -> bool:
        """Verify downloaded file."""
        # Check size
        if "size" in file_info:
            actual_size = file_path.stat().st_size
            expected_size = file_info["size"]
            
            if abs(actual_size - expected_size) > 1000:
                print(f"Size mismatch: expected {expected_size}, got {actual_size}")
                return False
                
        # Check hash
        if "sha256" in file_info and file_info["sha256"]:
            print("Verifying file integrity...")
            actual_hash = self._calculate_sha256(file_path)
            
            if actual_hash != file_info["sha256"]:
                print(f"Hash mismatch!")
                return False
                
        return True
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
                
        return sha256_hash.hexdigest()
    
    def list_available_models(self) -> List[str]:
        """List available model versions."""
        return list(self.MODELS.keys())
    
    def get_model_info(self, version: str) -> Optional[Dict]:
        """Get information about a model version."""
        return self.MODELS.get(version)


def download_models(
    output_dir: Path,
    version: str = "v1_0",
    url: Optional[str] = None,
    force: bool = False,
    quiet: bool = False,
) -> bool:
    """Convenience function to download models.
    
    Args:
        output_dir: Directory to save models
        version: Model version
        url: Optional custom URL
        force: Force redownload
        quiet: Suppress progress bars
        
    Returns:
        True if successful
    """
    downloader = ModelDownloader(progress=not quiet)
    return downloader.download(output_dir, version, url, force)