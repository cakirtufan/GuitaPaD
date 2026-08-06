# GuitaPaD — Session Memory Workflow

Bu dosya her geliştirme oturumunun sonunda izlenecek çalışma kuralını tanımlar.

## Amaç

Her oturum sonunda `docs/project_memory.md` güncellenerek aşağıdaki bilgilerin kaybolması önlenir:

- Yapılan gerçek değişiklikler
- Çalıştırılan testler
- Ölçülen sonuçlar
- Teknik kararlar ve gerekçeleri
- Başarısız denemeler
- Geçici workaround’lar
- Açık problemler
- Bir sonraki oturumun ilk adımı

## Oturum başında

1. `docs/project_memory.md` dosyasını oku.
2. En son günlük kaydındaki `Sonraki oturum` bölümünü kontrol et.
3. Mevcut repository durumunu doğrula.
4. Önceki ölçümlerin hâlâ geçerli olduğunu varsayma; kritik noktaları gerektiğinde yeniden test et.
5. Kullanıcıya daha önce cevaplanmış bilgileri tekrar sorma.

## Oturum sırasında

- Her önemli değişikliği küçük ve test edilebilir tut.
- Çalıştırılmayan kodu tamamlandı sayma.
- Audio callback güvenliği ihlal edilmemeli.
- Latency, callback time ve dropout sonuçlarını kaydet.
- Bir teknik karar değişirse eski kararın neden değiştiğini belirt.
- Başarısız deneyleri silme; neyi elediğini kaydet.

## Oturum sonunda

`docs/project_memory.md` içine yeni tarih başlığıyla şu bölümleri ekle:

```markdown
## YYYY-MM-DD

### Hedef

### Yapılanlar

### Doğrulanan sonuçlar

### Teknik kararlar

### Açık konular

### Sonraki oturum
```

Ayrıca şu kontrolleri yap:

- Syntax/test çalıştı mı?
- Audio stream gerçek donanımda test edildi mi?
- Callback status `OK` mı?
- Block mismatch oluştu mu?
- Yeni GUI kontrolü seste click/pop oluşturdu mu?
- Yeni DSP işlemi offline ve real-time test edildi mi?
- Yeni dosyalar git tarafından görülüyor mu?

## Commit öncesi minimum kontrol

```powershell
python -m compileall -q src tools dashboards
git status
```

Testler eklendikten sonra:

```powershell
python -m pytest
```

## Commit mesajı ilkesi

Örnekler:

```text
feat: add input and output peak meters
feat: add smoothed master gain
feat: add offline profiling dashboard
fix: preserve Audient 128-frame ASIO buffer
docs: update project memory for YYYY-MM-DD
```

## Temel doğruluk kuralı

Project memory bir pazarlama metni değildir. Gerçekte çalışmayan, test edilmeyen veya ölçülmeyen hiçbir şey tamamlandı olarak yazılmaz.
