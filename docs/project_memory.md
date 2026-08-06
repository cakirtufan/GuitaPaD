# GuitaPaD — Project Memory

Bu dosya projenin kalıcı teknik hafızasıdır. Her çalışma gününün sonunda güncellenir.

Amaç yalnızca yapılan işleri listelemek değildir. Hangi problemin neden ortaya çıktığını, hangi deneyin neyi kanıtladığını, hangi teknik kararın hangi ölçüme dayandığını ve bir sonraki oturumda nereden devam edileceğini korumaktır.

---

## 1. Projenin amacı

GuitaPaD, Audient EVO 4 ses kartını kullanarak gitar sinyalini gerçek zamanlı işleyen, Python tabanlı ve modüler bir dijital pedalboard uygulamasıdır.

Ana hedefler:

- Audient EVO 4 üzerinden düşük gecikmeli ASIO giriş/çıkış
- Python ile öğrenilebilir ve test edilebilir DSP zinciri
- PySide6 ile canlı masaüstü kontrol arayüzü
- Behringer X-TOUCH MINI ile fiziksel MIDI kontrolü
- Streamlit ile offline profiling, benchmark ve preset karşılaştırması
- Gerektiğinde yalnızca kritik ses katmanının native/JUCE çözümüne taşınabilmesi

Temel sinyal akışı:

```text
Guitar
→ Audient EVO 4 Input 1
→ Python audio engine
→ DSP effect chain
→ Safety limiter
→ Audient EVO 4 Output 1–2
```

---

## 2. Kullanıcı ve çalışma yaklaşımı

- Ana geliştirme dili Python.
- Öncelik hızlı ama ölçülebilir prototipleme.
- Teknoloji veya model körlemesine seçilmeyecek.
- Her önemli karar gerçek latency, callback load, dropout ve ses testiyle doğrulanacak.
- Kod modüler ve JUCE/native backend geçişine açık tutulacak.
- Audio callback içinde dosya işlemi, GUI işi, print, blocking lock veya ağır allocation yapılmayacak.
- Amaç yalnızca hazır kütüphaneleri bağlamak değil; DSP mantığını öğrenerek kendi pedalboard’umuzu geliştirmek.

---

## 3. Mevcut donanım ve ortam

### Audio

- Ses kartı: Audient EVO 4
- Driver: Audient USB Audio ASIO Driver
- ASIO device index: 26
- Gitar girişi: ASIO input channel 1 / Python index 0
- Çıkış: output 1–2, dual-mono
- Sample rate: 48,000 Hz
- Hedef native ASIO buffer: 128 frames

### MIDI

- Behringer X-TOUCH MINI
- İlk aşamada Standard MIDI Mode kullanılacak.
- Layer A ve Layer B ileride ayrı işlev katmanları olarak değerlendirilecek.

### Development

- Repository: `cakirtufan/GuitaPaD`
- Local repository: `G:\Github\GuitaPaD`
- Platform: Windows
- Python: 3.13.2
- Environment: `.venv`
- Audio library: `sounddevice 0.5.5`
- PortAudio ASIO DLL:
  `G:\Github\GuitaPaD\.venv\Lib\site-packages\_sounddevice_data\portaudio-binaries\libportaudio64bit-asio.dll`

---

## 4. Kritik ASIO buffer bulgusu

### Gözlenen problem

Audient paneli elle 128 frames olarak ayarlandığında bazı PortAudio/sounddevice stream açılışlarında buffer şu şekilde büyüyordu:

```text
128 → 256 → 512 → 2048
```

Başlangıçta bunun yalnızca `blocksize` davranışından kaynaklandığı düşünüldü. Kontrollü deneyler bunun eksik bir açıklama olduğunu gösterdi.

### Kontrol deneyi

`PaAsio_GetAvailableBufferSizes` ile stream açmadan yapılan ölçüm:

```text
Minimum native buffer:    8 frames
Maximum native buffer:    2048 frames
Preferred native buffer:  128 frames
Buffer granularity:       -1
Default low input latency:  2.90 ms
Default low output latency: 2.90 ms
```

Bu deney şunu kanıtladı:

- Audient panelindeki 128 ayarı gerçekten ASIO driver’a uygulanıyor.
- PortAudio stream açılmadan önce preferred buffer değerini doğru okuyor.
- Buffer değişimi stream açılışı sırasında gerçekleşiyor.

### Untouched stream deneyi

`blocksize` ve `latency` argümanları verilmeden açılan stream gerçekte sounddevice varsayılanını kullandı:

```text
sounddevice default latency: ['high', 'high']
Frames: 2048
Total reported latency: 94.79 ms
```

Dolayısıyla “argüman vermemek”, Audient’in mevcut 128 değerini olduğu gibi kabul etmek anlamına gelmedi.

