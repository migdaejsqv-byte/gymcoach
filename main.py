# -*- coding: utf-8 -*-
"""Gym Coach: личный тренер в зале на базе ИИ (DeepSeek / Gemini)."""
import datetime
import json
import os
import threading

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.utils import platform

Window.softinput_mode = "below_target"

BASE_EXERCISES = """Жим штанги лёжа — грудь
Жим гантелей на наклонной скамье — верх груди
Разводка гантелей лёжа — грудь
Отжимания на брусьях — грудь, трицепс
Подтягивания широким хватом — спина
Тяга верхнего блока к груди — спина
Тяга штанги в наклоне — спина
Тяга гантели одной рукой — спина
Тяга нижнего блока — спина
Приседания со штангой — ноги, ягодицы
Жим ногами — ноги
Румынская тяга — задняя поверхность бедра
Выпады с гантелями — ноги, ягодицы
Разгибание ног в тренажёре — квадрицепс
Сгибание ног в тренажёре — бицепс бедра
Подъём на носки стоя — икры
Жим штанги стоя — плечи
Жим гантелей сидя — плечи
Махи гантелей в стороны — средняя дельта
Тяга к лицу на блоке — задняя дельта
Подъём штанги на бицепс — бицепс
Молотковые сгибания — бицепс, предплечья
Французский жим — трицепс
Разгибание рук на верхнем блоке — трицепс
Планка — пресс, кор
Скручивания на пресс — пресс
Подъём ног в висе — низ пресса
Гиперэкстензия — поясница, ягодицы
Ягодичный мостик со штангой — ягодицы
Становая тяга — спина, ноги
"""

SYSTEM_PROMPT = """Ты личный тренер в тренажёрном зале. У пользователя нет живого тренера, ты его заменяешь.

Правила:
1. Используй ТОЛЬКО упражнения из списка пользователя. Если нужного нет, так и скажи и предложи ближайшее из списка.
2. Если данных мало, сначала задай 2-4 коротких вопроса: что хочет качать сегодня или какая цель, уровень, сколько времени, есть ли травмы. Не задавай вопросы, ответы на которые уже есть в профиле или диалоге.
3. Когда данных достаточно, дай тренировку списком. Для каждого упражнения: подходы x повторения, отдых в секундах, как подобрать рабочий вес (запас 1-3 повторения до отказа) и 1-2 предложения о технике.
4. Начни с короткой разминки, закончи заминкой.
5. Следи за равномерным развитием: смотри историю тренировок и предлагай группы мышц, которые давно не качались. Не ставь одну и ту же группу два дня подряд.
6. Пиши простым текстом на русском. Не используй markdown: без звёздочек, решёток и таблиц.
7. Если у пользователя боль или травма, советуй остановиться и обратиться к врачу.
"""

