# Proposal: Python Package Distribution for Kokoro-FastAPI

## Executive Summary

This proposal outlines a plan to enhance Kokoro-FastAPI to support distribution and usage as a standard Python package while maintaining full compatibility with the existing Docker-based deployment model. This dual-mode approach will significantly expand the project's accessibility and use cases without compromising its current functionality.

## Background

Kokoro-FastAPI is currently designed as a Docker-first FastAPI wrapper for the Kokoro-82M text-to-speech model. While Docker provides excellent isolation and reproducibility, there are compelling reasons to also support direct Python package installation:

1. **Developer Experience**: Python developers expect to `pip install` packages
2. **Integration**: Easier to integrate into existing Python applications
3. **Development**: Faster iteration without container rebuilds
4. **Deployment Flexibility**: Some environments don't support Docker
5. **Resource Efficiency**: No container overhead for simple use cases

## Goals

### Primary Goals
1. Enable installation via `pip install kokoro-fastapi` (future PyPI release)
2. Support running via `uvx` from GitHub repository (immediate)
3. Maintain 100% compatibility with existing Docker deployment
4. Provide clear system dependency management
5. Support flexible model storage locations

### Secondary Goals
1. Enable programmatic usage as a Python library
2. Support Jupyter notebook usage
3. Facilitate cloud function deployments
4. Improve developer onboarding experience

## Non-Goals
1. Replacing Docker as the primary deployment method
2. Bundling model files within the package
3. Automated system dependency installation
4. Windows system dependency management (initially)

## Proposed Approach

### 1. Package Structure Enhancement

The current package structure is already well-organized. We'll enhance it with:

```
kokoro-fastapi/
├── api/
│   └── src/
│       ├── kokoro_fastapi/        # CLI and utilities package
│       │   ├── __init__.py
│       │   ├── launcher.py        # Main entry point
│       │   ├── cli.py            # Future CLI commands
│       │   └── utils.py          # Shared utilities
│       ├── core/                  # Existing core package
│       ├── inference/             # Existing inference package
│       ├── routers/               # Existing routers
│       └── services/              # Existing services
├── docs/
│   └── specs/
│       └── python-packaging/      # This specification
├── pyproject.toml                 # Enhanced with package metadata
└── README.md                      # Updated with package instructions
```

### 2. Installation Methods

#### Method A: Direct from GitHub (Immediate)
```bash
# One-time run
uvx --from git+https://github.com/mbailey/Kokoro-FastAPI kokoro-start

# Install as tool
uv tool install git+https://github.com/mbailey/Kokoro-FastAPI
kokoro-start --models-dir ~/models/kokoro
```

#### Method B: From PyPI (Future)
```bash
# Standard pip
pip install kokoro-fastapi

# With GPU support
pip install kokoro-fastapi[gpu]

# With uv
uv pip install kokoro-fastapi
```

### 3. Configuration Flexibility

#### Environment Variables (Existing)
```bash
export KOKORO_MODELS_DIR=~/models/kokoro
export KOKORO_VOICES_DIR=~/models/kokoro/voices
kokoro-start
```

#### Command Line Arguments (Enhanced)
```bash
kokoro-start \
  --models-dir ~/models/kokoro \
  --host 0.0.0.0 \
  --port 8880 \
  --workers 4
```

#### Configuration File (Future)
```yaml
# ~/.config/kokoro/config.yaml
models_dir: ~/models/kokoro
voices_dir: ~/models/kokoro/voices
default_voice: af_bella
gpu: auto
```

### 4. System Dependencies

#### Startup Verification
The launcher will check for required system dependencies and provide platform-specific installation instructions:

```
Checking system dependencies...
✓ Python 3.10+ found
✓ ffmpeg found
✗ espeak-ng not found

To install espeak-ng:
  Ubuntu/Debian: sudo apt-get install espeak-ng
  macOS:         brew install espeak-ng
  Windows:       Download from https://github.com/espeak-ng/espeak-ng/releases

Some features may not work without espeak-ng.
Continue anyway? [y/N]
```

