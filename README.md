# 🧵 Telegram ERP — Tikuvchilik Sexi

Tikuvchilik sexi va fabrikalar uchun Telegram bot ERP tizimi.

## Railway.app da ishga tushirish (5 daqiqa)

### 1-qadam: GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit - Telegram ERP MVP"
git branch -M main
git remote add origin https://github.com/SIZNING_USERNAME/telegram-erp.git
git push -u origin main
```

### 2-qadam: Railway.app da loyiha yaratish

1. [railway.app](https://railway.app) ga kiring
2. **New Project** → **Deploy from GitHub repo**
3. `telegram-erp` reposini tanlang
4. Railway avtomatik Dockerfile ni topib build qiladi

### 3-qadam: PostgreSQL qo'shish

1. Railway dashboard da **+ New** → **Database** → **Add PostgreSQL**
2. PostgreSQL paydo bo'lganda, uni bot servisiga ulang:
   - PostgreSQL servisini bosing → **Variables** → **DATABASE_URL** ni ko'ring
   - Bot servisini bosing → **Variables** → **New Variable**:
     - `DATABASE_URL` = PostgreSQL ning **DATABASE_URL** qiymatini ko'chiring

   **Yoki osonroq usul:** PostgreSQL servisida → **Connect** → bot servisini tanlang → avtomatik ulanadi

### 4-qadam: Redis qo'shish

1. **+ New** → **Database** → **Add Redis**
2. Xuddi shunday Redis ni bot servisiga ulang:
   - `REDIS_URL` = Redis ning **REDIS_URL** qiymati

### 5-qadam: Environment Variables (2 ta kiritasiz)

Bot servisini bosing → **Variables** → qo'shing:

| O'zgaruvchi | Qiymat | Qayerdan olish |
|---|---|---|
| `BOT_TOKEN` | `7123456789:AAH...` | @BotFather dan |
| `ADMIN_TELEGRAM_ID` | `123456789` | @userinfobot dan |

**Tamom! Railway avtomatik deploy qiladi.**

### 6-qadam: Tekshirish

Telegram da botingizga `/start` yozing. Bot javob berishi kerak.

Loglarni ko'rish: Railway dashboard → bot servisi → **Deployments** → oxirgi deploy → **View Logs**

---

## Loyiha tuzilmasi

```
telegram_erp/
├── bot.py                  ← Asosiy fayl (avtomatik migratsiya)
├── config.py               ← Sozlamalar (Railway + lokal)
├── Dockerfile              ← Railway uchun
├── railway.toml            ← Railway konfiguratsiya
├── requirements.txt
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── database.py         ← SQLAlchemy engine/session
│   ├── models/             ← 7 ta jadval
│   ├── handlers/
│   │   ├── start.py        ← /start, ro'yxatdan o'tish
│   │   ├── admin.py        ← Zakaz, xodimlar, hisobot
│   │   ├── worker.py       ← Ish olish/topshirish
│   │   └── qc.py           ← Sifat nazorati
│   ├── keyboards/          ← Inline Keyboard'lar
│   ├── middlewares/         ← Auth middleware
│   ├── services/            ← Biznes logika
│   ├── states/             ← FSM holatlar
│   └── utils/              ← Yordamchi funksiyalar
```

## MVP funksiyalari

- ✅ Xodim ro'yxatdan o'tkazish (6 ta rol)
- ✅ Zakaz ochish va boshqarish
- ✅ Tikuvchi ish olish / topshirish
- ✅ Donabay avtomatik hisob-kitob
- ✅ Kunlik hisobot (ishchi + admin)
- ✅ QC: qabul / rad etish
- ⏳ Mato ombor moduli (v1.1)
- ⏳ Transfer moduli (v1.2)
- ⏳ Web admin panel (v2.0)