### Çözüm

PortAudio stream callback boyutu otomatik bırakıldı:

```python
blocksize=0
```

İstenen native buffer için latency talebi hedef buffer’ın bir frame altına ayarlandı:

```python
target_latency_seconds = (128 - 1) / 48_000
```

Sonuç:

```text
Python callback frames: 128
Input latency:           4.23 ms
Output latency:          5.56 ms
Total latency:           9.79 ms
Status:                  OK
```

Bu workaround mevcut Audient EVO 4 + PortAudio ASIO kombinasyonu için korunmalıdır.

### Kavramsal ayrım

Aşağıdaki kavramlar birbirine karıştırılmamalıdır:

- Audient panelindeki native ASIO buffer
- PortAudio `blocksize`
- Python callback içindeki `frames`
- `stream.latency`

Callback `frames=128` görülmesi tek başına driver panelinin de 128 olduğu anlamına gelmez. Gerektiğinde hem ASIO capability hem stream davranışı birlikte ölçülmelidir.

---

## 5. Mevcut yazılım mimarisi

### Audio

```text
src/guitapad/audio/
├── backend.py
├── config.py
├── engine.py
├── metrics.py
└── sounddevice_backend.py
```

### DSP

```text
src/guitapad/dsp/
├── base.py
├── chain.py
├── gain.py
└── limiter.py
```

### Runtime

```text
src/guitapad/runtime.py
```

Runtime katmanı audio backend, audio engine ve DSP zincirinin sahibidir. CLI, GUI ve ileride MIDI kontrol katmanları aynı runtime state’ini kullanmalıdır.

### GUI

```text
src/guitapad/gui/
├── __init__.py
├── app.py
├── main_window.py
└── theme.py
```

Launcher:

```text
tools/gui.py
```

### Offline dashboard

```text
dashboards/offline_analysis.py
```

Dashboard ASIO stream açmaz. Yalnızca offline DSP profiling ve preset karşılaştırması yapar.

---

## 6. Mevcut canlı DSP zinciri

```text
Input 1
→ Smoothed master gain
→ Hard safety limiter
→ Output 1–2
```

### Master gain

- Güncel başlangıç değeri: `0.60`
- Yaklaşık karşılığı: `-4.44 dB`
- Slider değişimleri doğrudan sıçramaz.
- Yaklaşık 20 ms lineer smoothing uygulanır.
- Input meter gain’den önce ölçülür.
- Output meter gain ve limiter sonrasında ölçülür.

### Safety limiter

- Güncel limit: `0.80`
- Bu limiter müzikal final limiter değildir.
- Erken geliştirme aşamasında beklenmeyen yüksek çıkışları önlemek için kullanılır.

---

## 7. PySide6 canlı arayüz durumu

Çalışan özellikler:

- Koyu tema
- START / STOP
- Master output slider
- Linear gain ve dB gösterimi
- Stream status badge
- Total latency gösterimi
- Max callback süresi
- Callback count
- Target buffer bilgisi
- Callback deadline load
- Callback error ve block mismatch durumu
- Canlı input peak meter
- Canlı output peak meter
- Yaklaşık 300 ms meter release
- Uygulama kapanırken stream’in güvenli durdurulması

Doğrulanan davranış:

```text
48 kHz
128-frame callback
9.79 ms total reported latency
Status OK
No callback errors
No block-size mismatches
```

---

## 8. Streamlit offline dashboard durumu

### DSP Profiling

- Mevcut `Gain → HardLimiter` zincirini benchmark eder.
- 64, 128, 256 ve 512 frame blokları karşılaştırır.
- Mean, P95 ve maximum DSP süresini ölçer.
- Her blok için deadline ve maximum deadline load hesaplar.
- Sonuçları CSV olarak dışa aktarabilir.

Bu değerler ASIO latency değildir. Yalnızca offline DSP block-processing süresidir.

### Preset Comparison

- İki farklı gain ve limiter ayarını karşılaştırır.
- Statik input/output transfer eğrisini gösterir.
- Hard limiting’in başladığı input amplitude değerini hesaplar.
- İleride overdrive, tone, EQ ve cabinet parametreleri eklenir.

---

## 9. Tamamlanan araçlar

```text
tools/list_audio_devices.py
tools/input_meter.py
tools/passthrough.py
tools/asio_buffer_probe.py
tools/compare_block_modes.py
tools/asio_capabilities.py
tools/untouched_asio_probe.py
tools/gui.py
```

Bu araçlar ASIO davranışını yeniden doğrulamak veya regression kontrolü yapmak için korunmalıdır.

---

## 10. Günlük geliştirme günlüğü

## 2026-08-06

### Hedef

