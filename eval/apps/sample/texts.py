"""Every string the sample app shows, in one place (#33).

Two reasons it is a module of its own rather than literals in the widgets:

* **The bug-injected versions (#47)** include a "wrong label" case (SC-21). With the texts
  here that version is a one-line change, and the diff says exactly what the bug is.
* **The NL dataset (#36) and the reference scenarios** quote these strings. When one has to
  change, this file is the only place to look, and `eval/nl/objects/sample.json` can be
  rebuilt from it.

The app's interface is **Turkish** and its identifiers are **English**. The scenarios
already fix the Turkish side (SC-20 types "Ayşe Çelik" and selects "Kalite Güvence", and
requires both to survive unchanged through the agent, the server and the report), the NL
dataset is Turkish, and the product is delivered to a Turkish closed network -- while
`objectName`, which becomes the UIA AutomationId, stays English so a logical name in the
repository reads the same as the code.
"""

from __future__ import annotations

VERSION = "1.0"

APP_NAME = "AYNA Örnek"


def title(screen: str) -> str:
    """A window title: the app, its version and the screen, e.g. `AYNA Örnek 1.0 - Giriş`.

    The version is in every title because #46 and #47 ship changed copies of this app and a
    screenshot or a snapshot has to say which one it came from.
    """
    return f"{APP_NAME} {VERSION} - {screen}"


def with_variant(window_title: str, variant: str) -> str:
    """A title with #46's change version in it: `AYNA Örnek 1.0-v2a - Giriş`.

    `variant_patch.py` rewrites the title rather than the windows passing the version down,
    so the version reaches every window the app opens later without six constructors having
    to carry it. A title with no version in it (the two dialogs) is returned unchanged.
    """
    return window_title.replace(
        f"{APP_NAME} {VERSION}", f"{APP_NAME} {VERSION}-{variant}", 1
    )


# --- login ---------------------------------------------------------------------------------

LOGIN_SCREEN = "Giriş"
LOGIN_HEADING = "Kullanıcı girişi"
LOGIN_USER_NAME = "Kullanıcı adı"
LOGIN_PASSWORD = "Şifre"
LOGIN_SERVER = "Sunucu"
LOGIN_SERVERS = ("Yerel sunucu", "Test sunucusu", "Canlı sunucu")
LOGIN_SHOW_PASSWORD = "Şifreyi göster"
LOGIN_REMEMBER_ME = "Beni hatırla"
LOGIN_BUTTON = "Giriş"
LOGIN_CLEAR = "Temizle"
LOGIN_FORGOT = "Şifremi unuttum"
LOGIN_EXIT = "Çıkış"

LOGIN_WELCOME = "Hoş geldiniz, {user}!"
LOGIN_INVALID = "Kullanıcı adı veya şifre hatalı"
LOGIN_EMPTY = "Kullanıcı adı ve şifre zorunlu"
LOGIN_FORGOT_HINT = "Şifre sıfırlama için sistem yöneticisine başvurun"

# --- list screen ---------------------------------------------------------------------------

MAIN_SCREEN = "Müşteriler"
MAIN_HEADING = "Müşteri listesi"
MAIN_SEARCH = "Müşteri ara"
MAIN_SEARCH_BUTTON = "Ara"
MAIN_CLEAR = "Temizle"
MAIN_CITY = "Şehir"
MAIN_ACTIVE_ONLY = "Sadece etkin kayıtlar"
MAIN_REFRESH = "Yenile"
MAIN_OPEN = "Aç"
MAIN_SETTINGS = "Ayarlar"
MAIN_WIZARD = "Yeni kayıt sihirbazı"
MAIN_COLUMNS = ("Ad", "Soyad", "Şehir", "Durum")

MAIN_SEARCHING = "Aranıyor..."
MAIN_FOUND = "{count} kayıt bulundu"
MAIN_NONE_FOUND = "Kayıt bulunamadı"
MAIN_SELECT_FIRST = "Açmak için bir kayıt seçin"

# --- detail form ---------------------------------------------------------------------------

DETAIL_SCREEN = "Müşteri detayı"
DETAIL_HEADING = "Müşteri bilgileri"
DETAIL_NAME = "Ad Soyad"
DETAIL_EMAIL = "E-posta"
DETAIL_DEPARTMENT = "Departman"
DETAIL_CITY = "Şehir"
DETAIL_NOTES = "Notlar"
DETAIL_ACTIVE = "Etkin"
DETAIL_SAVE = "Kaydet"
DETAIL_RESET = "Sıfırla"
DETAIL_BACK = "Geri"

