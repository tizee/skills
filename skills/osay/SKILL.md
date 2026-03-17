---
name: osay
description: AI-powered text-to-speech CLI tool. Use for pronunciation queries, reading text aloud, generating audio files, or language practice. Use this skill whenever you need to speak text, pronounce words, convert text to audio, read content aloud, or generate speech files. Triggers on "how to pronounce", "say this", "read aloud", "TTS", "text to speech", "speak", "audio generation", "voice synthesis", or any request involving hearing how something sounds.
---

# osay - AI Text-to-Speech

A CLI tool for AI-powered speech synthesis via OpenAI's gpt-4o-mini-tts API
with automatic fallback to macOS's built-in `say` command.

## Quick Reference

```bash
# Basic usage - speak text (default voice: alloy, default tone: cheerful)
osay "Hello, world!"

# Check pronunciation of unfamiliar words
osay "ephemeral"
osay "Nietzsche"

# With specific voice
osay -v coral "Welcome to the presentation."

# Save as audio file
osay -o output.mp3 "This will be saved to a file."

# Replay last audio
osay -p

# Neutral tone (disable default cheerful instructions)
osay --no-instructions "Objective statement."

# JSON output for agents
osay --json "Hello"
```

## Voices

Default voice is `alloy`. List all with `osay -v '?'`.

| Voice   | Characteristics                    |
|---------|-----------------------------------|
| alloy   | Neutral, balanced (default)       |
| ash     | Soft, gentle                      |
| ballad  | Melodic, smooth                   |
| coral   | Warm, conversational              |
| echo    | Resonant, clear                   |
| fable   | Storytelling, narrative           |
| nova    | Clear, standard                   |
| onyx    | Deeper, formal                    |
| sage    | Calm, wise                        |
| shimmer | Expressive, emotional             |

## Speech Instructions

Default instruction: "Speak in a cheerful and positive tone."

Control tone and delivery style with `--instructions`, or disable defaults with `--no-instructions`:

```bash
osay --instructions "Speak slowly and clearly" "Complex technical content."
osay --instructions "Speak with enthusiasm" "This is amazing news!"
osay --no-instructions "Factual news report."
```

## Input Methods

```bash
# Direct text argument
osay "Hello, world!"

# Read from file
osay -f mytext.txt

# Pipe from stdin
echo "Hello from a pipe" | osay
cat article.txt | osay -v coral
```

## Output Formats

Use `--format` to specify audio format (OpenAI only):

| Format | Use Case                          |
|--------|-----------------------------------|
| mp3    | Default, general purpose          |
| opus   | Efficient storage, streaming      |
| aac    | Apple ecosystem, good compression |
| flac   | Lossless, archival quality        |
| wav    | Lossless, editing                 |
| pcm    | Raw audio, processing             |

```bash
osay -o speech.wav --format wav "High quality audio"
osay -o compressed.opus --format opus "Small file size"
```

## Playback Modes

| Mode            | Trigger                  | Latency | Caches? |
|-----------------|--------------------------|---------|---------|
| Cached playback | default (cache enabled)  | Medium  | Yes     |
| Live streaming  | `--no-cache`             | Lowest  | No      |
| File output     | `-o <file>`              | N/A     | No      |
| Cache hit       | same input, cache exists | Instant | N/A     |

Live streaming uses PCM format via `LocalAudioPlayer` for lowest time-to-first-audio.

## Cache Management

Audio files are cached automatically in `~/.osay/audios/` using content-addressable
SHA-256 hashes of `(text, voice, format, instructions)`.

```bash
# List cached audio with metadata
osay --list-cached

# Replay most recent
osay -p

# Select from cache interactively (requires fzf)
osay --play-cached

# Play specific cached audio by ID
osay --play-cached abc123

# Clean up expired entries
osay --cleanup
```

## Agent UX (JSON Mode)

Pass `--json` for structured output. JSON goes to stdout, status messages to stderr.

| Command                        | JSON stdout                                |
|--------------------------------|--------------------------------------------|
| `osay --json "hello"`          | `{"status":"ok","cache_hit":false,...}`     |
| `osay --json "hello"` (cached) | `{"status":"ok","cache_hit":true,"id":...}` |
| `osay --list-cached --json`    | `{"items":[...]}`                          |
| `osay --show-key --json`       | `{"configured":true,"source":"key.json"}`  |
| `osay --cleanup --json`        | `{"status":"ok","removed":3}`              |
| `osay --setup KEY --json`      | `{"status":"ok","key_file":"..."}`         |
| (error)                        | `{"error":"no_input","message":"..."}`     |

### Exit Codes

| Code | Meaning                            |
|------|------------------------------------|
| 0    | Success                            |
| 1    | General error                      |
| 2    | No text provided / file not found  |
| 3    | API key invalid or missing         |

### Non-Interactive Key Setup

Agents should use `osay --setup sk-... --json` (no TTY required).

## Use Cases

### Pronunciation Queries

```bash
osay "worcestershire"
osay "Dostoevsky"
osay "kubernetes"
```

### Audio Generation

```bash
osay -v onyx -o intro.mp3 "Welcome to the show."
osay -o memo.mp3 "Remember to review the pull request."
```

### Language Learning

```bash
osay --instructions "Speak slowly, pausing between phrases" \
  "Could you repeat that more slowly?"
osay --instructions "Speak at natural native speed" \
  "I'm gonna grab a coffee real quick."
```

See [examples/english/SENTENCES.md](examples/english/SENTENCES.md) for practice sentence collections.

## Configuration

### API Key Management

```bash
osay --setup           # Interactive setup
osay --setup sk-...    # Direct key (agent-friendly)
osay --show-key        # Check key status
osay --remove-key      # Remove stored key
```

Key resolution priority:
1. `OPENAI_API_KEY` environment variable
2. `~/.config/osay/key.json` file

### Environment

- **Config file**: `~/.config/osay/config.json`
- **Key file**: `~/.config/osay/key.json` (0600 permissions)
- **Audio cache**: `~/.osay/audios/`
- **Environment variable**: `OPENAI_API_KEY` (overrides key file)

Falls back to macOS `say` command if no valid OpenAI key is available.
