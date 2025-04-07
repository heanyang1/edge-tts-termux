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
from enum import Enum

voices_and_languages = asyncio.run(edge_tts.list_voices())
all_languages = "All languages"
languages = [all_languages] + list(
    sorted(set([voice.get("Locale") for voice in voices_and_languages]))
)
choose_voice = "Choose a voice"
voices = [choose_voice] + [voice.get("ShortName") for voice in voices_and_languages]

socket_in, socket_out = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
mpv = None

class State(Enum):
    START = 0
    DOWNLOADED = 1
    PLAYING = 2
    STOPPED = 3


state = State.START

# Default values
language = all_languages
voice = choose_voice
remove_file = True
text = "Enter text here"
filename = "Filename.mp3"


def request_tts(c, text, name, rate, pitch, volume):
    if voice == choose_voice:
        c.toast("Please choose a voice")
    elif text == "":
        c.toast("Please enter some text")
    elif name == "":
        c.toast("Please enter output filename")
    else:
        c.toast("Sending request...")
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        communicate.save_sync(name)


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

    et1 = tg.EditText(a, text, layout, inputtype="textMultiLine")
    et2 = tg.EditText(a, filename, layout)

    spinners = tg.LinearLayout(a, layout, vertical=False)
    spinners.setheight(tg.View.WRAP_CONTENT)
    spinners.setlinearlayoutparams(0)

    language_spinner = tg.Spinner(a, spinners)
    language_spinner.setlist(languages)
    voice_spinner = tg.Spinner(a, spinners)
    voice_spinner.setlist(voices)

    remove_file_checkbox = tg.Checkbox(a, "Remove file on exit", layout, remove_file)
    remove_file_checkbox.setheight(tg.View.WRAP_CONTENT)
    remove_file_checkbox.setlinearlayoutparams(0)

    option = tg.LinearLayout(a, layout, vertical=False)
    option.setheight(tg.View.WRAP_CONTENT)
    option.setlinearlayoutparams(0)

    tg.TextView(a, "Rate: ", option)
    rate = tg.EditText(a, "+0%", option)

    tg.TextView(a, "Pitch: ", option)
    pitch = tg.EditText(a, "+0Hz", option)

    tg.TextView(a, "Volume: ", option)
    volume = tg.EditText(a, "+0%", option)

    buttons = tg.LinearLayout(a, layout, vertical=False)
    buttons.setheight(tg.View.WRAP_CONTENT)
    buttons.setlinearlayoutparams(0)

    request = tg.Button(a, "request", buttons)
    play = tg.Button(a, "play", buttons)
    exit_ = tg.Button(a, "exit", buttons)

    for ev in c.events():
        if ev.type == tg.Event.destroy and ev.value["finishing"]:
            sys.exit()
        elif ev.type == tg.Event.click and ev.value["id"] == request:
            quit_mpv()
            text = et1.gettext()
            filename = et2.gettext()
            request_tts(
                c, text, filename, rate.gettext(), pitch.gettext(), volume.gettext()
            )
            c.toast("The audio file is ready")
            state = State.DOWNLOADED
        elif ev.type == tg.Event.click and ev.value["id"] == play:
            if state == State.START:
                c.toast("Press 'request' first")
            elif state == State.DOWNLOADED:
                assert mpv is None
                mpv = subprocess.Popen(
                    ["mpv", filename, f"--input-ipc-client=fd://{socket_in.fileno()}"],
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
            language = ev.value["selected"]
            voices = [choose_voice] + [
                voice.get("ShortName")
                for voice in voices_and_languages
                if language == all_languages or voice.get("Locale") == language
            ]
            voice = choose_voice
            voice_spinner.setlist(voices)
        elif ev.type == tg.Event.itemselected and ev.value["id"] == voice_spinner:
            voice = ev.value["selected"]
        elif ev.type == tg.Event.click and ev.value["id"] == remove_file_checkbox:
            remove_file = ev.value["set"]
        elif ev.type == tg.Event.click and ev.value["id"] == exit_:
            break

    quit_mpv()
    if remove_file and os.path.exists(filename):
        os.unlink(filename)
    socket_in.close()
    socket_out.close()
    a.finish()
