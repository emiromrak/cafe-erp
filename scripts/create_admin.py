"""İlk yönetici parolasını terminalde gizleyerek alır; örnek PIN'leri kullanmaz."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.auth import create_first_admin
from app.database import get_engine


if __name__ == '__main__':
    username = input('Yönetici kullanıcı adı (a-z, 0-9, en az 3 karakter): ').strip()
    name = input('Ad soyad: ').strip()
    password = getpass.getpass('Parola (4–128 karakter): ')
    if password != getpass.getpass('Parola tekrar: '):
        raise SystemExit('Parolalar eşleşmiyor.')
    engine = get_engine()
    try:
        account = create_first_admin(engine, username, name, password)
        print(f"Yönetici oluşturuldu: {account['username']}")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        engine.dispose()
