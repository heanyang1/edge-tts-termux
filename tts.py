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

voices_and_languages = asyncio.run(edge_tts.list_voices())

all_languages = "All languages"
languages = [all_languages] + list(
    sorted(set([voice.get("Locale") for voice in voices_and_languages]))
)
language = languages[0]

choose_voice = "Choose a voice"
voices = [choose_voice] + [voice.get("ShortName") for voice in voices_and_languages]
voice = choose_voice

with tg.Connection() as c:
    a = tg.Activity(c)
    root = tg.LinearLayout(a)
    sv = tg.NestedScrollView(a, root)
    layout = tg.LinearLayout(a, sv)

    title = tg.TextView(a, "Edge TTS", layout)
    title.settextsize(30)
    title.setmargin(5)

    et1 = tg.EditText(a, "Enter text here", layout, inputtype="textMultiLine")
    et2 = tg.EditText(a, "Filename.mp3", layout)

    spinners = tg.LinearLayout(a, layout, vertical=False)
    spinners.setheight(tg.View.WRAP_CONTENT)
    spinners.setlinearlayoutparams(0)

    language_spinner = tg.Spinner(a, spinners)
    language_spinner.setlist(languages)
    voice_spinner = tg.Spinner(a, spinners)
    voice_spinner.setlist(voices)

    option = tg.LinearLayout(a, layout, vertical=False)
    option.setheight(tg.View.WRAP_CONTENT)
    option.setlinearlayoutparams(0)

    tg.TextView(a, "Rate: ", option).settextsize(19)
    rate = tg.EditText(a, "+0%", option)

    tg.TextView(a, "Pitch: ", option).settextsize(19)
    pitch = tg.EditText(a, "+0Hz", option)

    tg.TextView(a, "Volume: ", option).settextsize(19)
    volume = tg.EditText(a, "+0%", option)

    buttons = tg.LinearLayout(a, layout, vertical=False)
    buttons.setheight(tg.View.WRAP_CONTENT)
    buttons.setlinearlayoutparams(0)

    save = tg.Button(a, "save", buttons)
    play = tg.Button(a, "play", buttons)
    exit_ = tg.Button(a, "exit", buttons)

    for ev in c.events():
        if ev.type == tg.Event.destroy and ev.value["finishing"]:
            sys.exit()
        if ev.type == tg.Event.click and ev.value["id"] in [save, play]:
            text = et1.gettext()
            name = et2.gettext()
            if voice == choose_voice:
                c.toast("Please choose a voice")
            elif text == "":
                c.toast("Please enter some text")
            elif name == "":
                c.toast("Please enter output filename")
            else:
                communicate = edge_tts.Communicate(
                    text,
                    voice,
                    rate=rate.gettext(),
                    pitch=pitch.gettext(),
                    volume=volume.gettext(),
                )
                c.toast("Sending request...")
                communicate.save_sync(name)
                if ev.value["id"] == save:
                    a.finish()
                elif ev.value["id"] == play:
                    with subprocess.Popen(["mpv", name]) as process:
                        process.communicate()
                    os.unlink(name)
        if ev.type == tg.Event.itemselected and ev.value["id"] == language_spinner:
            language = ev.value["selected"]
            voices = [choose_voice] + [
                voice.get("ShortName")
                for voice in voices_and_languages
                if language == all_languages or voice.get("Locale") == language
            ]
            voice = choose_voice
            voice_spinner.setlist(voices)
        if ev.type == tg.Event.itemselected and ev.value["id"] == voice_spinner:
            voice = ev.value["selected"]
        if ev.type == tg.Event.click and ev.value["id"] == exit_:
            a.finish()