Audient EVO 4 üzerinden kararlı düşük gecikmeli passthrough kurmak ve ilk kullanıcı arayüzünü oluşturmak.

### Yapılanlar

- Repository ve Python `.venv` hazırlandı.
- `sounddevice` ASIO desteği doğrulandı.
- Audient EVO 4 ASIO cihazı bulundu.
- Gitar input channel mapping doğrulandı.
- Mono input → output 1–2 passthrough çalıştırıldı.
- Modular audio backend, engine, metrics ve DSP chain oluşturuldu.
- Gain ve safety limiter eklendi.
- Callback süreleri ve stream status ölçüldü.
- Audient buffer’ın stream açılışlarında 128’den 256/512/2048’e büyüdüğü tespit edildi.
- `PaAsio_GetAvailableBufferSizes` ile stream öncesi preferred buffer ölçüldü.
- Sorunun driver panelinden değil stream latency negotiation’dan kaynaklandığı izole edildi.
- `blocksize=0` ve `(target_buffer - 1) / sample_rate` latency workaround’u bulundu.
- 128 callback ve 9.79 ms toplam raporlanan latency doğrulandı.
- Master gain dinleme testi sonucunda `0.60` seçildi.
- PySide6 masaüstü GUI oluşturuldu.
- START/STOP, master slider ve runtime metrics çalıştırıldı.
- Canlı input/output peak meter eklendi.
- Master gain’e 20 ms smoothing eklendi.
- Streamlit offline profiling ve preset comparison dashboard’u oluşturuldu.

### Doğrulanan sonuçlar

```text
Device: Audient USB Audio ASIO Driver
Sample rate: 48,000 Hz
Native/callback buffer: 128 frames
Input latency: 4.23 ms
Output latency: 5.56 ms
Total latency: 9.79 ms
Max callback observed during passthrough: below 0.1 ms in tested runs
Status: OK
```

### Teknik kararlar

- Ana canlı arayüz: PySide6
- Offline analiz: Streamlit
- Streamlit audio engine’in sahibi olmayacak.
- GUI yalnızca runtime state’i okuyacak ve control komutları gönderecek.
- Audio callback GUI’den bağımsız kalacak.
- Gain değişiklikleri smoothing ile uygulanacak.
- ASIO backend mevcut workaround’u koruyacak.

### Açık konular

- Meter ölçümünün callback load üzerindeki etkisi uzun süreli test edilmedi.
- 30 dakika kesintisiz stability testi henüz yapılmadı.
- Input clipping indicator henüz yok.
- Final limiter henüz müzikal limiter değil.
- Preset dosya formatı henüz tanımlanmadı.
- MIDI probe ve X-TOUCH MINI mapping henüz yapılmadı.
- İlk gerçek overdrive/tone efektleri henüz eklenmedi.

### Sonraki oturum

1. Mevcut değişiklikleri commit ve push et.
2. 30 dakika stability testi yap.
3. Input/output clip indicator ekle.
4. İlk gerçek efekt için high-pass filter oluştur.
5. Overdrive algoritmasını offline test sinyalleriyle geliştir.
6. Tone filter ekle.
7. PySide6 GUI’ye efekt bypass ve parametre kontrollerini ekle.
8. X-TOUCH MINI MIDI probe başlat.

---

## 11. Günlük kayıt şablonu

```markdown
## YYYY-MM-DD

### Hedef

Oturumun amacı.

### Yapılanlar

- Gerçekleştirilen değişiklikler
- Eklenen dosyalar
- Yapılan deneyler

### Doğrulanan sonuçlar

- Ölçülen latency
- Callback süreleri
- Dropout/error durumu
- Dinleme testi sonucu

### Teknik kararlar

- Kabul edilen kararlar
- Reddedilen seçenekler ve gerekçeleri

### Açık konular

- Çözülmeyen problemler
- Bilinmeyenler
- Regression riskleri

### Sonraki oturum

1. İlk adım
2. İkinci adım
3. Test kriteri
```

---

## 12. Hafıza güncelleme kuralları

- Yalnızca gerçekten yapılan işler yazılmalıdır.
- Çalıştırılmamış kod “tamamlandı” olarak işaretlenmemelidir.
- Ölçüm sonuçları tahmin edilmemelidir.
- Her workaround’un nedeni ve sınırı yazılmalıdır.
- Geçici çözümler kalıcı mimari kararı gibi sunulmamalıdır.
- Bir önceki kararı değiştiren yeni bulgu varsa eski karar silinmemeli; neden değiştiği kaydedilmelidir.
- Günlük kayıtlar kronolojik olarak korunmalıdır.
- Günün sonunda bir sonraki oturumun ilk somut adımı mutlaka yazılmalıdır.
