# AYNA demo rehberi

Bu rehber, AYNA'nın bugüne kadarki arayüzünü tek komutla açmak ve danışman hocamıza adım adım göstermek içindir. Demo macOS'ta hazırlandı ve denendi.

> **Önemli:** Arayüzün son hali henüz `main` dalında değil, inceleme bekleyen PR'larda. Demo bu yüzden `omer/195-advisor-demo` dalından çalışır.

## Tek komutla başlatma

Gerekenler: açık bir Docker Desktop, Node 22.12 veya üstü, Python 3 ve depo kökünde bir `.env` dosyası. `.env` yoksa `.env.example` dosyasını kopyalayıp doldurun.

Depo kökünde dala geçin:

```bash
git switch omer/195-advisor-demo
```

Sonra `client` klasöründe tek komutu çalıştırın:

```bash
cd client && npm run demo
```

Komut sırayla şunları yapar:

1. Docker'ın açık olduğunu kontrol eder.
2. `docker compose up -d --build` ile Neo4j ve sunucuyu başlatır, hazır olmalarını bekler.
3. Örnek veriyi gerçek API üzerinden kurar. Var olan veriye dokunmaz, yalnızca eksikleri ekler.
4. İstemciyi sahte ajanla açar. Sunucu ve uygulama seçili gelir, dil Türkçedir.

Pencere açılınca `.env` dosyasındaki `AYNA_ADMIN_USERNAME` ve `AYNA_ADMIN_PASSWORD` ile oturum açın. Oturum açma ekranı da gösterimin parçası olduğu için otomatik geçilmez.

**Toplantıdan önce:**

- Komutu bir kez çalıştırın. İlk derleme birkaç dakika sürebilir; sonraki açılışlar saniyeler içinde hazır olur.
- Pencereyi tam ekran yapın. Test tablosu dar pencerede yana kayar.
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
| Üst çubukta ajan hazır görünmüyor | `python3 --version` ile Python 3'ü kontrol edin. |

## Gösterim sırası (yaklaşık 10 dakika)

### 1. Oturum açma ve kabuk

Oturum açın. Üst çubukta uygulama, sürüm, ajan durumu, dil ve kullanıcı bulunur. Sol menüde **Çalıştırmalar**, **Onarımlar** ve **Değişiklikler** "Yakında" olarak görünür; bunlar planlanan yerlerdir.

Anlatılacak nokta: Arayüz, TestComplete'ten daha sade ve anlaşılır olacak şekilde baştan tasarlandı. Tasarım dokümanları `docs/ui/` klasöründedir.

### 2. İki dil

Üst çubuktaki **TR** menüsünden **English** seçin, ekran anında değişir. Sonra Türkçeye dönün. Test verisi yazıldığı gibi kalır.

### 3. Nesne Gözcüsü

1. Soldan **AYNA Trial - Login** penceresini seçin. Ortada öge ağacı açılır: 14 öge.
2. Ağaçta arama yapın, örneğin `password`.
3. **Login** düğmesini seçin. Sağda AYNA'nın onu nasıl bulacağı ve nerede olduğu görünür. **Gelişmiş** bölümünde tüm UI Automation özellikleri vardır.
4. Ağaçtan **Username** etiketini seçip **Depoya ekle** düğmesine basın. Ad olarak `login.userNameLabel` yazıp kaydedin.

Dürüstçe söylenecek nokta: Mac'te gerçek ajan pencere okuyamadığı için burada sahte ajan çalışıyor. Ağaç, deneme uygulamasının Windows'ta alınmış gerçek yakalamasıdır. Bu yüzden kırmızı vurgu çerçevesi ekranda gerçek bir pencerenin üzerinde değil, sabit bir yerde belirir.

### 4. Depo

1. **Depo** ekranını açın. Ögeler ekrana göre gruplanmış, her birinin kaç testte kullanıldığı yazıyor.
2. `loginButton` ögesini seçin. Hangi testlerin kullandığı, nasıl bulunduğu ve hangi sürümlerde görüldüğü görünür.
3. **Yeniden adlandır** ile adını `login.signInButton` yapın. **Testler** ekranında adımın yeni adla çalışmaya devam ettiğini gösterin.
4. Aynı ögeyi kaldırmayı deneyin. Testlerde kullanıldığı için reddedilir ve testlerin adı yazılır.