#### Graceful Degradation
- Core TTS functionality works without espeak-ng (using fallback phonemizer)
- Audio format conversion works without ffmpeg (WAV only)
- Clear error messages when features are unavailable

### 5. Model Management

#### Automatic Download
```python
# First run
$ kokoro-start
Models not found at ~/models/kokoro/v1_0
Download Kokoro v1.0 models? (~500MB) [Y/n]: y
Downloading models... ████████████████████ 100%
Models installed successfully!
```

#### Manual Download
```bash
# Separate command for model management
kokoro-models download --output ~/models/kokoro
kokoro-models list
kokoro-models clean
```

### 6. Usage Patterns

#### CLI Server (Primary)
```bash
# Start the FastAPI server
kokoro-start --models-dir ~/models/kokoro

# With custom settings
kokoro-start --host 0.0.0.0 --port 8080 --workers 4
```

#### Python API (Future Enhancement)
```python
from kokoro_fastapi import KokoroTTS

# Initialize
tts = KokoroTTS(models_dir="~/models/kokoro")

# Generate speech
audio = tts.synthesize(
    text="Hello, world!",
    voice="af_bella",
    speed=1.0
)

# Save to file
audio.save("output.wav")
```

#### Jupyter Notebook Support
```python
# In a notebook
from kokoro_fastapi.notebook import play_tts

play_tts("Hello from Jupyter!", voice="af_bella")
```

## Implementation Phases

### Phase 1: Package Foundation (Immediate)
- [x] Create `kokoro_fastapi` package structure
- [x] Implement flexible path resolution
- [x] Add `kokoro-start` entry point
- [ ] Update configuration for package mode
- [ ] Add system dependency checking

### Phase 2: Enhanced CLI (Near-term)
- [ ] Add `kokoro-models` command for model management
- [ ] Implement configuration file support
- [ ] Add `--version` and `--help` commands
- [ ] Create user-friendly error messages

### Phase 3: Python API (Medium-term)
- [ ] Design programmatic API
- [ ] Implement synchronous interface
- [ ] Add async interface
- [ ] Create Jupyter notebook utilities

### Phase 4: PyPI Release (Long-term)
- [ ] Coordinate with original author
- [ ] Prepare PyPI package metadata
- [ ] Set up CI/CD for releases
- [ ] Create comprehensive documentation

## Benefits

### For Users
1. **Easier Installation**: Single command installation
2. **Flexibility**: Run anywhere Python runs
3. **Integration**: Use in existing Python projects
4. **Development**: Faster testing and iteration

### For the Project
1. **Wider Adoption**: Lower barrier to entry
2. **Community Growth**: More accessible to Python developers
3. **Use Case Expansion**: Notebooks, scripts, integrations
4. **Maintenance**: Easier testing and CI/CD

## Risks and Mitigations

### Risk: System Dependency Complexity
**Mitigation**: Clear documentation, helpful error messages, graceful degradation

### Risk: Model Distribution Size
**Mitigation**: Separate download step, multiple mirror options, progress indicators

### Risk: Platform Differences
**Mitigation**: Extensive testing, platform-specific instructions, Docker fallback

### Risk: Backward Compatibility
**Mitigation**: All changes are additive, Docker mode remains unchanged

## Success Metrics

1. **Installation Success Rate**: >90% successful first-time installations
2. **Documentation Clarity**: <5 minutes to working TTS output
3. **Performance Parity**: Same inference speed as Docker version
4. **User Adoption**: 100+ package installations in first month

## Conclusion

Making Kokoro-FastAPI available as a Python package will significantly expand its reach and usability while maintaining the robustness of the Docker deployment option. This proposal provides a clear path forward that respects the original design while opening new possibilities for the project's future.

## Next Steps

1. Review and approve this proposal
2. Implement Phase 1 changes
3. Test package installation methods
4. Update documentation
5. Gather user feedback
6. Iterate based on usage patterns