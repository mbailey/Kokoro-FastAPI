"""Model management CLI for Kokoro-FastAPI."""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

from kokoro_fastapi.utils.download import ModelDownloader
from kokoro_fastapi.utils.paths import PathResolver


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for model management."""
    parser = argparse.ArgumentParser(
        description="Kokoro model management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Download command
    download_parser = subparsers.add_parser(
        "download", 
        help="Download models",
        epilog="Example: kokoro-models download --output ~/models/kokoro"
    )
    download_parser.add_argument(
        "--output", "-o",
        default="~/models/kokoro",
        help="Output directory (default: ~/models/kokoro)"
    )
    download_parser.add_argument(
        "--version", "-v",
        default="v1_0",
        help="Model version to download (default: v1_0)"
    )
    download_parser.add_argument(
        "--url",
        help="Custom download URL (overrides default)"
    )
    download_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force redownload even if files exist"
    )
    download_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress bars"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List installed models"
    )
    list_parser.add_argument(
        "--dir", "-d",
        default="~/models/kokoro",
        help="Models directory (default: ~/models/kokoro)"
    )
    
    # Verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify model integrity"
    )
    verify_parser.add_argument(
        "--dir", "-d",
        default="~/models/kokoro",
        help="Models directory (default: ~/models/kokoro)"
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove old or corrupted models"
    )
    clean_parser.add_argument(
        "--dir", "-d",
        default="~/models/kokoro",
        help="Models directory (default: ~/models/kokoro)"
    )
    clean_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show information about available models"
    )
    info_parser.add_argument(
        "version",
        nargs="?",
        default="v1_0",
        help="Model version (default: v1_0)"
    )
    
    return parser


def cmd_download(args):
    """Handle download command."""
    output_path = Path(args.output).expanduser().absolute()
    
    print(f"Downloading Kokoro {args.version} models to {output_path}")
    
    downloader = ModelDownloader(progress=not args.quiet)
    success = downloader.download(
        output_path,
        version=args.version,
        url=args.url,
        force=args.force,
    )
    
    if success:
        print("\n✓ Models downloaded successfully")
        
        # Show what was downloaded
        model_path = output_path / args.version
        if model_path.exists():
            print(f"\nModel files in {model_path}:")
            for file in sorted(model_path.glob("*")):
                size_mb = file.stat().st_size / 1024 / 1024
                print(f"  - {file.name} ({size_mb:.1f} MB)")
    else:
        print("\n✗ Failed to download models")
        sys.exit(1)


def cmd_list(args):
    """Handle list command."""
    models_dir = Path(args.dir).expanduser().absolute()
    
    if not models_dir.exists():
        print(f"Models directory not found: {models_dir}")
        return
        
    print(f"Models in {models_dir}:\n")
    
    found_models = False
    for version_dir in sorted(models_dir.glob("v*")):
        if version_dir.is_dir():
            found_models = True
            print(f"Version: {version_dir.name}")
            
            # Check for model files
            model_files = list(version_dir.glob("*.pth")) + list(version_dir.glob("*.onnx"))
            config_files = list(version_dir.glob("*.json"))
            
            if model_files:
                print("  Model files:")
                for file in model_files:
                    size_mb = file.stat().st_size / 1024 / 1024
                    print(f"    - {file.name} ({size_mb:.1f} MB)")
                    
            if config_files:
                print("  Config files:")
                for file in config_files:
                    print(f"    - {file.name}")
                    
            # Check for voices
            voices_dir = models_dir / "voices" / version_dir.name
            if voices_dir.exists():
                voice_files = list(voices_dir.glob("*.pt"))
                if voice_files:
                    print(f"  Voice packs: {len(voice_files)} found")
                    
            print()
    
    if not found_models:
        print("No models found.")
        print("\nDownload models with: kokoro-models download")


def cmd_verify(args):
    """Handle verify command."""
    models_dir = Path(args.dir).expanduser().absolute()
    paths = PathResolver(str(models_dir))
    
    print(f"Verifying models in {models_dir}...\n")
    
    # Check basic structure
    issues = []
    
    if not models_dir.exists():
        print("✗ Models directory does not exist")
        sys.exit(1)
        
    if not paths.models_exist():
        issues.append("Required model files not found")
    else:
        print("✓ Model files found")
        
    if not paths.voices_exist():
        issues.append("Voice packs not found")
    else:
        print("✓ Voice packs found")
        
    # Check file integrity
    downloader = ModelDownloader()
    for version in ["v1_0"]:
        version_dir = models_dir / version
        if version_dir.exists():
            model_info = downloader.get_model_info(version)
            if model_info:
                print(f"\nChecking {version} files:")
                for file_info in model_info.get("files", []):
                    file_path = version_dir / file_info["name"]
                    if file_path.exists():
                        size = file_path.stat().st_size
                        expected = file_info.get("size", 0)
                        if expected and abs(size - expected) > 1000:
                            issues.append(f"{file_info['name']}: size mismatch")
                            print(f"  ✗ {file_info['name']} - size mismatch")
                        else:
                            print(f"  ✓ {file_info['name']}")
                    else:
                        issues.append(f"{file_info['name']}: missing")
                        print(f"  ✗ {file_info['name']} - missing")
    
    if issues:
        print(f"\n⚠ Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRun 'kokoro-models download --force' to redownload")
        sys.exit(1)
    else:
        print("\n✓ All models verified successfully")


def cmd_clean(args):
    """Handle clean command."""
    models_dir = Path(args.dir).expanduser().absolute()
    
    if not models_dir.exists():
        print(f"Models directory not found: {models_dir}")
        return
        
    print(f"Scanning {models_dir} for files to clean...\n")
    
    # Find temporary and backup files
    temp_patterns = ["*.tmp", "*.bak", "*.old", "*.download"]
    files_to_clean = []
    
    for pattern in temp_patterns:
        files_to_clean.extend(models_dir.rglob(pattern))
    
    if not files_to_clean:
        print("No temporary files found to clean.")
        return
        
    print(f"Found {len(files_to_clean)} file(s) to clean:")
    total_size = 0
    for file in files_to_clean:
        size = file.stat().st_size
        total_size += size
        print(f"  - {file.relative_to(models_dir)} ({size / 1024:.1f} KB)")
    
    print(f"\nTotal space to free: {total_size / 1024 / 1024:.1f} MB")
    
    if not args.yes:
        response = input("\nDelete these files? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Delete files
    deleted = 0
    for file in files_to_clean:
        try:
            file.unlink()
            deleted += 1
        except Exception as e:
            print(f"Error deleting {file}: {e}")
    
    print(f"\n✓ Deleted {deleted} file(s)")


def cmd_info(args):
    """Handle info command."""
    downloader = ModelDownloader()
    
    if args.version == "all":
        versions = downloader.list_available_models()
        print("Available model versions:")
        for version in versions:
            print(f"  - {version}")
        return
    
    info = downloader.get_model_info(args.version)
    if not info:
        print(f"No information available for version: {args.version}")
        print("\nAvailable versions:")
        for v in downloader.list_available_models():
            print(f"  - {v}")
        return
    
    print(f"Kokoro Model {args.version}:\n")
    
    # Model files
    print("Model files:")
    total_size = 0
    for file_info in info.get("files", []):
        size_mb = file_info.get("size", 0) / 1024 / 1024
        total_size += file_info.get("size", 0)
        print(f"  - {file_info['name']} ({size_mb:.1f} MB)")
    
    # Voice packs
    if "voices" in info:
        voice_count = len(info["voices"].get("files", []))
        print(f"\nVoice packs: {voice_count} available")
    
    print(f"\nTotal download size: ~{total_size / 1024 / 1024:.0f} MB")
    
    # Download info
    if "url" in info:
        print(f"\nDownload URL: {info['url']}")


def main():
    """Main entry point for kokoro-models command."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Dispatch to command handler
    handlers = {
        "download": cmd_download,
        "list": cmd_list,
        "verify": cmd_verify,
        "clean": cmd_clean,
        "info": cmd_info,
    }
    
    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\nError: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()