KV = """
#:import dp kivy.metrics.dp
#:import NoTransition kivy.uix.screenmanager.NoTransition

<Msg>:
    size_hint_y: None
    text_size: self.width - dp(24), None
    height: self.texture_size[1] + dp(24)
    halign: 'left'
    valign: 'middle'
    color: 1, 1, 1, 1
    font_size: '15sp'
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<Btn@Button>:
    background_normal: ''
    background_color: 0.10, 0.42, 0.30, 1
    color: 1, 1, 1, 1
    font_size: '13sp'

<Field@TextInput>:
    background_normal: ''
    background_active: ''
    background_color: 0.13, 0.19, 0.16, 1
    foreground_color: 1, 1, 1, 1
    cursor_color: 0.24, 0.86, 0.52, 1
    hint_text_color: 0.5, 0.6, 0.55, 1
    padding: dp(10), dp(10)
    font_size: '15sp'

<Title@Label>:
    size_hint_y: None
    height: dp(32)
    halign: 'left'
    text_size: self.width, None
    color: 0.24, 0.86, 0.52, 1
    font_size: '14sp'

<Root>:
    orientation: 'vertical'
    padding: dp(6)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 0.06, 0.10, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(46)
        spacing: dp(4)
        Btn:
            text: 'Чат'
            on_release: sm.current = 'chat'
        Btn:
            text: 'Упражнения'
            on_release: sm.current = 'ex'
        Btn:
            text: 'История'
            on_release: app.show_history(); sm.current = 'hist'
        Btn:
            text: 'Настройки'
            on_release: sm.current = 'set'

    ScreenManager:
        id: sm
        transition: NoTransition()

        Screen:
            name: 'chat'
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(6)
                ScrollView:
                    id: scroll
                    do_scroll_x: False
                    BoxLayout:
                        id: chat
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(8)
                        padding: dp(4)
                BoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(4)
                    Btn:
                        text: 'Тренировка на сегодня'
                        on_release: app.quick()
                    Btn:
                        text: 'Записать как сделанную'
                        on_release: app.record()
                    Btn:
                        text: 'Новый чат'
                        on_release: app.new_chat()
                BoxLayout:
                    size_hint_y: None
                    height: dp(64)
                    spacing: dp(4)
                    Field:
                        id: inp
                        hint_text: 'Напишите, что хотите качать'
                        multiline: True
                    Btn:
                        text: 'Отправить'
                        size_hint_x: None
                        width: dp(96)
                        on_release: app.send()

        Screen:
            name: 'ex'
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(6)
                Title:
                    text: 'Ваши упражнения (одно на строку: название — мышцы)'
                Field:
                    id: ex_input
                    hint_text: 'Жим лёжа — грудь'
                BoxLayout:
                    size_hint_y: None
                    height: dp(46)
                    spacing: dp(4)
                    Btn:
                        text: 'Сохранить'
                        on_release: app.save_ex()
                    Btn:
                        text: 'Базовый список'
                        on_release: app.add_base()
                    Btn:
                        text: 'Из файла .txt'
                        on_release: app.pick_file()

        Screen:
            name: 'hist'
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(6)
                ScrollView:
                    do_scroll_x: False
                    BoxLayout:
                        id: hist_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(8)
                        padding: dp(4)
                Btn:
                    text: 'Очистить историю'
                    size_hint_y: None
                    height: dp(46)
                    on_release: app.clear_history()

        Screen:
            name: 'set'
            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)
                    padding: dp(4)
                    Title:
                        text: 'Нейросеть'
                    Spinner:
                        id: prov
                        text: 'DeepSeek'
                        values: ['DeepSeek', 'Gemini']
                        size_hint_y: None
                        height: dp(46)
                        background_normal: ''
                        background_color: 0.10, 0.42, 0.30, 1
                        on_text: app.load_provider(self.text)
                    Title:
                        text: 'API-ключ'
                    Field:
                        id: key
                        password: True
                        multiline: False
                        size_hint_y: None
                        height: dp(46)
                    Title:
                        text: 'Модель'
                    Field:
                        id: model
                        multiline: False
                        size_hint_y: None
                        height: dp(46)
                    Title:
                        text: 'О себе (цель, уровень, травмы, дней в неделю)'
                    Field:
                        id: profile
                        size_hint_y: None
                        height: dp(120)
                    Btn:
                        text: 'Сохранить настройки'
                        size_hint_y: None
                        height: dp(48)
                        on_release: app.save_settings()
                    Label:
                        id: set_msg
                        size_hint_y: None
                        height: dp(30)
                        color: 0.24, 0.86, 0.52, 1
                        font_size: '13sp'
"""

DEFAULTS = {
    "provider": "DeepSeek",
    "keys": {"DeepSeek": "", "Gemini": ""},
    "models": {"DeepSeek": "deepseek-chat", "Gemini": "gemini-2.5-flash"},
    "profile": "",
    "exercises": "",
    "history": [],
}


class Msg(Label):
    bg = ListProperty([0.15, 0.22, 0.18, 1])


class Root(BoxLayout):
    pass


def clean(text):
    """Kivy не рисует markdown, убираем разметку."""
    text = text.replace("**", "").replace("__", "").replace("`", "")
    lines = []
    for ln in text.split("\n"):
        s = ln.lstrip("#").lstrip()
        if s.startswith("* "):
            s = "• " + s[2:]
        lines.append(s)
    return "\n".join(lines).strip()


