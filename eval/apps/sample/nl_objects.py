"""Build `eval/nl/objects/sample.json`, the NL dataset's object list for this app (#36).

    .venv/Scripts/python.exe eval/apps/sample/nl_objects.py --write    # regenerate the file
    .venv/Scripts/python.exe eval/apps/sample/nl_objects.py --check    # exit 1 if it is stale

The file is the list of repository objects a gold step of the NL dataset may target
(`eval/nl/guideline.md`, "Object list"; shape: `eval/nl/objects.schema.json`). It is built
from the app's own widgets on Qt's offscreen platform, so it needs no display and runs on
macOS too, and nothing in it is typed by hand except the Turkish `description` of each
object, which is a tester's wording and cannot be derived.

Why from the widgets and not from `uia_check.py --json`: the dump sees only what is on
screen, and two settings tabs, two wizard pages and both dialogs are not. Building from the
widgets is safe because the two rules it relies on were measured against UI Automation on
2026-11-17 for every object here, tabs, pages and dialogs included, and
`tests/test_nl_objects_uia.py` keeps measuring them:

* the **AutomationId** is `QApplication.` plus the objectName of every widget from the
  top-level window down (a dialog is a top-level window of its own, so
  `QApplication.discardDialog.yesButton`, not under `detail`);
* the **ControlType** follows from the Qt class (`CONTROL_TYPES`); note `QDateEdit` is a
  `Spinner`, not an `Edit`.

What is in the list: every interactive control, every window, and the labels a test reads
(`CHECKED_LABELS`: headings, status lines, the result count, the wizard's step, page and
summary, a dialog's question). A caption label ("Kullanıcı adı" beside its input) is left
out: no scenario checks one, and to the NL assistant it would be a second object with the
input's own words.

The settings **tab items** are listed with a `name`. Qt gives all three the tab bar's
AutomationId (`QApplication.settings.tabs.qt_tabwidget_tabbar`) and tells them apart only by
their UIA Name, so each carries that Name (`TAB_ITEMS`), and `eval/nl/objects.schema.json`
allows a shared AutomationId only when the names differ (galip's call on #259, option a).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

#: Where the object list lives: next to the NL pairs, which is galip's folder (#36).
OUTPUT = HERE.parents[1] / "nl" / "objects" / "sample.json"

#: Qt class name -> UIA ControlType, as measured on 2026-11-17 (PySide6 6.12, Windows 11).
#: Looked up along the class's MRO, so a subclass maps like its Qt base.
CONTROL_TYPES = {
    "QLineEdit": "Edit",
    "QPlainTextEdit": "Edit",
    "QComboBox": "ComboBox",
    "QCheckBox": "CheckBox",
    "QPushButton": "Button",
    "QSpinBox": "Spinner",
    "QDateEdit": "Spinner",
    "QTableWidget": "Table",
    "QLabel": "Text",
}

#: The labels a step may check. Every other QLabel is a caption beside an input.
CHECKED_LABELS = {
    "headingLabel",
    "statusLabel",
    "resultCountLabel",
    "stepLabel",
    "pageLabel",
    "summaryLabel",
    "questionLabel",
}

#: The tab items, which share the tab bar's AutomationId: logical name -> UIA Name (measured).
TAB_ITEMS = {
    "settings.generalTab": "Genel",
    "settings.notificationsTab": "Bildirimler",
    "settings.advancedTab": "Gelişmiş",
}

#: The Turkish description of every object, as a tester would name the control. The UI is
#: Turkish, so there is no English text in parentheses (guideline: only for an English UI).
#: Neutral wording, never a phrase from a pair's text.
DESCRIPTIONS = {
    # login
    "login.window": "Giriş penceresi",
    "login.headingLabel": "Giriş ekranının başlığı",
    "login.userNameInput": "Kullanıcı adı alanı",
    "login.passwordInput": "Şifre alanı",
    "login.serverCombo": "Bağlanılacak sunucu seçimi",
    "login.showPasswordCheck": "Şifreyi göster onay kutusu",
    "login.rememberMeCheck": "Beni hatırla onay kutusu",
    "login.loginButton": "Giriş butonu",
    "login.clearButton": "Giriş formunu temizleme butonu",
    "login.exitButton": "Uygulamadan çıkış butonu",
    "login.forgotPasswordLink": "Şifremi unuttum bağlantısı",
    "login.statusLabel": "Giriş sonucunu gösteren durum etiketi",
    # main
    "main.window": "Müşteri listesi penceresi",
    "main.headingLabel": "Müşteri listesi ekranının başlığı",
    "main.searchInput": "Müşteri arama alanı",
    "main.searchButton": "Arama butonu",
    "main.clearButton": "Aramayı temizleme butonu",
    "main.cityFilterCombo": "Şehre göre filtre seçimi",
    "main.activeOnlyCheck": "Yalnızca etkin kayıtları gösterme onay kutusu",
    "main.refreshButton": "Listeyi yenileme butonu",
    "main.customerGrid": "Müşterileri listeleyen tablo",
    "main.resultCountLabel": "Bulunan kayıt sayısını gösteren etiket",
    "main.openButton": "Seçili müşteriyi açma butonu",
    "main.settingsButton": "Ayarlar ekranını açan buton",
    "main.wizardButton": "Yeni kayıt sihirbazını açan buton",
    # detail
    "detail.window": "Müşteri detayı penceresi",
    "detail.headingLabel": "Müşteri detayı ekranının başlığı",
    "detail.nameInput": "Müşterinin ad soyad alanı",
    "detail.emailInput": "Müşterinin e-posta alanı",
    "detail.departmentCombo": "Müşterinin departman seçimi",
    "detail.cityCombo": "Müşterinin şehir seçimi",
    "detail.notesInput": "Müşteriyle ilgili notlar alanı",
    "detail.activeCheck": "Müşterinin etkin olduğunu belirten onay kutusu",
    "detail.saveButton": "Müşteri bilgilerini kaydetme butonu",
    "detail.resetButton": "Formu kayıtlı değerlere döndürme butonu",
    "detail.backButton": "Müşteri listesine geri dönme butonu",
    "detail.statusLabel": "Kaydetme sonucunu ve hataları gösteren durum etiketi",
    # settings
    "settings.window": "Ayarlar penceresi",
    "settings.generalTab": "Genel sekmesi",
    "settings.notificationsTab": "Bildirimler sekmesi",
    "settings.advancedTab": "Gelişmiş sekmesi",
    "settings.themeCombo": "Tema seçimi (Genel sekmesi)",
    "settings.languageCombo": "Dil seçimi (Genel sekmesi)",
    "settings.timeoutSpin": "Saniye cinsinden zaman aşımı değeri (Genel sekmesi)",
    "settings.fontSizeSpin": "Yazı boyutu değeri (Genel sekmesi)",
    "settings.startupCheck": "Açılışta başlatma onay kutusu (Genel sekmesi)",
    "settings.emailNotificationsCheck": "E-posta bildirimleri onay kutusu (Bildirimler sekmesi)",
    "settings.desktopNotificationsCheck": (
        "Masaüstü bildirimleri onay kutusu (Bildirimler sekmesi)"
    ),
    "settings.quietHoursCheck": "Sessiz saatler onay kutusu (Bildirimler sekmesi)",
    "settings.frequencyCombo": "Bildirim sıklığı seçimi (Bildirimler sekmesi)",
    "settings.emailAddressInput": "Bildirimlerin gideceği e-posta adresi alanı (Bildirimler sekmesi)",
    "settings.logLevelCombo": "Günlük kayıt seviyesi seçimi (Gelişmiş sekmesi)",
    "settings.proxyInput": "Vekil sunucu adresi alanı (Gelişmiş sekmesi)",
    "settings.cacheSizeSpin": "MB cinsinden önbellek boyutu değeri (Gelişmiş sekmesi)",
    "settings.experimentalCheck": "Deneysel özellikler onay kutusu (Gelişmiş sekmesi)",
    "settings.defaultsButton": "Ayarları varsayılanlara döndürme butonu (Gelişmiş sekmesi)",
    "settings.saveButton": "Ayarları kaydetme butonu",
    "settings.closeButton": "Ayarlar penceresini kapatma butonu",
    "settings.statusLabel": "Ayarların kaydedilip kaydedilmediğini gösteren durum etiketi",
    # wizard
    "wizard.window": "Yeni kayıt sihirbazı penceresi",
    "wizard.stepLabel": "Sihirbazın kaçıncı adımda olduğunu gösteren etiket",
    "wizard.pageLabel": "Sihirbazın o anki sayfasının başlığı",
    "wizard.nameInput": "Yeni kaydın ad soyad alanı (1. adım)",
    "wizard.emailInput": "Yeni kaydın e-posta alanı (1. adım)",
    "wizard.phoneInput": "Yeni kaydın telefon alanı (1. adım)",
    "wizard.recordTypeCombo": "Kayıt türü seçimi (1. adım)",
    "wizard.departmentCombo": "Yeni kaydın departman seçimi (2. adım)",
    "wizard.roleCombo": "Yeni kaydın görev seçimi (2. adım)",
    "wizard.startDateEdit": "İşe başlangıç tarihi (2. adım)",
    "wizard.remoteCheck": "Uzaktan çalışma onay kutusu (2. adım)",
    "wizard.noteInput": "Kayıtla ilgili açıklama alanı (3. adım)",
    "wizard.summaryLabel": "Girilen bilgilerin özetini gösteren etiket (3. adım)",
    "wizard.confirmCheck": "Bilgileri onaylama onay kutusu (3. adım)",
    "wizard.sendEmailCheck": "Özeti e-posta ile gönderme onay kutusu (3. adım)",
    "wizard.copyButton": "Özeti panoya kopyalama butonu (3. adım)",
    "wizard.backButton": "Sihirbazda önceki adıma dönme butonu",
    "wizard.nextButton": "Sihirbazda sonraki adıma geçme butonu",
    "wizard.finishButton": "Sihirbazı bitirip kaydı oluşturma butonu",
    "wizard.cancelButton": "Sihirbazı iptal etme butonu",
    "wizard.statusLabel": "Sihirbazın uyarı ve sonuçlarını gösteren durum etiketi",
    # the two dialogs
    "discardDialog.window": "Kaydedilmemiş değişiklikleri atma onayı penceresi",
    "discardDialog.questionLabel": "Değişiklikleri atma onayında sorulan soru",
    "discardDialog.yesButton": "Değişiklikleri atmayı onaylayan Evet butonu",
    "discardDialog.noButton": "Değişiklikleri atmaktan vazgeçen Hayır butonu",
    "confirmDialog.window": "Yeni kaydı oluşturma onayı penceresi",
    "confirmDialog.questionLabel": "Kayıt oluşturma onayında sorulan soru",
    "confirmDialog.yesButton": "Kaydı oluşturmayı onaylayan Evet butonu",
    "confirmDialog.noButton": "Kaydı oluşturmaktan vazgeçen Hayır butonu",
}


def _top_levels():
    """Every top-level window of the app: the five screens, then the two dialogs.

    The dialogs are built with the same arguments `windows.py` gives them, so their ids and
    texts are the app's. They need a QApplication, which the caller provides.
    """
    import texts as t
    import windows

    return [
        windows.LoginWindow(),
        windows.MainWindow(),
        windows.DetailWindow(),
        windows.SettingsWindow(),
        windows.WizardWindow(),
        windows.QuestionDialog("discardDialog", t.DISCARD_TITLE, t.DISCARD_QUESTION),
        windows.QuestionDialog("confirmDialog", t.CONFIRM_TITLE, t.CONFIRM_QUESTION),
    ]


def automation_id(widget) -> str:
    """`QApplication.` and the objectNames from the top-level window down to `widget`."""
    names = []
    while widget is not None:
        names.append(widget.objectName())
        if widget.isWindow():
            break
        widget = widget.parentWidget()
    return ".".join(["QApplication", *reversed(names)])


def control_type(widget) -> str | None:
    for cls in type(widget).__mro__:
        if cls.__name__ in CONTROL_TYPES:
            return CONTROL_TYPES[cls.__name__]
    return None


def _listed(widget) -> bool:
    name = widget.objectName()
    if not name or name.startswith("qt_"):
        return False
    kind = control_type(widget)
    if kind is None:
        return False  # containers: tab pages, the tab widget, layouts' helpers
    if kind == "Text":
        return name in CHECKED_LABELS
    return True


def collect(windows_) -> dict[str, dict]:
    """Logical name -> object, without descriptions, in window and creation order."""
    from PySide6.QtWidgets import QComboBox, QWidget

    objects: dict[str, dict] = {}
    for window in windows_:
        screen = window.objectName()
        objects[f"{screen}.window"] = {
            "automationId": automation_id(window),
            "controlType": "Window",
        }
        for widget in window.findChildren(QWidget):
            if not _listed(widget):
                continue
            name = f"{screen}.{widget.objectName()}"
            if name in objects:
                raise ValueError(f"two widgets would both be {name}")
            entry = {
                "automationId": automation_id(widget),
                "controlType": control_type(widget),
            }
            if isinstance(widget, QComboBox):
                entry["items"] = [widget.itemText(i) for i in range(widget.count())]
            objects[name] = entry
    return objects


def tab_items(windows_) -> dict[str, dict]:
    """`TAB_ITEMS` with the tab bar's AutomationId, checked against the tab texts.

    A tab item is not a widget, so `collect` cannot see it; its id is the bar's, and only its
    Name (the tab text) tells the three apart.
    """
    from PySide6.QtWidgets import QTabWidget

    found: dict[str, dict] = {}
    for window in windows_:
        for tabs in window.findChildren(QTabWidget):
            texts = {tabs.tabText(i) for i in range(tabs.count())}
            for name, text in TAB_ITEMS.items():
                if name.split(".")[0] == window.objectName() and text in texts:
                    found[name] = {
                        "automationId": automation_id(tabs.tabBar()),
                        "controlType": "TabItem",
                        "name": text,
                    }
    missing = sorted(set(TAB_ITEMS) - set(found))
    if missing:
        raise ValueError(f"tab items not in the app: {missing}")
    return found


def build() -> dict:
    """The whole object list, descriptions included. Needs a QApplication."""
    import texts as t

    windows_ = _top_levels()
    found = collect(windows_)
    # The tab items go right after their window, where a reader looks for them.
    tabs = tab_items(windows_)
    ordered: dict[str, dict] = {}
    for name, entry in found.items():
        ordered[name] = entry
        if name.endswith(".window"):
            screen = name.split(".")[0]
            ordered.update(
                {n: e for n, e in tabs.items() if n.startswith(f"{screen}.")}
            )
    found = ordered
    missing = sorted(set(found) - set(DESCRIPTIONS))
    extra = sorted(set(DESCRIPTIONS) - set(found))
    if missing or extra:
        raise ValueError(f"descriptions missing for {missing}, for no object: {extra}")
    objects = {}
    for name, entry in found.items():
        obj = {
            "automationId": entry["automationId"],
            "controlType": entry["controlType"],
        }
        if "name" in entry:
            obj["name"] = entry["name"]
        obj["description"] = DESCRIPTIONS[name]
        if "items" in entry:
            obj["items"] = entry["items"]
        objects[name] = obj
    return {
        "app": "sample",
        "appVersion": t.VERSION,
        "source": (
            "eval/apps/sample (#33), generated by eval/apps/sample/nl_objects.py from the "
            "app's widgets; AutomationIds and control types checked against UI Automation "
            "by eval/apps/sample/tests/test_nl_objects_uia.py. The three settings tab items "
            "share the tab bar's AutomationId and are told apart by their UIA Name (name)."
        ),
        "objects": objects,
    }


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def offscreen_app():
    """A QApplication on Qt's offscreen platform, chosen in argv (not QT_QPA_PLATFORM)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(
        ["nl_objects", "-platform", "offscreen"]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help=f"write {OUTPUT.name}")
    group.add_argument("--check", action="store_true", help="exit 1 if it is stale")
    args = parser.parse_args(argv)

    _app = offscreen_app()
    text = render(build())
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT} ({len(json.loads(text)['objects'])} objects)")
        return 0
    current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if current != text:
        print(f"{OUTPUT} is stale: run nl_objects.py --write")
        return 1
    print(f"{OUTPUT} is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
