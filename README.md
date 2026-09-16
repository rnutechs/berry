# `b"rry`
A system of models built to be an entertainer in the vein of [Neuro-sama](https://vedal.ai/).

## Programs
- [`neuroapi.py`](./neuroapi.py): Implements a websocket server for the [Neuro API](https://github.com/VedalAI/neuro-sdk/tree/main/API) as well as for [Voice Chat](https://github.com/VedalAI/neuro-sdk/blob/main/API/VOICE_CHAT.md).
  - Performs STT and TTS through [Moonshine Voice](https://www.moonshine.ai/).
- [`discordbot.py`](./discordbot.py): Implements a voice client for [`neuroapi.py`](./neuroapi.py) that works through Discord voice channels.