class GymCoachApp(App):
    title = "Gym Coach"

    # ---------- данные ----------
    def path(self):
        return os.path.join(self.user_data_dir, "data.json")

    def load(self):
        self.data = json.loads(json.dumps(DEFAULTS))
        try:
            with open(self.path(), "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                if isinstance(v, dict) and isinstance(self.data.get(k), dict):
                    self.data[k].update(v)
                else:
                    self.data[k] = v
        except Exception:
            pass

    def store(self):
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
        except Exception as e:
            self.bubble("Не удалось сохранить: %s" % e, "sys")

    # ---------- запуск ----------
    def build(self):
        self.load()
        self.messages = []
        self.busy = False
        Builder.load_string(KV)
        self.root_w = Root()
        return self.root_w

    def on_start(self):
        ids = self.root_w.ids
        ids.prov.text = self.data["provider"]
        self.load_provider(self.data["provider"])
        ids.profile.text = self.data["profile"]
        ids.ex_input.text = self.data["exercises"]
        if platform == "android":
            try:
                from android.permissions import Permission, request_permissions
                request_permissions([Permission.READ_EXTERNAL_STORAGE])
            except Exception:
                pass
        self.bubble("Привет! Я твой тренер. Добавь упражнения на вкладке «Упражнения», "
                    "вставь API-ключ в «Настройках» и нажми «Тренировка на сегодня».", "sys")

    # ---------- чат ----------
    def bubble(self, text, who):
        colors = {"user": [0.10, 0.42, 0.30, 1], "ai": [0.15, 0.22, 0.18, 1], "sys": [0.25, 0.25, 0.20, 1]}
        m = Msg(text=text, bg=colors[who])
        self.root_w.ids.chat.add_widget(m)
        Clock.schedule_once(lambda dt: setattr(self.root_w.ids.scroll, "scroll_y", 0), 0.15)
        return m

    def quick(self):
        self.send("Составь мне тренировку на сегодня. Если нужно, сначала задай вопросы.")

    def new_chat(self):
        if self.busy:
            return
        self.messages = []
        self.root_w.ids.chat.clear_widgets()
        self.bubble("Новый диалог. Что качаем?", "sys")

    def send(self, text=None):
        if self.busy:
            return
        ids = self.root_w.ids
        text = (text or ids.inp.text).strip()
        if not text:
            return
        prov = self.data["provider"]
        if not self.data["keys"].get(prov):
            self.bubble("Сначала вставьте API-ключ %s в «Настройках»." % prov, "sys")
            return
        if not self.data["exercises"].strip():
            self.bubble("Список упражнений пуст. Добавьте его на вкладке «Упражнения».", "sys")
            return
        ids.inp.text = ""
        self.messages.append({"role": "user", "text": text})
        self.bubble(text, "user")
        self.busy = True
        self.wait = self.bubble("Тренер думает…", "sys")
        threading.Thread(target=self.worker, daemon=True).start()

    def system_text(self):
        hist = self.data["history"][-8:]
        hist_txt = "\n".join("%s: %s" % (h["date"], h["text"][:400].replace("\n", " ")) for h in hist)
        return (SYSTEM_PROMPT
                + "\nСегодня: " + datetime.date.today().isoformat()
                + "\n\nУпражнения пользователя:\n" + self.data["exercises"].strip()
                + "\n\nО пользователе: " + (self.data["profile"].strip() or "не указано")
                + "\n\nПоследние тренировки:\n" + (hist_txt or "пока нет"))

    def worker(self):
        try:
            reply = self.ask(self.system_text(), self.messages[-20:])
            Clock.schedule_once(lambda dt: self.done(reply, None))
        except Exception as e:
            err = str(e)
            Clock.schedule_once(lambda dt: self.done(None, err))

    def ask(self, system, msgs):
        prov = self.data["provider"]
        key = self.data["keys"][prov]
        model = self.data["models"][prov]
        if prov == "DeepSeek":
            body = {"model": model, "stream": False,
                    "messages": [{"role": "system", "content": system}] + [
                        {"role": "user" if m["role"] == "user" else "assistant", "content": m["text"]}
                        for m in msgs]}
            r = requests.post("https://api.deepseek.com/chat/completions",
                              headers={"Authorization": "Bearer " + key}, json=body, timeout=120)
            if r.status_code != 200:
                raise RuntimeError("DeepSeek %s: %s" % (r.status_code, r.text[:300]))
            return r.json()["choices"][0]["message"]["content"]
        body = {"system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user" if m["role"] == "user" else "model",
                              "parts": [{"text": m["text"]}]} for m in msgs]}
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
        r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
        if r.status_code != 200:
            raise RuntimeError("Gemini %s: %s" % (r.status_code, r.text[:300]))
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def done(self, reply, err):
        self.busy = False
        self.root_w.ids.chat.remove_widget(self.wait)
        if err:
            self.bubble("Ошибка: " + err, "sys")
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            return
        reply = clean(reply)
        self.messages.append({"role": "ai", "text": reply})
        self.bubble(reply, "ai")

    def record(self):
        last = next((m for m in reversed(self.messages) if m["role"] == "ai"), None)
        if not last:
            self.bubble("Пока нечего записывать: сначала получите план тренировки.", "sys")
            return
        self.data["history"].append({"date": datetime.date.today().isoformat(), "text": last["text"]})
        self.store()
        self.bubble("Тренировка записана в историю. В следующий раз тренер учтёт её.", "sys")

    # ---------- упражнения ----------
    def save_ex(self):
        self.data["exercises"] = self.root_w.ids.ex_input.text.strip()
        self.store()
        n = len([l for l in self.data["exercises"].split("\n") if l.strip()])
        self.bubble("Сохранено упражнений: %d" % n, "sys")

    def add_base(self):
        box = self.root_w.ids.ex_input
        if box.text.strip():
            box.text = box.text.rstrip() + "\n" + BASE_EXERCISES
        else:
            box.text = BASE_EXERCISES

    def pick_file(self):
        start = "/storage/emulated/0" if platform == "android" else os.path.expanduser("~")
        chooser = FileChooserListView(path=start, filters=["*.txt", "*.csv"])
        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=46, spacing=4)
        ok = Button(text="Загрузить")
        cancel = Button(text="Отмена")
        row.add_widget(ok)
        row.add_widget(cancel)
        box.add_widget(row)
        pop = Popup(title="Выберите файл со списком упражнений", content=box, size_hint=(0.95, 0.9))

        def load_it(*_):
            if chooser.selection:
                try:
                    with open(chooser.selection[0], "r", encoding="utf-8") as f:
                        txt = f.read().strip()
                    box_in = self.root_w.ids.ex_input
                    box_in.text = (box_in.text.rstrip() + "\n" + txt).strip()
                except Exception as e:
                    self.bubble("Не удалось прочитать файл: %s" % e, "sys")
            pop.dismiss()

        ok.bind(on_release=load_it)
        cancel.bind(on_release=pop.dismiss)
        pop.open()

    # ---------- история ----------
    def show_history(self):
        box = self.root_w.ids.hist_box
        box.clear_widgets()
        if not self.data["history"]:
            box.add_widget(Msg(text="Записанных тренировок пока нет.", bg=[0.25, 0.25, 0.20, 1]))
            return
        for h in reversed(self.data["history"]):
            box.add_widget(Msg(text=h["date"] + "\n" + h["text"], bg=[0.15, 0.22, 0.18, 1]))

    def clear_history(self):
        self.data["history"] = []
        self.store()
        self.show_history()

    # ---------- настройки ----------
    def load_provider(self, name):
        ids = self.root_w.ids
        ids.key.text = self.data["keys"].get(name, "")
        ids.model.text = self.data["models"].get(name, "")

    def save_settings(self):
        ids = self.root_w.ids
        prov = ids.prov.text
        self.data["provider"] = prov
        self.data["keys"][prov] = ids.key.text.strip()
        self.data["models"][prov] = ids.model.text.strip() or DEFAULTS["models"][prov]
        self.data["profile"] = ids.profile.text.strip()
        self.store()
        ids.set_msg.text = "Сохранено. Активна нейросеть: " + prov


if __name__ == "__main__":
    GymCoachApp().run()
