An [`edge-tts`](https://github.com/rany2/edge-tts) frontend on Android using [Termux:GUI Python bindings](https://github.com/tareksander/termux-gui-python-bindings).

## Features

- All features of `edge-tts` (select voice, rate, pitch and volume)
- Play and save save the generated voice
- Scrape a webpage and read its content

## Install and usage

Install [Termux:GUI](https://github.com/termux/termux-gui) and dependencies:
```sh
pkg install python mpv
pip install edge-tts termuxgui html2text requests
```

Then run `python tts.py` on your Termux session.

GUI usage:
1. Enter the text (or a URL of a webpage) you want to transform into speech and a file name
2. Set a voice (use the spinbox on the left to filter voices with certain language), rate, pitch and volume (the value must be integer)
3. Press `scrape` to scrape the page and load its content
4. Press `request` to send a TTS request and download it as an mp3 audio file
5. Press `play` to play the downloaded audio
6. Uncheck the checkbox if you want to keep the downloaded file

You can change the default configuration by modifying `config.json`.

## License

Apache License 2.0
