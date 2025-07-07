# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Buzz Lightyear Voice Assistant Client for ESP32-S3/ESP32-C3, implementing voice activity detection (VAD) with automatic recording and playback capabilities. The system continuously monitors for voice activity, records audio when speech is detected, sends it to an API server for processing, and plays back the server's response.

## Build and Development Commands

```bash
# Initial setup (run once)
idf.py set-target esp32s3  # For ESP32-S3
idf.py set-target esp32c3  # For ESP32-C3
idf.py menuconfig  # Configure WiFi credentials and GPIO pins

# Build
idf.py build

# Flash and monitor (replace PORT with your device port, e.g., /dev/ttyUSB0, COM3)
idf.py -p PORT flash monitor

# Clean build
idf.py fullclean

# Run linting (ESP-IDF doesn't have built-in linting)
# Consider using: clang-format -i main/*.c components/*/*.c
```

## Architecture

The codebase follows ESP-IDF component architecture:

- **main/main_client.c**: Core application logic including VAD task, recording task, and API communication
- **components/audio_player/**: Handles I2S configuration, WAV file recording/playback, and SD card operations
  - **stream_buffer.c/h**: Ring buffer implementation for streaming audio data
  - **audio_stream.c/h**: Streaming playback API with concurrent download/playback
- **components/wifi_manager/**: Manages WiFi station mode connection with retry logic

Key architectural decisions:
- Separate I2S channels for microphone (channel 0) and speaker (channel 1) to avoid resource conflicts
- Mutex-based synchronization between VAD and recording tasks
- Task suspension mechanism to prevent VAD interference during active recording
- Fallback from SD card to SPIFFS for audio storage
- **Streaming audio playback**: Implements ring buffer-based streaming to reduce latency by playing audio while downloading

## ESP32-C3 Adaptation Details

1. **PDM to I2S Microphone Conversion**: ESP32-C3 doesn't support PDM, so the code was modified to use standard I2S microphone (INMP441 or similar).

2. **Single I2S Channel**: ESP32-C3 has only I2S_NUM_0, requiring careful resource management between mic and speaker.

3. **GPIO Limitations**: ESP32-C3 has fewer GPIOs (22 vs 45), requiring pin reassignment.

4. **Configuration Management**: WiFi credentials and API server settings moved to Kconfig for easier configuration via `idf.py menuconfig`.

5. **Partition Size**: Using CONFIG_PARTITION_TABLE_SINGLE_APP_LARGE for 1.5MB app partition on 2MB/4MB flash.

## Critical Implementation Details

1. **I2S Resource Management**: The system uses careful mutex locking in audio_player component to prevent conflicts between microphone and speaker operations.

2. **VAD Task Lifecycle**: 
   - VAD task is suspended during recording (main_client.c:420)
   - Must be resumed after recording completes (main_client.c:520)
   - Uses configurable RMS threshold for voice detection

3. **API Communication**: 
   - Server endpoint hardcoded to `192.168.1.24:8080` (main_client.c:145)
   - Implements both recording upload and proactive message checking
   - HTTP multipart form-data for audio upload

4. **Hardware Pin Configuration** (via menuconfig or defaults):
   - ESP32-S3:
     - Microphone I2S (PDM): CLK=6, DATA=4
     - Speaker I2S: BCK=3, WS=2, DOUT=1
     - Status LED: GPIO 7
   - ESP32-C3:
     - Microphone I2S (I2S mode): BCK=7, WS=6, DIN=5
     - Speaker I2S: BCK=10, WS=2, DOUT=1
     - Note: ESP32-C3 has only one I2S peripheral (I2S_NUM_0)
   - SD Card: SPI mode on standard pins

5. **Memory Management**: 
   - Uses SPIRAM for large audio buffers
   - Careful malloc/free for HTTP buffers and audio data
   - Task stack sizes tuned for SPIRAM usage

6. **Streaming Audio Implementation**:
   - **Ring Buffer**: 16KB circular buffer for concurrent HTTP download and audio playback
   - **stream_and_play_audio()**: Replaces download_and_play_audio() for lower latency
   - **WAV Header Parsing**: Dynamic parsing during stream to start playback after 44 bytes
   - **Concurrent Tasks**: Separate tasks for HTTP data reception and I2S playback
   - **Buffer Management**: Semaphore-based synchronization between producer/consumer