DETAIL_SAVED = "Kayıt kaydedildi"
DETAIL_NAME_REQUIRED = "Ad alanı zorunlu"
DETAIL_EMAIL_INVALID = "E-posta adresi geçersiz"

DISCARD_TITLE = "Değişiklikleri at?"
DISCARD_QUESTION = "Kaydedilmemiş değişiklikler var. Atmak istiyor musunuz?"

# --- settings ------------------------------------------------------------------------------

SETTINGS_SCREEN = "Ayarlar"
SETTINGS_GENERAL_TAB = "Genel"
SETTINGS_NOTIFICATIONS_TAB = "Bildirimler"
SETTINGS_ADVANCED_TAB = "Gelişmiş"

SETTINGS_THEME = "Tema"
SETTINGS_THEMES = ("Açık", "Koyu", "Sistem")
SETTINGS_LANGUAGE = "Dil"
SETTINGS_LANGUAGES = ("Türkçe", "English")
SETTINGS_STARTUP = "Açılışta başlat"
SETTINGS_TIMEOUT = "Zaman aşımı (sn)"
SETTINGS_FONT_SIZE = "Yazı boyutu"

SETTINGS_EMAIL_NOTIFICATIONS = "E-posta bildirimleri"
SETTINGS_DESKTOP_NOTIFICATIONS = "Masaüstü bildirimleri"
SETTINGS_FREQUENCY = "Sıklık"
SETTINGS_FREQUENCIES = ("Anlık", "Günlük", "Haftalık")
SETTINGS_EMAIL_ADDRESS = "Bildirim adresi"
SETTINGS_QUIET_HOURS = "Sessiz saatler (22:00-07:00)"

SETTINGS_LOG_LEVEL = "Günlük seviyesi"
SETTINGS_LOG_LEVELS = ("Hata", "Uyarı", "Bilgi", "Ayrıntılı")
SETTINGS_CACHE_SIZE = "Önbellek boyutu (MB)"
SETTINGS_PROXY = "Vekil sunucu"
SETTINGS_EXPERIMENTAL = "Deneysel özellikler"
SETTINGS_DEFAULTS = "Varsayılanlara dön"

SETTINGS_SAVE = "Kaydet"
SETTINGS_CLOSE = "Kapat"
SETTINGS_SAVED = "Ayarlar kaydedildi"
SETTINGS_RESET = "Ayarlar varsayılana döndürüldü"

# --- wizard --------------------------------------------------------------------------------

WIZARD_SCREEN = "Yeni kayıt sihirbazı"
WIZARD_STEP = "Adım {current} / {total}"
WIZARD_PAGE_ONE = "Kişi bilgileri"
WIZARD_PAGE_TWO = "Görev bilgileri"
WIZARD_PAGE_THREE = "Özet"

WIZARD_NAME = "Ad Soyad"
WIZARD_EMAIL = "E-posta"
WIZARD_PHONE = "Telefon"
WIZARD_RECORD_TYPE = "Kayıt türü"
WIZARD_RECORD_TYPES = ("Personel", "Taşeron", "Misafir")
WIZARD_REMOTE = "Uzaktan çalışma"
WIZARD_NOTE = "Açıklama"
WIZARD_SEND_EMAIL = "Özeti e-posta ile gönder"
WIZARD_COPY = "Özeti kopyala"
WIZARD_COPIED = "Özet panoya kopyalandı"
WIZARD_DEPARTMENT = "Departman"
WIZARD_ROLE = "Görev"
WIZARD_START_DATE = "Başlangıç tarihi"
WIZARD_CONFIRM = "Bilgileri onaylıyorum"

WIZARD_BACK = "Geri"
WIZARD_NEXT = "İleri"
WIZARD_FINISH = "Bitir"
WIZARD_CANCEL = "İptal"

WIZARD_SUMMARY = "{name} · {department} · {role}"
WIZARD_NAME_REQUIRED = "Ad Soyad alanı zorunlu"
WIZARD_NOT_CONFIRMED = "Bitirmek için bilgileri onaylayın"
WIZARD_CREATED = "Kayıt oluşturuldu: {name}"

CONFIRM_TITLE = "Kaydı oluştur?"
CONFIRM_QUESTION = "Yeni kayıt oluşturulacak. Onaylıyor musunuz?"
DIALOG_YES = "Evet"
DIALOG_NO = "Hayır"
