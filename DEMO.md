# AYNA demo rehberi

Bu rehber, AYNA'nın bugüne kadarki arayüzünü tek komutla açmak ve danışman hocamıza adım adım göstermek içindir. Demo macOS'ta hazırlandı ve denendi.

> Arayüzün bugünkü hali `main` dalındadır (2026-11-08). Windows'ta gerçek aracıyla kurulum ve adım adım deneme için [DEMO-windows.md](DEMO-windows.md) rehberine bakın.

## Tek komutla başlatma

Gerekenler: açık bir Docker Desktop, Node 22.12 veya üstü, Python 3 ve depo kökünde bir `.env` dosyası. `.env` yoksa `.env.example` dosyasını kopyalayıp doldurun.

Depo kökünde `main` dalını güncelleyin:

```bash
git switch main && git pull --ff-only
```

Sonra `client` klasöründe tek komutu çalıştırın:

```bash
cd client && npm run demo
```

Komut sırayla şunları yapar:

1. Docker'ın açık olduğunu kontrol eder.
2. `docker compose up -d --build` ile Neo4j ve sunucuyu başlatır, hazır olmalarını bekler.
3. Örnek veriyi gerçek API üzerinden kurar: eksikleri ekler, iki örnek testi baştaki haline döndürür.
4. İstemciyi sahte aracıyla açar. Sunucu ve uygulama seçili gelir, dil Türkçedir.

Pencere açılınca `.env` dosyasındaki `AYNA_ADMIN_USERNAME` ve `AYNA_ADMIN_PASSWORD` ile oturum açın. Oturum açma ekranı da gösterimin parçası olduğu için otomatik geçilmez.

