"""
Copyright 2025 heanyang1

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import termuxgui as tg
import sys
import edge_tts
import asyncio
import subprocess
import json
import socket
import requests
import html2text
from enum import Enum


class Languages:
    def __init__(self, config):
        self.voices_and_languages = asyncio.run(edge_tts.list_voices())
        self.all_languages = "All languages"
        self.choose_voice = "Choose voice"
        self.language = config["language"]
        self.voice = config["voice"]
        assert self.language in self.get_languages()
        assert self.voice in self.get_voices()

    def get_languages(self):
        return [self.all_languages] + list(
            sorted(set([voice.get("Locale") for voice in self.voices_and_languages]))
        )

    def get_voices(self):
        return [self.choose_voice] + [
            voice.get("ShortName")
            for voice in self.voices_and_languages
            if self.language == self.all_languages
            or self.language == voice.get("Locale")
        ]

    def set_language(self, language):
        self.language = language
        self.voice = self.choose_voice

    def set_voice(self, voice):
        assert voice in self.get_voices()
        self.voice = voice

    def use_voice(self, c):
        if self.voice == self.choose_voice:
            c.toast("Please choose a voice")
            return None
        return self.voice

    def get_voice_idx(self):
        return self.get_voices().index(self.voice)

    def get_language_idx(self):
        return self.get_languages().index(self.language)


def prefix(value, name, c):
    if not value.isdigit():
        c.toast(f'"{name}" is not a number')
        return None
    return ("+" if eval(value) >= 0 else "") + value


class State(Enum):
    START = 0
    DOWNLOADED = 1
    PLAYING = 2
    STOPPED = 3


state = State.START

socket_in, socket_out = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
mpv = None

with open("config.json", "r") as f:
    config = json.loads(f.read())

def scrape_webpage(c, url):
    try:
        r = requests.get(url)
        r.raise_for_status()
    except Exception as e:
        c.toast(f"Failed to fetch page: {e}")
        return None
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.ignore_emphasis = True
    h.ignore_links = True
    return h.handle(r.text)

def request_tts(c, text, name, rate, pitch, volume, languages):
    global state
    if text == "":
        c.toast("Please enter some text")
    elif name == "":
        c.toast("Please enter output filename")
    else:
        voice = languages.use_voice(c)
        rate_str = prefix(rate, "rate", c)
        pitch_str = prefix(pitch, "pitch", c)
        volume_str = prefix(volume, "volume", c)
        if None in [rate_str, pitch_str, volume_str]:
            return
        c.toast("Sending request...")
        communicate = edge_tts.Communicate(
            text,
            voice=voice,
            rate=f"{rate_str}%",
            pitch=f"{pitch_str}Hz",
            volume=f"{volume_str}%",
        )
        communicate.save_sync(name)
        c.toast("The audio file is ready")
        state = State.DOWNLOADED


def send_command(s: socket.socket, command: list):
    s.sendall((json.dumps({"command": command}) + "\n").encode())
    # mpv returns a response after the command is executed
    # we receive the response and discard it to make sure the command was executed
    s.recv(1024)


def quit_mpv():
    global mpv
    if state in [State.PLAYING, State.STOPPED]:
        assert mpv is not None
        mpv.terminate()
        mpv = None


with tg.Connection() as c:
    a = tg.Activity(c)
    root = tg.LinearLayout(a)
    sv = tg.NestedScrollView(a, root)
    layout = tg.LinearLayout(a, sv)

    title = tg.TextView(a, "Edge TTS", layout)
    title.settextsize(30)
    title.setmargin(5)

    et1 = tg.EditText(a, config["text"], layout, inputtype="textMultiLine")
    et2 = tg.EditText(a, config["filename"], layout)

    spinners = tg.LinearLayout(a, layout, vertical=False)
    spinners.setheight(tg.View.WRAP_CONTENT)
    spinners.setlinearlayoutparams(0)

    language_spinner = tg.Spinner(a, spinners)
    voice_spinner = tg.Spinner(a, spinners)

    languages = Languages(config)
    language_spinner.setlist(languages.get_languages())
    language_spinner.selectitem(languages.get_language_idx())
    voice_spinner.setlist(languages.get_voices())
    voice_spinner.selectitem(languages.get_voice_idx())

    remove_file_checkbox = tg.Checkbox(
        a, "Remove file on exit", layout, config["remove_file"]
    )
    remove_file_checkbox.setheight(tg.View.WRAP_CONTENT)
    remove_file_checkbox.setlinearlayoutparams(0)

    option = tg.LinearLayout(a, layout, vertical=False)
    option.setheight(tg.View.WRAP_CONTENT)
    option.setlinearlayoutparams(0)

    tg.TextView(a, "Rate: ", option)
    rate_et = tg.EditText(a, config["rate"], option)
    tg.TextView(a, "%", option)

    tg.TextView(a, "Pitch: ", option)
    pitch_et = tg.EditText(a, config["pitch"], option)
    tg.TextView(a, "Hz", option)

    tg.TextView(a, "Volume: ", option)
    volume_et = tg.EditText(a, config["volume"], option)
    tg.TextView(a, "%", option)

    buttons = tg.LinearLayout(a, layout, vertical=False)
    buttons.setheight(tg.View.WRAP_CONTENT)
    buttons.setlinearlayoutparams(0)

    scrape = tg.Button(a, "scrape", buttons)
    request = tg.Button(a, "request", buttons)
    play = tg.Button(a, "play", buttons)
    exit_ = tg.Button(a, "exit", buttons)

    for ev in c.events():
        if ev.type == tg.Event.destroy and ev.value["finishing"]:
            sys.exit()
        elif ev.type == tg.Event.click and ev.value["id"] == scrape:
            scrape_text = scrape_webpage(et1.gettext())
            if scrape_text is not None:
                et1.settext(scrape_text)
        elif ev.type == tg.Event.click and ev.value["id"] == request:
            quit_mpv()
            request_tts(
                c,
                et1.gettext(),
                et2.gettext(),
                rate_et.gettext(),
                pitch_et.gettext(),
                volume_et.gettext(),
                languages,
            )
            play.settext("play")
        elif ev.type == tg.Event.click and ev.value["id"] == play:
            if state == State.START:
                c.toast('Press "request" first')
            elif state == State.DOWNLOADED:
                assert mpv is None
                mpv = subprocess.Popen(
                    [
                        "mpv",
                        et2.gettext(),
                        "--loop-playlist",
                        f"--input-ipc-client=fd://{socket_in.fileno()}",
                    ],
                    pass_fds=[socket_in.fileno()],
                )
                play.settext("pause")
                state = State.PLAYING
            elif state == State.PLAYING:
                send_command(socket_out, ["keypress", "p"])
                play.settext("play")
                state = State.STOPPED
            elif state == State.STOPPED:
                send_command(socket_out, ["keypress", "p"])
                play.settext("pause")
                state = State.PLAYING
        elif ev.type == tg.Event.itemselected and ev.value["id"] == language_spinner:
            languages.set_language(ev.value["selected"])
            voice_spinner.setlist(languages.get_voices())
            voice_spinner.selectitem(languages.get_voice_idx())
        elif ev.type == tg.Event.itemselected and ev.value["id"] == voice_spinner:
            languages.set_voice(ev.value["selected"])
            voice_spinner.selectitem(languages.get_voice_idx())
        elif ev.type == tg.Event.click and ev.value["id"] == remove_file_checkbox:
            config["remove_file"] = ev.value["set"]
        elif ev.type == tg.Event.click and ev.value["id"] == exit_:
            break

    quit_mpv()
    if config["remove_file"] and os.path.exists(et2.gettext()):
        # TODO: users may create files with different names; need to remove all of them
        os.unlink(et2.gettext())
    socket_in.close()
    socket_out.close()
    a.finish()
