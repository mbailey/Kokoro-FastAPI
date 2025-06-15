"""System dependency checking utilities."""

import platform
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


def check_system_dependencies(skip_optional: bool = False) -> bool:
    """Check for required and optional system dependencies.
    
    Args:
        skip_optional: Skip checking optional dependencies
        
    Returns:
        True if all required dependencies are found
    """
    deps = get_required_dependencies()
    missing_required = []
    missing_optional = []
    warnings = []
    
    print("Checking system dependencies...")
    
    for name, spec in deps.items():
        if skip_optional and not spec.get("required", True):
            continue
            
        result = check_dependency(name, spec)
        
        if result["status"] == "missing":
            if spec.get("required", True):
                missing_required.append((name, result))
            else:
                missing_optional.append((name, result))
        elif result["status"] == "warning":
            warnings.append((name, result))
        else:
            print(f"  ✓ {name} found")
    
    # Report results
    if missing_required or missing_optional or warnings:
        print_dependency_report(missing_required, missing_optional, warnings)
    else:
        print("  ✓ All dependencies satisfied")
    
    return len(missing_required) == 0


def get_required_dependencies() -> Dict[str, Dict]:
    """Get required and optional system dependencies."""
    system = platform.system()
    
    deps = {
        "python": {
            "commands": [sys.executable, "--version"],
            "min_version": "3.10",
            "required": True,
            "parse_version": lambda output: output.split()[1],
        },
        "espeak-ng": {
            "commands": ["espeak-ng", "--version"],
            "fallback_commands": [["espeak", "--version"]],
            "required": False,
            "feature": "phonemization (text-to-phoneme conversion)",
            "install": {
                "Linux": "sudo apt-get install espeak-ng",
                "Darwin": "brew install espeak-ng",
                "Windows": "Download from https://github.com/espeak-ng/espeak-ng/releases",
            },
        },
        "ffmpeg": {
            "commands": ["ffmpeg", "-version"],
            "required": False,
            "feature": "audio format conversion (MP3, OGG, etc.)",
            "install": {
                "Linux": "sudo apt-get install ffmpeg",
                "Darwin": "brew install ffmpeg",
                "Windows": "Download from https://ffmpeg.org/download.html",
            },
        },
    }
    
    # Add CUDA check for Linux/Windows
    if system in ["Linux", "Windows"]:
        deps["cuda"] = {
            "commands": ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            "required": False,
            "feature": "GPU acceleration",
            "install": {
                "Linux": "Install NVIDIA drivers from your distribution",
                "Windows": "Download from https://www.nvidia.com/drivers",
            },
        }
    
    return deps


def check_dependency(name: str, spec: Dict) -> Dict:
    """Check a single dependency.
    
    Args:
        name: Dependency name
        spec: Dependency specification
        
    Returns:
        Dict with status and additional info
    """
    commands = spec.get("commands", [])
    
    # Try primary command
    if shutil.which(commands[0]):
        # Found, check version if needed
        if "min_version" in spec:
            try:
                output = subprocess.check_output(
                    commands, 
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Parse version if parser provided
                if "parse_version" in spec:
                    version = spec["parse_version"](output.strip())
                else:
                    version = extract_version(output)
                
                if version and not check_version(version, spec["min_version"]):
                    return {
                        "status": "warning",
                        "message": f"Version {version} is older than recommended {spec['min_version']}",
                    }
            except Exception:
                pass  # Version check failed, but command exists
                
        return {"status": "found"}
    
    # Try fallback commands
    for fallback_cmd in spec.get("fallback_commands", []):
        if shutil.which(fallback_cmd[0]):
            return {
                "status": "warning", 
                "message": f"Found {fallback_cmd[0]} instead of {commands[0]}",
            }
    
    return {
        "status": "missing",
        "feature": spec.get("feature"),
        "install": spec.get("install", {}),
        "required": spec.get("required", True),
    }


def extract_version(output: str) -> Optional[str]:
    """Extract version number from command output."""
    import re
    
    # Common version patterns
    patterns = [
        r"version\s+(\d+\.\d+(?:\.\d+)?)",
        r"v(\d+\.\d+(?:\.\d+)?)",
        r"(\d+\.\d+(?:\.\d+)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def check_version(version: str, min_version: str) -> bool:
    """Check if version meets minimum requirement."""
    try:
        from packaging import version as pkg_version
        return pkg_version.parse(version) >= pkg_version.parse(min_version)
    except ImportError:
        # Fallback to simple string comparison
        return version >= min_version


def print_dependency_report(
    missing_required: List[Tuple[str, Dict]],
    missing_optional: List[Tuple[str, Dict]], 
    warnings: List[Tuple[str, Dict]]
):
    """Print a formatted dependency report."""
    system = platform.system()
    
    # Warnings
    if warnings:
        print("\nWarnings:")
        for name, result in warnings:
            print(f"  ⚠ {name}: {result['message']}")
    
    # Missing optional
    if missing_optional:
        print("\nOptional dependencies not found:")
        for name, result in missing_optional:
            print(f"  ✗ {name}")
            if feature := result.get("feature"):
                print(f"    Feature: {feature}")
            if install := result.get("install", {}).get(system):
                print(f"    Install: {install}")
    
    # Missing required
    if missing_required:
        print("\nRequired dependencies not found:")
        for name, result in missing_required:
            print(f"  ✗ {name} (REQUIRED)")
            if install := result.get("install", {}).get(system):
                print(f"    Install: {install}")
        print("\nSome required dependencies are missing!")
        print("Please install them before continuing.")


if __name__ == "__main__":
    # Test the dependency checker
    success = check_system_dependencies()
    sys.exit(0 if success else 1)