### 5. Testler (kodsuz editör)

1. **Geçerli kullanıcıyla giriş** testini açın: 7 adım, hiç JSON yazılmadan kurulmuş.
2. Bir satırı tutamacından sürükleyerek taşıyın ya da Alt+↑ ve Alt+↓ kullanın.
3. **+ Adım ekle** deyin. Yeni satırda öge seçili olmadığı için satır hemen işaretlenir ve nedeni yazılır. **Kaydet** hangi adımın düzeltilmesi gerektiğini söyler. Bir öge seçin ya da satırı silin.
4. **Kaydet** deyin, başka bir teste geçip geri dönün. Test aynen geri gelir.
5. **+ Yeni test** ile yeni bir test açıp **+ Adım ekle** ile birkaç adım ekleyin.

### 6. Kullanıcılar

**Kullanıcılar** ekranında hesapları, rolleri ve CI için API anahtarlarını gösterin. Sunucu her isteği oturum açmış bir hesapla ilişkilendirir.

## Bugüne kadar yapılanlar

**`main` dalında:**

| Alan | İş |
|---|---|
| Sunucu | Neo4j grafik şeması ve migration'lar (#14), uygulama ve sürüm API'si (#128), test ve adım API'si (#39), hesaplar, roller ve API anahtarları (#60), OpenAPI sözleşmesi (#31), ortak hata biçimi (#158) |
| Ajan | İstemciyle JSON-RPC bağlantısı (#16), öge tanımı (#11), UI Automation ile pencere yakalama (#12) |
| Yapay zekâ | Yerel modelle Türkçe komuttan test adımı üreten servis (#71), self-healing puanlayıcısı (#49), yerel model denemesi (#7) |
| Karar ve belgeler | Deneme uygulaması ve pilot uygulama kararı (#21), gereksinim senaryoları ve RS taslağı (#34, #35), SDD mimari, test ve yapay zekâ bölümleri (#45, #48, #50) |

**PR'da, inceleme bekliyor (bu demoda görünenler):**

| İş | PR |
|---|---|
| Ajanı istemciden yönetme | #154 |
| Anlık görüntü içe aktarma | #182 |
| Nesne Gözcüsü | #186 |
| Ögeyi depoya ekleme | #187 |
| Arayüz tasarımı ve uygulama kabuğu | #188 |
| Üç panelli Nesne Gözcüsü | #189 |
| Türkçe ve İngilizce arayüz | #190 |
| Depo ekranı | #191 |
| Kodsuz test editörü | #192 |

**PR'da, inceleme bekliyor (demoda görünmeyenler):**

| İş | PR |
|---|---|
| Koşu kayıtları ve canlı durum, sunucu tarafı (#44) | #193 |
| SDD yapay zekâ bölümü ve tasarım gerekçeleri (#53) | #194 |
| WinForms yavaşlığının ölçümü (#161) | #170 |

## Henüz gösterilemeyenler

| Özellik | Durum |
|---|---|
| Testi çalıştırma | Sunucu tarafı PR'da (#193). Oynatma motoru (#26, #40) başlamadı; istemci ekranı ona bağlı. |
| Gerçek Windows penceresi yakalama | Ajan kodu hazır (#12), Windows'ta çalışıyor. Bu demo Mac'te olduğu için kullanılmıyor. |
| İmleçle öge seçme | Ajan tarafı (#22) başlamadı. Ekrandaki kısayol ipucu bu yüzden henüz çalışmaz. |
| Türkçe komutla test üretme | Servis hazır, editördeki panel (#78) başlamadı. |
| Otomatik onarım, raporlar, değişiklik etkisi | Plandaki sonraki haftalarda. |

## Tekrar prova ederken

`npm run demo` yalnızca eksik örnek veriyi ekler; sizin yaptığınız değişiklikleri geri almaz. Provada `login.loginButton` ögesini yeniden adlandırdıysanız, toplantıdan önce adını geri alın. Aksi halde komut aynı adla yeni bir öge daha ekler.
