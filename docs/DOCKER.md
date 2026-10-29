# Docker ile geliştirme

Docker Desktop Linux konteynerleriyle çalışmalıdır. İlk kullanım öncesi kökteki
`.env` dosyasına `POSTGRES_PASSWORD` ekleyin. Proje kökünden ilk kurulum:

```powershell
docker compose up -d --wait db
docker compose build api
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python scripts/import_sqlite.py
docker compose up -d --wait api
docker compose ps
docker compose logs -f api
docker compose down
```

Sonraki açılışlarda `docker compose up -d --wait api` yeterlidir. Alembic geçişi
tekrar çalıştırılabilir; örnek veri aktarımı hedef doluysa güvenli biçimde durur.

API: http://localhost:8000 — Swagger: http://localhost:8000/docs

`Dockerfile`, Python 3.12 ve LightGBM için OpenMP çalışma zamanını kurar.
Saat dilimi `Europe/Istanbul` olarak ayarlanır.
`requirements.lock`, doğrulanan ortamın paket sürümlerini sabitler;
`requirements.txt` üst düzey bağımlılık listesidir. Yeni paket eklenirse her
iki dosya güncellenmeli ve imaj yeniden oluşturulmalıdır.

## Veri ve ayarlar

- `data/` ve `backend/app/ai/models/` bilgisayardan bağlanır. Konteyneri
  silmek bu dosyaları silmez. Buradaki değişiklikler bilgisayara da yansır;
  önemli verileri ayrıca yedekleyin.
- `.env`, `.venv`, Git geçmişi ve yerel loglar imaja dahil edilmez.
- Compose, kökteki `.env` dosyasından konum ve Telegram ayarlarını okur.
  API servisine yalnızca konum ayarları aktarılır.
- Telegram logları `telegram-logs` adlı Docker volume'ünde saklanır.
  PostgreSQL verileri `postgres-data` volume'ündedir. `docker compose down -v`
  her iki volume'ü ve içindeki verileri siler.
- API yalnızca bilgisayarın `127.0.0.1:8000` adresinde yayımlanır.

## pgAdmin bağlantısı

pgAdmin'de yeni sunucu kaydında host `127.0.0.1`, port `5433`, veritabanı ve
kullanıcı `cafe_erp`, parola ise `.env` içindeki `POSTGRES_PASSWORD` değeridir.
`POSTGRES_PORT`, `POSTGRES_DB` veya `POSTGRES_USER` ayarlanmışsa ilgili değeri
kullanın. Bu ayarlar ilk oluşturulmuş PostgreSQL volume'ünün kullanıcı ve
parolasını sonradan değiştirmez.

`data/sample_cafe.db` ve örnek JSON dosyası eski verilerin aktarım kaynağıdır;
günlük API sorguları artık PostgreSQL kullanır. Kaynak dosyaları yedek olarak
korunur. Örnek veri üreteci eski SQLite/JSON dosyalarını yeniden oluşturur;
PostgreSQL'deki işletme verilerini güncellemez.

## Test ve bakım

```powershell
docker compose exec api python -B -m unittest discover -s tests -v
docker compose exec api python -m pip check
docker compose exec api python backend/app/ai/train_forecast.py
```

Son komut bağlı model dosyasını yeniden eğitir ve değiştirir.
Örnek veri üreteci mevcut veritabanını yeniden oluşturur; başlatma sırasında
otomatik çalıştırılmaz.

## Telegram (isteğe bağlı)

`.env` içinde `TELEGRAM_BOT_TOKEN` ve virgülle ayrılmış
`TELEGRAM_ALLOWED_USER_IDS` tanımlandıktan sonra:

```powershell
docker compose --profile telegram up -d telegram
docker compose stop telegram
```

Aynı tokenle çalışan yerel botu önce durdurun. Bot yalnızca izin verilen
kullanıcıların özel sohbetlerini işler. Normal API başlatma komutu botu açmaz.

## VS Code Dev Container

VS Code'da Microsoft **Dev Containers** uzantısını kurun. Komut paletinden
**Dev Containers: Reopen in Container** seçin. Python ve Pylance eklentileri
konteynerde kurulur; yorumlayıcı `/usr/local/bin/python` olarak seçilir.

Bu ortamda proje `/app` altında açılır, API kod değişikliklerinde yeniden
yüklenir. Windows'taki `.venv` yerine konteynerdeki Linux paketleri kullanılır.
Terminalde testleri doğrudan `python -B -m unittest discover -s tests -v`
ile çalıştırabilirsiniz. **Reopen Folder Locally** komutuyla yerel ortama dönülür.

Dev Container ayarları değiştiğinde **Dev Containers: Rebuild Container**
komutunu kullanın. İlk imaj oluşturma ve eklenti kurulumu internet gerektirir.
