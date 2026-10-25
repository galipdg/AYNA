# Draft: department GPU access request (#7)

Draft only — Galip sends it. Numbers are from `llm-smoke.md` (2026-10-25 run).

---

**Konu:** AYNA bitirme projesi — bölüm GPU sunucusuna erişim talebi

Sayın Hocam,

AYNA projesinde (COM 4061, HAVELSAN SUIT) Türkçe doğal dil cümlelerinden test adımı üretmek için açık ağırlıklı dil modellerini tamamen yerel (internetsiz) olarak çalıştırıyoruz. İlk denemeyi 16 GB belleğe sahip bir MacBook (Apple M2) üzerinde 7-9B parametreli, 4-bit sıkıştırılmış iki modelle yaptık:

- qwen3:8b — saniyede yaklaşık 15 token, yaklaşık 4,5 GB bellek, 10 yanıtın 10'u şemaya uygun JSON
- gemma4:e4b — saniyede yaklaşık 18 token, yaklaşık 3 GB bellek, 10 yanıtın 9'u şemaya uygun JSON

Önümüzdeki haftalarda (Aralık–Ocak) en az üç modeli karşılaştırmamız, 14B ve üzeri modelleri de denememiz ve 100 cümlelik veri setimizle değerlendirme yapmamız gerekiyor. Bu boyuttaki modeller, uygulamanın diğer bileşenleriyle birlikte 16 GB'lık dizüstü bilgisayarlarımızın belleğine rahatça sığmıyor.

Bu nedenle bölümün GPU sunucusuna (en az 24 GB GPU belleği) aşağıdaki koşullarla erişim rica ediyoruz:

- Kullanım: haftada birkaç saatlik değerlendirme koşuları; model eğitimi yok, yalnızca çıkarım (inference).
- Yazılım: Ollama veya llama.cpp; modeller yerelde tutulur, dış servislere bağlantı gerekmez.
- Kullanıcılar: Galip Enes Doğan, Ömerfaruk Sarıbal, Hasan Berk Yanıkkaya.

Uygun görürseniz erişim için kime başvurmamız gerektiğini ve kullanım kurallarını bildirmenizi rica ederim.

Saygılarımla,
Galip Enes Doğan
