# AYNA Windows test rehberi

Bu rehber AYNA'yı bir Windows bilgisayarında sıfırdan kurup gerçek ajanla ayağa kaldırmak ve bugüne kadar yapılan her şeyi adım adım denemek içindir. Haftalık Windows oturumunda bu sırayı izleyin.

[DEMO.md](DEMO.md)'deki Mac demosundan farkı şudur: Mac'te sahte ajan sabit bir yakalamayı gösterir. Windows'ta gerçek ajan (`agent/`) açık pencereleri UI Automation ile o anda okur, kırmızı çerçeveyi gerçek pencerenin üstüne çizer ve kaydedilen ögeler o anki uygulamadan gelir.

Rehber `main` dalına göre yazıldı (2026-11-08). Açık bir PR'ı denerken o PR'ın issue'sundaki kontrolü izleyin. Örneğin #206 için PR #215'teki kontrol geçerlidir.

## Bugün ne var, ne yok

| Çalışıyor (`main`) | Henüz yok |
|---|---|
| Sunucu, Neo4j, oturum açma, kullanıcılar ve API anahtarları | İmleçle öge seçme kısayolu (#22). Ekrandaki kısayol ipucu bu yüzden henüz çalışmaz. |
| Uygulama ve sürüm seçimi | İstemciden test çalıştırma (#44, #40'ı bekliyor). Oynatma şimdilik yalnız ajan testleriyle denenir, bkz. [Bölüm 6](#6-testi-çalıştırma-bugün). |
| Ajanın istemciyle başlayıp durması, çökünce yeniden başlaması (#17) | **Çalıştırmalar**, **Onarımlar**, **Değişiklikler** ekranları ("Yakında") |
| Nesne Gözcüsü: gerçek pencere listesi, canlı yakalama, kırmızı çerçeve, depoya ekleme (#24, #184, #25) | Türkçe komutla test üretme paneli (#78) |
| Depo: arama, yeniden adlandırma, düzenleme, kaldırma (#30) | |
| Kodsuz test editörü (#38), Türkçe ve İngilizce arayüz (#185) | |

**Bilinen sınırlar** (hata olarak bildirmeyin, issue'ları açık):

- Qt uygulamalarında ağaç araması gürültülü. AutomationId noktalı bir yol olduğu için `Login` gibi bir arama neredeyse her ögeyle eşleşir (#204).
- Yüzlerce ögeli gerçek pencerelerde ağaçta kaydırma ve arama akıcı değil (#204).
- Türkçe arayüzde "En çok bekle" `2.5` görünür. Düzeltmesi PR #215'te (#206).
- Depoda adı değiştirilen öge, açık testte eski adıyla kalır. Düzeltmesi PR #215'te (#206).
- Electron penceresinin içi UI Automation'a görünmez. AYNA istemcisi kendini Nesne Gözcüsü'nde göremez.

## 1. Gerekenler (bir kez)

- Windows 10 ya da 11.
- Git.
- Docker Desktop (WSL 2 altyapısıyla). Açık ve çalışır durumda olmalı.
- Node.js 22.12 veya üstü (`node --version`).
- Python 3.11 veya üstü (`python --version`). 3.13 ile denendi.
- İlk kurulum için internet: npm paketleri, Electron, sunucu imajı ve pip paketleri indirilir. Sonraki açılışlar internetsiz çalışır.

Komutlar PowerShell içindir. Hepsi depo kökünden başlar.

## 2. Kurulum (bir kez)

### 2.1 Depo ve `.env`

```powershell
git clone https://github.com/galipdg/AYNA.git
cd AYNA
git switch main
git pull --ff-only
Copy-Item .env.example .env
```

`.env` dosyasını açın ve en az şunları değiştirin:

- `NEO4J_PASSWORD`: en az 8 karakter. Neo4j bu parolayı yalnız veritabanı ilk oluşturulurken alır.
- `AYNA_ADMIN_USERNAME` / `AYNA_ADMIN_PASSWORD`: ilk yönetici hesabı. Parola en az 8 karakter.

**8080 portu dolu mu?** Kontrol edin:

```powershell
netstat -ano | findstr :8080
```

Bir satır çıkarsa (örneğin EnterpriseDB'nin Apache'si `PEMHTTPD-x64`), `.env` içinde `AYNA_SERVER_PORT=8081` yazın. Aşağıdaki adreslerde de 8080 yerine 8081 kullanın. Dolu bir portta sunucu açılmış görünür ama istekler başka programa gider (#208).

### 2.2 Ajan ortamı

İstemci ajanı `agent\.venv` içindeki Python ile başlatır. Bu klasör yoksa PATH'teki `python` kullanılır, ama onda ajan paketleri yoktur.

```powershell
cd agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..
```

### 2.3 Deneme uygulaması ortamı

Deneme uygulaması (`eval/apps/trial/app.py`, PySide6) depo kökündeki `.venv` ile çalışır. Ajanın oynatma testleri de PySide6'yı burada arar.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e "eval[dev]"
```

### 2.4 İstemci

```powershell
cd client
npm ci
cd ..
```

## 3. Otomatik testler

Elle denemeden önce çalıştırın. Hepsi yeşil olmalı. Kırmızı olan varsa çıktısını saklayın.

**Önce deneme uygulamasını kapatın.** Ajan testleri onu kendisi açar ve pencereyi başlığıyla bulur. Aynı başlıkta ikinci bir pencere açıksa yanlış olanı kullanabilir.

| Bölüm | Komut | Beklenen |
|---|---|---|
| İstemci | `cd client; npm run lint; npm run typecheck; npm test; cd ..` | Hata yok, `main`'de 198 test geçer |
| Ajan | `cd agent; .venv\Scripts\python.exe -m pytest; cd ..` | Hepsi geçer. `test_playback_trial_app.py` atlanmamalı (`SKIPPED` değil `PASSED`) |
| Deneme uygulaması | `cd eval; ..\.venv\Scripts\python.exe -m pytest apps/trial/tests -v; cd ..` | Hepsi geçer, `test_uia.py` dahil |

Sunucunun testleri Windows'ta gerekmez, CI'da çalışır (JDK 21 ve Testcontainers ister).

## 4. Ayağa kaldırma

Üç PowerShell penceresi açın.

**Pencere 1: sunucu ve Neo4j**

```powershell
docker compose up -d --build
```

İlk derleme birkaç dakika sürer. Sonra kontrol edin (PowerShell'de `curl` başka bir komuttur, `curl.exe` yazın):

```powershell
curl.exe http://127.0.0.1:8080/api/health
```

**Beklenen:** yanıtta `"db":"UP"` geçer.

**Pencere 2: deneme uygulaması**

```powershell
.venv\Scripts\python.exe eval\apps\trial\app.py
```

**Beklenen:** "AYNA Trial - Login" penceresi açılır. Kullanıcı adı ve parola `admin` ile "Welcome, admin!" yazar.

**Pencere 3: istemci**

```powershell
cd client
npm run dev
```

**Beklenen:** AYNA penceresi açılır. Bu terminalde `[agent]` ile başlayan satırlar görünür. Sorun olursa ilk bakılacak yer burasıdır.

## 5. Adım adım deneme

Her adımda **Beklenen** satırına bakın. Uymayan adımı not edin ve devam edin.

### 5.1 İlk açılış

1. Sunucu adresine `http://127.0.0.1:8080` yazıp **Bağlan** deyin. **Beklenen:** oturum açma ekranı gelir.
2. `.env`'deki yönetici adı ve parolasıyla oturum açın. **Beklenen:** "Bu bilgisayarda hangi uygulamayı test ediyorsunuz?" ekranı gelir.
3. **Yeni uygulama**: Ad `AYNA Trial`, Teknoloji `PySide6` → **Ekle ve seç**. **Beklenen:** ana ekran açılır.
4. Üst çubukta **Test ettiğiniz sürümü ekleyin** → `1.0` → **Ekle**. **Beklenen:** sürüm 1.0 seçili görünür.
5. Üst çubuğa bakın. **Beklenen:** birkaç saniye içinde "Ajan hazır" yazar.

### 5.2 Ajan yönetimi (#17)

1. Ajanın süreç numarasını bulun. Deneme uygulaması da `python.exe` olduğu için komut satırına bakın:

   ```powershell
   Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object CommandLine -match 'ayna_agent.rpc' | Select-Object ProcessId, CommandLine
   ```

2. O süreci durdurun: `Stop-Process -Id <ProcessId> -Force`. **Beklenen:** üst çubuk "Ajan yeniden başlıyor…" der, sonra yine "Ajan hazır".
3. 1–2. adımları kısa aralıklarla üç kez daha tekrarlayın (toplam dört). **Beklenen:** dördüncüde "Ajan çalışmıyor" ve **Yeniden başlat** düğmesi çıkar. Mesajda `INFO` ile başlayan bir günlük satırı olmamalı.
4. **Yeniden başlat**'a basın. **Beklenen:** "Ajan hazır".

### 5.3 Nesne Gözcüsü (#24, #184)

1. Soldan **Nesne Gözcüsü**'nü açın. **Beklenen:** solda açık pencereler listelenir, aralarında "AYNA Trial - Login" vardır.
2. "AYNA Trial - Login"i seçin. **Beklenen:** ortada öge ağacı açılır (14 öge civarı). Üstte "Yakalandı (…): … ms içinde … öge." yazar ve süre bir saniyenin altındadır.
3. Ağaçta **Login** düğmesini seçin. **Beklenen:** sağda "AYNA onu nasıl bulur" ve konum bilgisi çıkar. Deneme penceresinde düğmenin etrafında kırmızı bir çerçeve belirir ve tam düğmeyi sarar.
4. Ok tuşlarıyla ağaçta gezin. **Beklenen:** seçim ve kırmızı çerçeve birlikte ilerler, paneller yerinden oynamaz.
5. **Gelişmiş** bölümünü açın. **Beklenen:** tüm UI Automation özellikleri listelenir. Okunamayanlarda "yakalanmadı" yazar.
6. Ağaçta arayın: `user` → 3 eşleşme, `Remember` → 1, `button` → 4, `zzz` → "eşleşen öge yok". Aramayı silin, ağaç geri gelir.
7. Deneme uygulamasında boş alanlarla **Login**'e basın, sonra AYNA'da **Yeniden yakala** deyin. **Beklenen:** durum etiketinin metni "Username and password are required" olarak görünür.

### 5.4 Depoya ekleme (#25)

Aşağıdaki beş ögenin her birini ağaçta seçin, **Depoya ekle** deyin, adı yazıp **Kaydet**'e basın:

| Öge | Ad |
|---|---|
| Username alanı | `login.userNameInput` |
| Password alanı | `login.passwordInput` |
| Remember me kutusu | `login.rememberMeCheckBox` |
| Login düğmesi | `login.loginButton` |
| Durum etiketi | `login.statusLabel` |

**Beklenen:** her kayıtta "Depoya kaydedildi: …" yazar. Formda "Uygulama değişirse şunları da dener: …" satırında birden çok özellik görünür (örneğin ad, sınıf, tür). "Kayıt yeri: AYNA Trial · Sürüm 1.0" yazar.

### 5.5 Testler: kodsuz editör (#38)

1. Soldan **Testler** → **Yeni test** → ad `Geçerli kullanıcıyla giriş` → oluşturun. **Beklenen:** test adımsız açılır, ş ve ğ doğru görünür.
2. **Adım ekle** ile şu adımları yalnız fareyle kurun:

   | Eylem | Öge | Değer / kontrol | En çok bekle |
   |---|---|---|---|
   | Bekle | `login.userNameInput` | | `10` |
   | Yaz | `login.userNameInput` | `admin` | |
   | Yaz | `login.passwordInput` | `admin` | |
   | Tıkla | `login.rememberMeCheckBox` | | |
   | Kontrol et | `login.rememberMeCheckBox` | İşaretli, eşittir, evet | |
   | Tıkla | `login.loginButton` | | |
   | Kontrol et | `login.statusLabel` | Metin, içerir, `Welcome` | `2,5` |

   **Beklenen:** açılır listeler hücrelerin hizasında açılır, metin kesilmez, sonunda hiçbir satır işaretli değildir.
3. 5. adımdaki kontrol özetine tıklayın. **Beklenen:** küçük bir panel açılır, Esc ile kapanır.
4. 2. satırdaki bir alana tıklayın, sonra Alt+↑, Alt+↑, Alt+↓. **Beklenen:** satır her seferinde taşınır, odak tabloda kalır, pencerenin menü çubuğu odağı almaz.
5. Bir satırı tutamacından sürükleyip başka bir yere bırakın. **Beklenen:** satır bırakılan yere gider, diğer satırların değerleri değişmez.
6. **Adım ekle** deyip yeni satırın ögesini boş bırakın. **Beklenen:** satır hemen işaretlenir, **Kaydet** hangi adımın düzeltilmesi gerektiğini söyler. Satırı silin.
7. **Kaydet**, başka bir teste geçip geri dönün, sonra istemciyi kapatıp `npm run dev` ile yeniden açın. **Beklenen:** test aynen geri gelir.
8. Bir adımı silin, Ctrl+Z ile geri getirin, Ctrl+Y ile yineleyin. **Beklenen:** aynı işi **Geri al** ve **Yinele** düğmeleri de yapar.
9. Bir değeri değiştirip kaydetmeden başka bir teste tıklayın. **Beklenen:** ayrılma uyarısı çıkar. Kalmayı seçerseniz değişiklik kalır, ayrılmayı seçerseniz atılır.

### 5.6 Depo (#30)

1. Soldan **Depo**'yu açın. **Beklenen:** beş öge listelenir, `login.loginButton` "1 test" der.
2. Aramaya `pass` yazın, sonra eşleşmeyen bir kelime yazın. **Beklenen:** liste daralır, ikincisinde eşleşme yok metni çıkar.
3. `login.loginButton` → **Yeniden adlandır** → `login.signInButton`. Sonra **Testler**'de testi açın. **Beklenen:** sunucu adımı yeni adla saklar. Testi yeniden açtığınızda yeni ad görünür. Test zaten açıksa eski adla kalması bilinen bir sınırdır (#206).
4. `login.signInButton`'ı **Kaldır**'mayı deneyin. **Beklenen:** reddedilir ve mesajda `Geçerli kullanıcıyla giriş` yazar.
5. `login.statusLabel` → **Düzenle** → "AYNA onu nasıl bulur" seçimini değiştirip kaydedin. **Beklenen:** kaydedildi mesajı.

### 5.7 Dil (#185)

Üst çubuktaki **TR** menüsünden **English** seçin. **Beklenen:** bütün ekran anında İngilizceye döner, Türkçe etiket kalmaz, düğmeler iki satıra taşmaz. Test verisi (`admin`, test adı) aynı kalır. Türkçeye dönün.

### 5.8 Kullanıcılar

**Kullanıcılar** ekranında bir test kullanıcısı ve bir API anahtarı oluşturun. **Beklenen:** hesap listede görünür. Anahtar yalnız bir kez gösterilir.

### 5.9 Ekran ölçeği

Windows Ayarlar → Ekran → Ölçek %150 yapın. Windows isterse oturumu kapatıp açın. 5.3'ün 3. adımını ve 5.5'in 2. adımını tekrarlayın. **Beklenen:** kırmızı çerçeve hem ögeyi hem pencereyi tam sarar, metinler kesilmez ya da üst üste binmez, sütun sürükleme fareyi izler. Bittiğinde ölçeği eski haline alın.

### 5.10 Kapatma

İstemci penceresini kapatın, sonra:

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object CommandLine -match 'ayna_agent.rpc'
```

**Beklenen:** hiçbir şey yazmaz, yani ajan istemciyle birlikte kapandı. Pencere birkaç saniye içinde kapanmalı, takılmamalı.

## 6. Testi çalıştırma (bugün)

İstemcide **Çalıştır** düğmesi henüz yok (#44). Oynatmanın kendisi `main`'de var: ajan bir testi mantıksal adlarla Click ve Type olarak oynatır (#26). Bunu 3. bölümdeki ajan testleri gösterir:

```powershell
cd agent
.venv\Scripts\python.exe -m pytest tests/test_playback_trial_app.py -v
cd ..
```

**Beklenen:** 5 test geçer. Testler deneme uygulamasını kendileri açıp giriş yaparlar ve sonra kapatırlar. Ekranda yazıldığını ve tıklandığını görürsünüz. Kapsananlar:

- 10 kez art arda giriş;
- boş değerle alan temizleme;
- adı değişmiş bir ögenin yedek özelliklerle bulunması;
- birden çok ögeyle eşleşen bir nesnenin yanlış yere tıklamak yerine hata vermesi.

## 7. Durdurma

```powershell
docker compose stop
```

Verileri silmek için `docker compose down -v` kullanın. Bu Neo4j'yi sıfırlar, bir sonraki açılışta `.env`'deki parolalar yeniden okunur.

## Sorun giderme

| Görülen | Çözüm |
|---|---|
| `docker compose up` hata veriyor | Docker Desktop açık mı? 8080 dolu mu (`netstat -ano \| findstr :8080`)? Doluysa `.env`'de `AYNA_SERVER_PORT` değiştirin. |
| Sunucu açık görünüyor ama istemci bağlanamıyor | Portu başka bir program tutuyor olabilir. `curl.exe http://127.0.0.1:8080/api/health` AYNA yanıtı mı veriyor, bakın. |
| Sunucu `AuthenticationException` ile kapanıyor | Neo4j veritabanı eski bir parolayla oluşturulmuş. `docker compose down -v` ile sıfırlayın (veriler silinir). |
| "Ajan çalışmıyor" hemen çıkıyor | `agent\.venv` var mı? 2.2'yi tekrarlayın. `npm run dev` terminalindeki son `[agent]` satırına bakın. |
| Pencere listesinde deneme uygulaması yok | Uygulama açık mı? **Yenile**'ye basın. |
| Ajan testleri `SKIPPED` diyor | Kök `.venv`'de PySide6 yok. 2.3'ü tekrarlayın. |
| Ajan testleri beklenmedik bir yerde kalıyor | Elle açtığınız deneme uygulamasını kapatın. Testler pencereyi başlığıyla bulduğu için yanlış pencereyi kullanabilir. |
| Boş istemci penceresi | Eski `npm run dev` pencerelerini kapatıp yeniden başlatın. |

## Sonucu bildirme

Her adım için geçti ya da kaldı yazın. Kalan adımlar için şunları ekleyin:

- ekran görüntüsü;
- `npm run dev` terminalindeki ilgili satırlar;
- sunucu sorunuysa `docker compose logs server` çıktısı;
- Windows sürümü ve ekran ölçeği.

Sonucu ilgili issue'ya yorum olarak yazın: ajan #17, Nesne Gözcüsü #184, editör #38, depo #30. Hepsini tek yorumda topluyorsanız #28'e yazın.
