# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Style-Bert-VITS2 is a Python-based Text-to-Speech (TTS) system that extends Bert-VITS2 with enhanced style control capabilities. It allows generation of emotionally expressive speech with controllable voice styles.

## Development Commands

### Setup and Installation
```bash
# Using uv (recommended - faster)
uv venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
uv pip install "torch<2.4" "torchaudio<2.4" --index-url https://download.pytorch.org/whl/cu118
uv pip install -r requirements.txt
python initialize.py

# Using regular pip
pip install -r requirements.txt
python initialize.py
```

### Running the Application
- `python server_editor.py --inbrowser` - Main voice synthesis editor (recommended)
- `python app.py` - Legacy WebUI
- `python server_fastapi.py` - FastAPI server for API access

### Testing
```bash
# Run tests via hatch
hatch run test:test              # Run all tests
hatch run test:coverage          # Run with coverage
hatch run test:cov-report        # Generate coverage report
```

### Code Quality
```bash
# Check and format code via hatch
hatch run style:check    # Check code style
hatch run style:fmt      # Auto-format code (Black + isort + Ruff)
```

## Architecture Overview

### Core Structure
- `/style_bert_vits2/` - Main Python package containing:
  - `/models/` - Model definitions and inference code
  - `/tts_model.py` - Main TTS synthesis interface
  - `/text/` - Text processing and language-specific modules
  - `/nlp/` - NLP preprocessing components
- `/bert/` - BERT configurations and tokenizers for different languages
- `/gradio_tabs/` - Web UI components for different features
- `/model_assets/` - Downloaded pre-trained models location

### Key Patterns
- Language support through modular text processors in `/style_bert_vits2/text/`
- Style control via style vectors embedded in the synthesis pipeline
- Model configuration through YAML files (see `default_config.yml`)
- Windows-friendly batch files for non-technical users

### API Development
- FastAPI server provides REST endpoints at `/voice` with automatic docs at `/docs`
- Supports both file uploads and base64 encoded responses
- CORS and character limits configurable in environment

### Important Considerations
- The project heavily uses PyTorch and CUDA for GPU acceleration
- Model files can be large (several GB) - stored in `/model_assets/`
- Training requires NVIDIA GPU; inference can run on CPU
- Primary user base is Japanese, with strong Windows support