**Hangi bilgisayardan?** `npm run demo` her zaman sahte aracıyla açılır ve Mac'te baştan sona denendi; Windows'ta denenmedi. Yeni arayüz gerçek aracıyla Windows'ta 2026-11-07'de çalıştırıldı: Nesne Gözcüsü kontrolünde 8 adımın 6'sı (#184), editör kontrolünde 14 adımın 12'si geçti (#38). Gerçek pencere yakalamayı göstermek için Windows'ta [DEMO-windows.md](DEMO-windows.md) rehberini izleyin.

**Toplantıdan önce:**

- Komutu bir kez çalıştırın. İlk derleme birkaç dakika sürebilir; sonraki açılışlar saniyeler içinde hazır olur.
- Başka bir `npm run dev` açıksa kapatın.

Uygulamayı kapatınca Docker çalışmaya devam eder. Durdurmak için:

```bash
docker compose stop
```

### Seçenekler

Seçenekler `--` sonrasına yazılır, örneğin `npm run demo -- --no-build`.

| Seçenek | Ne işe yarar |
|---|---|
| `--no-build` | Sunucu imajını yeniden derlemez. İnternet yoksa işe yarar. |
| `--no-docker` | Docker'a dokunmaz, çalışan sunucuyu kullanır. |
| `--server <adres>` | Başka bir sunucuya bağlanır. Varsayılan `http://127.0.0.1:8080`. |

### Sorun giderme

| Görülen | Çözüm |
|---|---|
| `Docker is not running` | Docker Desktop'ı açıp komutu tekrarlayın. |
| `docker compose up failed` | 8080 portunu kullanan başka bir stack'i durdurun. |
| `the server refused admin` | İlk yönetici yalnızca bir kez oluşturulur. `.env` dosyasına bu veritabanındaki gerçek parolayı yazın. |
| Boş pencere | Eski `npm run dev` pencerelerini kapatıp komutu tekrarlayın. |
| Üst çubukta aracı hazır görünmüyor | `python3 --version` ile Python 3'ü kontrol edin. |

## Gösterim sırası (yaklaşık 10 dakika)

### 1. Oturum açma ve kabuk

Oturum açın. Üst çubukta uygulama, sürüm, aracı durumu, dil ve kullanıcı bulunur. Sol menüde **Çalıştırmalar**, **Onarımlar** ve **Değişiklikler** "Yakında" olarak görünür; bunlar planlanan yerlerdir.

Anlatılacak nokta: Arayüz, TestComplete'ten daha sade ve anlaşılır olacak şekilde baştan tasarlandı. Tasarım dokümanları `docs/ui/` klasöründedir.

### 2. İki dil

Üst çubuktaki **TR** menüsünden **English** seçin, ekran anında değişir. Sonra Türkçeye dönün. Test verisi yazıldığı gibi kalır.

### 3. Nesne Gözcüsü

1. Soldan **AYNA Trial - Login** penceresini seçin. Ortada öğe ağacı açılır: 14 öğe.
2. Ağaçta arama yapın, örneğin `password`.
3. **Login** düğmesini seçin. Sağda AYNA'nın onu nasıl bulacağı ve nerede olduğu görünür. **Gelişmiş** bölümünde tüm UI Automation özellikleri vardır.
4. Ağaçtan **Username** etiketini seçip **Depoya ekle** düğmesine basın. Ad olarak `login.userNameLabel` yazıp kaydedin.

Dürüstçe söylenecek nokta: Mac'te gerçek aracı pencere okuyamadığı için burada sahte aracı çalışıyor. Ağaç, deneme uygulamasının Windows'ta alınmış gerçek yakalamasıdır. Bu yüzden kırmızı vurgu çerçevesi ekranda gerçek bir pencerenin üzerinde değil, sabit bir yerde belirir. Ayrıntı için [Yakalama nasıl çalışıyor](#yakalama-nasıl-çalışıyor) bölümüne bakın.

### 4. Depo

1. **Nesne Deposu** ekranını açın. Öğeler ekrana göre gruplanmış, her birinin kaç testte kullanıldığı yazıyor.
2. `loginButton` öğesini seçin. Hangi testlerin kullandığı, nasıl bulunduğu ve hangi sürümlerde yakalandığı görünür.
3. **Yeniden adlandır** ile adını `login.signInButton` yapın. **Testler** ekranında adımın yeni adla çalışmaya devam ettiğini gösterin.
4. Aynı öğeyi kaldırmayı deneyin. Testlerde kullanıldığı için reddedilir ve testlerin adı yazılır.

### 5. Testler (kodsuz editör)

1. **Geçerli kullanıcıyla giriş** testini açın: 7 adım, hiç JSON yazılmadan kurulmuş.
2. Bir satırı tutamacından sürükleyerek taşıyın ya da Alt+↑ ve Alt+↓ kullanın.
3. 5. adımdaki kontrol özetine tıklayın. Özellik, karşılaştırma ve beklenen değer küçük bir panelde açılır; Esc ile kapanır. Sol test listesini kenarından sürükleyerek daraltırsanız adımlara daha çok yer kalır.
4. **+ Adım ekle** deyin. Yeni satırda öğe seçili olmadığı için satır hemen işaretlenir ve nedeni yazılır. **Kaydet** hangi adımın düzeltilmesi gerektiğini söyler. Bir öğe seçin ya da satırı silin.
5. **Kaydet** deyin, başka bir teste geçip geri dönün. Test aynen geri gelir.
6. Bir adımı silin, sonra ⌘Z (Windows'ta Ctrl+Z) ile geri getirin. ⇧⌘Z ya da Ctrl+Y yineler; aynı işler **Geri al** ve **Yinele** düğmelerinde de var.
7. **+ Yeni test** ile yeni bir test açıp **+ Adım ekle** ile birkaç adım ekleyin.

### 6. Kullanıcılar

**Kullanıcılar** ekranında hesapları, rolleri ve CI için API anahtarlarını gösterin. Sunucu her isteği oturum açmış bir hesapla ilişkilendirir.

## Yakalama nasıl çalışıyor

**Hangi uygulama?** Listedeki **AYNA Trial - Login**, ekibin yazdığı tek ekranlık PySide6 giriş penceresidir: `eval/apps/trial/app.py` (#9). AYNA'nın ilk hedefi olarak kullanılıyor. Ağaçtaki 14 öge, bu pencerenin Hasan'ın Windows bilgisayarında UI Automation ile alınmış yakalamasıdır (`schemas/examples/snapshot/trial-login.json`, #12).

Pencerenin kendisi Mac'te de açılır. Hoca görmek isterse bir kez kurun:

```bash
python3 -m venv /tmp/ayna-trial && /tmp/ayna-trial/bin/pip install PySide6
```

Sonra depo kökünde çalıştırın (kullanıcı adı ve parola `admin`):

```bash
/tmp/ayna-trial/bin/python eval/apps/trial/app.py
```

**Ne statik, ne dinamik?**

| | Bu demo (Mac) | Gerçek kullanım (Windows) |
|---|---|---|
| Pencere listesi | Sahte aracı, sabit dosya (`client/dev/demo/windows.json`) | Gerçek aracı, açık pencerelerin hepsi (`listWindows`) |
| Öğe ağacı | Kayıtlı yakalama | Seçilen pencere o anda okunur (`snapshot`, #12) |
| Konum ve boyut | Yakalamadaki sabit değerler | O anki gerçek değerler |

Dinamik yakalamanın aracı kodu `main` dalında hazır ve Windows'ta çalışıyor: deneme penceresi 28–32 ms'de yakalandı. Yeni Nesne Gözcüsü ekranı gerçek aracıyla Windows'ta 2026-11-07'de denendi (#184): 285 öğeli bir pencere 723 ms'de yakalandı, kırmızı çerçeve %150 ölçekte de öğeyi tam sardı. Eksik olan imleçle öğe seçmedir (#22). Mac'te dinamik yakalama planlanmıyor, çünkü UI Automation bir Windows özelliğidir ve birinci dönem hedefi Windows masaüstüdür.

## Bugüne kadar yapılanlar

Hepsi `main` dalında (2026-11-08):

| Alan | İş |
|---|---|
| Sunucu | Neo4j grafik şeması ve migration'lar (#14), uygulama ve sürüm API'si (#128), test ve adım API'si (#39), hesaplar, roller ve API anahtarları (#60), OpenAPI sözleşmesi (#31), ortak hata biçimi (#158), anlık görüntü içe aktarma (#15), depoya öğe ekleme (#25), depo ekranının API'si (#30), koşu kayıtları ve canlı durum, sunucu tarafı (#44) |
| Aracı | İstemciyle JSON-RPC bağlantısı (#16), öğe tanımı (#11), UI Automation ile pencere yakalama (#12), mantıksal adla Click ve Type oynatma (#26) |
| İstemci | Aracıyı yönetme (#17), Nesne Gözcüsü (#24, #184), arayüz tasarımı ve uygulama kabuğu (#183), Türkçe ve İngilizce arayüz (#185), depo ekranı (#30), kodsuz test editörü (#38), tek komutla demo (#195, #196) |
| Yapay zekâ | Yerel modelle Türkçe komuttan test adımı üreten servis (#71), self-healing puanlayıcısı (#49), yerel model denemesi (#7) |
| Karar ve belgeler | Deneme uygulaması ve pilot uygulama kararı (#21), gereksinim senaryoları ve RS taslağı (#34, #35), SDD bölümleri (#45, #48, #50, #53) |

## Henüz gösterilemeyenler

| Özellik | Durum |
|---|---|
| Testi istemciden çalıştırma | Sunucu tarafı (#44) ve aracının Click/Type oynatması (#26) hazır. İstemci ekranı tüm anahtar kelimeleri oynatan aracıyı (#40) bekliyor. Oynatma bugün aracı testleriyle görülebilir ([DEMO-windows.md](DEMO-windows.md#6-testi-çalıştırma-bugün)). |
| Gerçek Windows penceresi yakalama | Windows'ta gerçek aracıyla çalışıyor ([DEMO-windows.md](DEMO-windows.md)). Bu demo Mac'te olduğu için sahte aracı kullanıyor. |
| İmleçle öğe seçme | Aracı tarafı (#22) bitmedi. Ekrandaki kısayol ipucu bu yüzden henüz çalışmaz. |
| Türkçe komutla test üretme | Servis hazır, editördeki panel (#78) başlamadı. |
| Otomatik onarım, raporlar, değişiklik etkisi | Plandaki sonraki haftalarda. |

## Tekrar prova ederken

`npm run demo` eksik örnek veriyi ekler ve iki örnek testi baştaki haline döndürür. Sizin açtığınız testlere ve öğelere dokunmaz. Provada `login.loginButton` öğesini yeniden adlandırdıysanız, komut bu adla yeni bir öğe ekler; yeniden adlandırdığınız öğe de listede kalır.
