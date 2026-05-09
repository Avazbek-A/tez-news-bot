"""Localization strings for the Spot News Bot.

Supports English (en), Russian (ru), Uzbek (uz), German (de), and Turkish (tr).
Strings missing a translation for a language fall back to English at runtime
(see the t() function at the bottom of this file).
"""

_STRINGS = {
    'start_help': {
        "en": (
            "Spot News Bot\n"
            "\n"
            "Scraping:\n"
            "/scrape 50 — Latest 50 as .txt file\n"
            "/scrape 50 inline — Send as individual messages\n"
            "/scrape 50 audio — .txt + individual voice messages\n"
            "/scrape 50 audio combined — .txt + combined voice (split at 1h)\n"
            "/scrape 35808-35758 — Posts by ID (stable)\n"
            "/scrape 2000-1950 — Posts by offset from latest\n"
            "/scrape 50 images — .txt + article images\n"
            "/scrape from \"<title>\" 50 — Anchor on a title; scrape 50 forward\n"
            "/scrape from \"<title>\" 5 audio combined — Title-anchored + combined MP3\n"
            "/today, /yesterday, /thisweek [flags] — Date-based shortcuts\n"
            "/since YYYY-MM-DD [flags] — Everything since a date\n"
            "\n"
            "How \"from\" works:\n"
            "• Wrap the title in double quotes. A fragment is enough.\n"
            "• Match is case-insensitive; punctuation is ignored.\n"
            "• Bot scans the latest ~2000 posts; most-recent match wins.\n"
            "• The matched article becomes #1 (oldest) in the batch;\n"
            "  the next N-1 newer articles follow.\n"
            "• All flags work: audio, combined, images, inline, file.\n"
            "Example:\n"
            "  /scrape from \"Tashkent metro\" 10 audio combined\n"
            "\n"
            "Auto-scrape:\n"
            "/auto daily 08:00 50 audio combined — Every day at 08:00\n"
            "/auto weekdays 08:00 50 audio — Mon-Fri only\n"
            "/auto weekly Mon 08:00 50 audio — Once a week\n"
            "/auto every 3 50 audio combined — Every 3 days (interval)\n"
            "/auto off — Disable\n"
            "\n"
            "Control:\n"
            "/cancel — Stop a running job\n"
            "\n"
            "Settings:\n"
            "/voice andrew — Change TTS voice\n"
            "/speed fast — Change audio speed\n"
            "/lang en — Change language (en/ru/uz)\n"
            "/order newest|oldest — Default delivery order\n"
            "/ads on|off — Include ads/sponsored content\n"
            "/quality <chars> — Min article length (0 = off)\n"
            "/topics <kw...> | off — Filter by keywords\n"
            "/dedup <0-100> — Collapse near-duplicate titles\n"
            "/summarize on|off — 2-3 sentence LLM summary per article (Groq)\n"
            "/channel — Show/change source channel\n"
            "/status — Show current settings\n"
            "\n"
            "Reading log:\n"
            "/find <query> — Search past delivered articles\n"
            "/unread — Count new articles since last scrape\n"
            "/bookmark <id> [tags...] — Save with optional tags\n"
            "/bookmarks [tag] — List saved (or filter by tag)\n"
            "/unbookmark <id> — Remove a bookmark\n"
            "/resume — Jump to last marked voice message (📍 button)\n"
            "/stats — Reading + audio totals\n"
            "\n"
            "Sources:\n"
            "/sources — List configured sources\n"
            "/addsource <type> <url> [label] — Add (type: telegram or rss)\n"
            "/removesource <id> — Remove"
        ),
        "ru": (
            "Spot News Bot\n"
            "\n"
            "Скрапинг:\n"
            "/scrape 50 — Последние 50 в .txt файле\n"
            "/scrape 50 inline — Отправить отдельными сообщениями\n"
            "/scrape 50 audio — .txt + голосовые сообщения\n"
            "/scrape 50 audio combined — .txt + общий голос (по 1ч)\n"
            "/scrape 35808-35758 — По ID постов (стабильно)\n"
            "/scrape 2000-1950 — По смещению от последнего\n"
            "/scrape 50 images — .txt + изображения статей\n"
            "/scrape from \"<заголовок>\" 50 — От заголовка вперёд на 50\n"
            "/scrape from \"<заголовок>\" 5 audio combined — От заголовка + общий MP3\n"
            "/today, /yesterday, /thisweek [флаги] — По дате\n"
            "/since YYYY-MM-DD [флаги] — Всё с указанной даты\n"
            "\n"
            "Как работает \"from\":\n"
            "• Заголовок — в двойных кавычках. Достаточно фрагмента.\n"
            "• Регистр и пунктуация не учитываются.\n"
            "• Сканируется до 2000 последних постов; берётся самый новый совпавший.\n"
            "• Найденная статья становится #1 (самой старой) в подборке;\n"
            "  далее идут N-1 более новых статей.\n"
            "• Все флаги работают: audio, combined, images, inline, file.\n"
            "Пример:\n"
            "  /scrape from \"Ташкентское метро\" 10 audio combined\n"
            "\n"
            "Авто-скрапинг:\n"
            "/auto daily 08:00 50 audio combined — Каждый день в 08:00\n"
            "/auto weekdays 08:00 50 audio — Только Пн-Пт\n"
            "/auto weekly Mon 08:00 50 audio — Раз в неделю\n"
            "/auto every 3 50 audio combined — Каждые 3 дня (интервал)\n"
            "/auto off — Отключить\n"
            "\n"
            "Управление:\n"
            "/cancel — Остановить текущую задачу\n"
            "\n"
            "Настройки:\n"
            "/voice dmitry — Сменить голос TTS\n"
            "/speed fast — Скорость аудио\n"
            "/lang ru — Сменить язык (en/ru/uz)\n"
            "/order newest|oldest — Порядок отправки по умолчанию\n"
            "/ads on|off — Включать рекламу/спонсорский контент\n"
            "/quality <число> — Минимальная длина статьи (0 = выкл.)\n"
            "/topics <слова...> | off — Фильтр по ключам\n"
            "/dedup <0-100> — Схлопывать похожие заголовки\n"
            "/summarize on|off — 2-3 предложения LLM-резюме (Groq)\n"
            "/channel — Канал-источник\n"
            "/status — Текущие настройки\n"
            "\n"
            "История:\n"
            "/find <запрос> — Поиск по полученным статьям\n"
            "/unread — Сколько новых статей с прошлого сбора\n"
            "/bookmark <id> [теги...] — Сохранить с тегами\n"
            "/bookmarks [тег] — Список (фильтр по тегу)\n"
            "/unbookmark <id> — Удалить закладку\n"
            "/resume — Перейти к отмеченному голосовому (кнопка 📍)\n"
            "/stats — Статистика чтения и аудио\n"
            "\n"
            "Источники:\n"
            "/sources — Список настроенных источников\n"
            "/addsource <тип> <url> [название] — Добавить (тип: telegram или rss)\n"
            "/removesource <id> — Удалить"
        ),
        "uz": (
            "Spot News Bot\n"
            "\n"
            "Skraping:\n"
            "/scrape 50 — So'nggi 50 ta .txt faylda\n"
            "/scrape 50 inline — Alohida xabarlar sifatida\n"
            "/scrape 50 audio — .txt + ovozli xabarlar\n"
            "/scrape 50 audio combined — .txt + umumiy ovoz (1 soatga bo'linadi)\n"
            "/scrape 35808-35758 — Post ID bo'yicha (barqaror)\n"
            "/scrape 2000-1950 — So'nggidan siljish bo'yicha\n"
            "/scrape 50 images — .txt + maqola rasmlari\n"
            "/scrape from \"<sarlavha>\" 50 — Sarlavhadan oldinga 50 ta\n"
            "/scrape from \"<sarlavha>\" 5 audio combined — Sarlavhadan + umumiy MP3\n"
            "/today, /yesterday, /thisweek [bayroqlar] — Sana bo'yicha\n"
            "/since YYYY-MM-DD [bayroqlar] — Sanadan beri hammasi\n"
            "\n"
            "\"from\" qanday ishlaydi:\n"
            "• Sarlavhani qo'shtirnoq ichiga oling. Bo'lak ham yetadi.\n"
            "• Katta-kichik harf va tinish belgilari hisobga olinmaydi.\n"
            "• So'nggi ~2000 post ko'rib chiqiladi; eng yangi mosi olinadi.\n"
            "• Topilgan maqola partiyaning #1 (eng eskisi) bo'ladi;\n"
            "  keyin N-1 yangi maqola keladi.\n"
            "• Barcha flaglar ishlaydi: audio, combined, images, inline, file.\n"
            "Misol:\n"
            "  /scrape from \"Toshkent metro\" 10 audio combined\n"
            "\n"
            "Avto-skraping:\n"
            "/auto daily 08:00 50 audio combined — Har kuni 08:00 da\n"
            "/auto weekdays 08:00 50 audio — Faqat Du-Ju\n"
            "/auto weekly Mon 08:00 50 audio — Haftada bir marta\n"
            "/auto every 3 50 audio combined — Har 3 kunda (interval)\n"
            "/auto off — O'chirish\n"
            "\n"
            "Boshqaruv:\n"
            "/cancel — Joriy vazifani to'xtatish\n"
            "\n"
            "Sozlamalar:\n"
            "/voice sardor — TTS ovozini o'zgartirish\n"
            "/speed fast — Audio tezligi\n"
            "/lang uz — Tilni o'zgartirish (en/ru/uz)\n"
            "/order newest|oldest — Standart yetkazib berish tartibi\n"
            "/ads on|off — Reklamalarni qo'shish\n"
            "/quality <belgi> — Maqola minimal uzunligi (0 = o'chiq)\n"
            "/topics <so'zlar...> | off — Kalit so'zlar bo'yicha filtr\n"
            "/dedup <0-100> — O'xshash sarlavhalarni birlashtirish\n"
            "/summarize on|off — Har maqolaga 2-3 jumlali xulosa (Groq)\n"
            "/channel — Manba kanali\n"
            "/status — Joriy sozlamalar\n"
            "\n"
            "O'qish tarixi:\n"
            "/find <so'rov> — Olingan maqolalar orasidan qidirish\n"
            "/unread — Oxirgi yig'ishdan beri qancha yangi maqola\n"
            "/bookmark <id> [teglar...] — Teg bilan saqlash\n"
            "/bookmarks [teg] — Ro'yxat (teg bo'yicha filtr)\n"
            "/unbookmark <id> — Xatcho'pni olib tashlash\n"
            "/resume — Belgilangan ovozli xabarga o'tish (📍 tugmasi)\n"
            "/stats — O'qish va audio statistikasi\n"
            "\n"
            "Manbalar:\n"
            "/sources — Sozlangan manbalar ro'yxati\n"
            "/addsource <turi> <url> [nomi] — Qo'shish (turi: telegram yoki rss)\n"
            "/removesource <id> — O'chirish"
        ),
        "de": (
            "Spot News Bot\n\n"
            "Scraping:\n"
            "/scrape 50 — Die letzten 50 als .txt-Datei\n"
            "/scrape 50 inline — Als einzelne Nachrichten senden\n"
            "/scrape 50 audio — .txt + einzelne Sprachnachrichten\n"
            "/scrape 50 audio combined — .txt + kombinierte Sprache (geteilt bei 1h)\n"
            "/scrape 35808-35758 — Posts nach ID (stabil)\n"
            "/scrape 2000-1950 — Posts nach Versatz vom neuesten\n"
            "/scrape 50 images — .txt + Artikelbilder\n"
            "/scrape from \"<Titel>\" 50 — Vom Titel an 50 vorwärts\n"
            "/scrape from \"<Titel>\" 5 audio combined — Titel + kombinierte Sprache\n"
            "/today, /yesterday, /thisweek [Flags] — Datumsbasierte Shortcuts\n"
            "/since YYYY-MM-DD [Flags] — Alles ab einem Datum\n\n"
            "Auto-Scrape:\n"
            "/auto daily 08:00 50 audio combined — Täglich um 08:00\n"
            "/auto weekdays 08:00 50 audio — Nur Mo-Fr\n"
            "/auto weekly Mon 08:00 50 audio — Einmal pro Woche\n"
            "/auto every 3 50 audio combined — Alle 3 Tage (Intervall)\n"
            "/auto off — Deaktivieren\n\n"
            "Steuerung:\n"
            "/cancel — Laufenden Vorgang stoppen\n\n"
            "Einstellungen:\n"
            "/voice conrad — TTS-Stimme ändern\n"
            "/voice de katja — Stimme pro Sprache überschreiben\n"
            "/speed fast — Audiogeschwindigkeit\n"
            "/lang de — Sprache (en/ru/uz/de/tr)\n"
            "/order newest|oldest — Standardreihenfolge\n"
            "/ads on|off — Werbung einschließen\n"
            "/quality <Zeichen> — Mindestlänge (0 = aus)\n"
            "/topics <Wörter...> | off — Nach Keywords filtern\n"
            "/dedup <0-100> — Ähnliche Titel zusammenführen\n"
            "/summarize on|off — 2-3 Sätze LLM-Zusammenfassung (Groq)\n"
            "/voice_engine edge|piper|supertonic — TTS-Engine\n"
            "/channel — Quellkanal anzeigen/ändern\n"
            "/status — Aktuelle Einstellungen\n\n"
            "Lese-Log:\n"
            "/find <Suche> — In gelieferten Artikeln suchen\n"
            "/unread — Neue Artikel seit letztem Scrape\n"
            "/bookmark <id> [tags...] — Mit optionalen Tags speichern\n"
            "/bookmarks [tag] — Lesezeichen auflisten\n"
            "/unbookmark <id> — Lesezeichen entfernen\n"
            "/resume — Zur markierten Sprachnachricht (📍 Knopf)\n"
            "/stats — Lese- und Audio-Statistik\n\n"
            "Quellen:\n"
            "/sources — Konfigurierte Quellen auflisten\n"
            "/addsource <typ> <url> [Name] — Hinzufügen (typ: telegram oder rss)\n"
            "/removesource <id> — Entfernen"
        ),
        "tr": (
            "Spot News Bot\n\n"
            "Scraping:\n"
            "/scrape 50 — Son 50 .txt dosyası olarak\n"
            "/scrape 50 inline — Ayrı mesajlar olarak gönder\n"
            "/scrape 50 audio — .txt + ayrı sesli mesajlar\n"
            "/scrape 50 audio combined — .txt + birleşik ses (1s'de bölünür)\n"
            "/scrape 35808-35758 — ID'ye göre gönderiler (kararlı)\n"
            "/scrape 2000-1950 — Sondan kayma ile gönderiler\n"
            "/scrape 50 images — .txt + makale görselleri\n"
            "/scrape from \"<başlık>\" 50 — Başlıktan 50 ileri\n"
            "/scrape from \"<başlık>\" 5 audio combined — Başlık + birleşik MP3\n"
            "/today, /yesterday, /thisweek [bayraklar] — Tarihe göre kısayollar\n"
            "/since YYYY-MM-DD [bayraklar] — Tarihten itibaren her şey\n\n"
            "Otomatik scrape:\n"
            "/auto daily 08:00 50 audio combined — Her gün 08:00'de\n"
            "/auto weekdays 08:00 50 audio — Sadece Pzt-Cum\n"
            "/auto weekly Mon 08:00 50 audio — Haftada bir\n"
            "/auto every 3 50 audio combined — Her 3 günde (aralık)\n"
            "/auto off — Devre dışı\n\n"
            "Kontrol:\n"
            "/cancel — Çalışan işi durdur\n\n"
            "Ayarlar:\n"
            "/voice ahmet — TTS sesini değiştir\n"
            "/voice tr emel — Dile göre ses geçersiz kıl\n"
            "/speed fast — Ses hızı\n"
            "/lang tr — Dil (en/ru/uz/de/tr)\n"
            "/order newest|oldest — Varsayılan teslim sırası\n"
            "/ads on|off — Reklamları dahil et\n"
            "/quality <karakter> — Minimum uzunluk (0 = kapalı)\n"
            "/topics <kelimeler...> | off — Anahtar kelimeyle filtrele\n"
            "/dedup <0-100> — Benzer başlıkları birleştir\n"
            "/summarize on|off — 2-3 cümle LLM özeti (Groq)\n"
            "/voice_engine edge|piper|supertonic — TTS motoru\n"
            "/channel — Kaynak kanalı göster/değiştir\n"
            "/status — Mevcut ayarları göster\n\n"
            "Okuma günlüğü:\n"
            "/find <sorgu> — Geçmiş makalelerde ara\n"
            "/unread — Son scrape'den beri yeni makale sayısı\n"
            "/bookmark <id> [tags...] — İsteğe bağlı etiketle kaydet\n"
            "/bookmarks [tag] — Yer imlerini listele\n"
            "/unbookmark <id> — Yer imini kaldır\n"
            "/resume — Son işaretli sesli mesaja atla (📍 düğmesi)\n"
            "/stats — Okuma + ses toplamları\n\n"
            "Kaynaklar:\n"
            "/sources — Yapılandırılmış kaynakları listele\n"
            "/addsource <tür> <url> [etiket] — Ekle (tür: telegram veya rss)\n"
            "/removesource <id> — Kaldır"
        ),
    },

    'job_running': {
        "en": 'A job is already running. Use /cancel to stop it first.',
        "ru": 'Задание уже выполняется. Используйте /cancel для отмены.',
        "uz": "Vazifa allaqachon bajarilmoqda. To'xtatish uchun /cancel ni bosing.",
        "de": 'Ein Vorgang läuft bereits. /cancel zum Stoppen.',
        "tr": 'Zaten bir iş çalışıyor. Durdurmak için /cancel.',
    },

    'range_format': {
        "en": (
            "Range must be two different numbers.\n"
            "Example: /scrape 31000-31050 (by post ID)\n"
            "Example: /scrape 1950-2000 (by offset)"
        ),
        "ru": (
            "Диапазон должен содержать два разных числа.\n"
            "Пример: /scrape 31000-31050 (по ID постов)\n"
            "Пример: /scrape 1950-2000 (по смещению)"
        ),
        "uz": (
            "Diapazon ikki xil son bo'lishi kerak.\n"
            "Misol: /scrape 31000-31050 (post ID bo'yicha)\n"
            "Misol: /scrape 1950-2000 (siljish bo'yicha)"
        ),
        "de": 'Bereich muss wie 35808-35758 oder 2000-1950 aussehen.',
        "tr": 'Aralık 35808-35758 veya 2000-1950 gibi olmalı.',
    },

    'max_range': {
        "en": 'Max range size is {max} posts.',
        "ru": 'Максимальный размер диапазона: {max} постов.',
        "uz": 'Maksimal diapazon hajmi: {max} ta post.',
        "de": 'Bereich zu groß. Maximum: {max} Posts.',
        "tr": 'Aralık çok büyük. En fazla: {max} gönderi.',
    },

    'max_offset': {
        "en": 'Max offset is {max}. For larger numbers, use post IDs (both numbers > {max}).',
        "ru": 'Максимальное смещение: {max}. Для больших чисел используйте ID постов (оба числа > {max}).',
        "uz": 'Maksimal siljish: {max}. Kattaroq sonlar uchun post ID ishlating (ikkala son > {max}).',
        "de": 'Versatz zu groß. Maximum: {max}.',
        "tr": 'Kayma çok büyük. En fazla: {max}.',
    },

    'starting': {
        "en": 'Starting: {desc}...',
        "ru": 'Запуск: {desc}...',
        "uz": 'Boshlanmoqda: {desc}...',
        "de": 'Starte: {desc}...',
        "tr": 'Başlatılıyor: {desc}...',
    },

    'no_articles': {
        "en": 'No articles found.',
        "ru": 'Статьи не найдены.',
        "uz": 'Maqolalar topilmadi.',
        "de": 'Keine Artikel gefunden.',
        "tr": 'Makale bulunamadı.',
    },

    'from_title_quotes': {
        "en": 'Mismatched quotes. Use: /scrape from "<title>" 50',
        "ru": 'Кавычки не закрыты. Используйте: /scrape from "<заголовок>" 50',
        "uz": 'Qo\'shtirnoqlar yopilmagan. Foydalaning: /scrape from "<sarlavha>" 50',
        "de": 'Anführungszeichen unausgeglichen. Nutze: /scrape from "<Titel>" 50',
        "tr": 'Tırnak işareti dengesiz. Kullan: /scrape from "<başlık>" 50',
    },

    'from_title_missing': {
        "en": 'Missing title. Use: /scrape from "<title>" 50',
        "ru": 'Не указан заголовок. Используйте: /scrape from "<заголовок>" 50',
        "uz": 'Sarlavha ko\'rsatilmagan. Foydalaning: /scrape from "<sarlavha>" 50',
        "de": 'Titel fehlt. Nutze: /scrape from "<Titel>" 50',
        "tr": 'Başlık eksik. Kullan: /scrape from "<başlık>" 50',
    },

    'from_title_not_found': {
        "en": 'No article found matching: {title}',
        "ru": 'Не найдено статьи по запросу: {title}',
        "uz": "So'rov bo'yicha maqola topilmadi: {title}",
        "de": 'Kein Artikel gefunden für: {title}',
        "tr": 'Bulunamadı: {title}',
    },

    'from_title_found': {
        "en": (
            "Found: {preview}\n"
            "Scraping forward..."
        ),
        "ru": (
            "Найдено: {preview}\n"
            "Сбор продолжается..."
        ),
        "uz": (
            "Topildi: {preview}\n"
            "Yig'ish davom etmoqda..."
        ),
        "de": (
            "Gefunden: {preview}\n"
            "Lese vorwärts..."
        ),
        "tr": (
            "Bulundu: {preview}\n"
            "İleri taranıyor..."
        ),
    },

    'from_title_anchor': {
        "en": (
            "Anchor: post #{anchor_id}\n"
            "{preview}"
        ),
        "ru": (
            "Якорь: пост #{anchor_id}\n"
            "{preview}"
        ),
        "uz": (
            "Bog'lanish: post #{anchor_id}\n"
            "{preview}"
        ),
        "de": (
            "Anker: Post #{anchor_id}\n"
            "{preview}"
        ),
        "tr": (
            "Bağlantı: Post #{anchor_id}\n"
            "{preview}"
        ),
    },

    'from_title_searching': {
        "en": (
            "Searching for: {title}\n"
            "(scanning up to 2000 recent posts)"
        ),
        "ru": (
            "Поиск: {title}\n"
            "(сканирую до 2000 последних постов)"
        ),
        "uz": (
            "Qidirilmoqda: {title}\n"
            "(so'nggi 2000 ta postgacha skanerlanadi)"
        ),
        "de": (
            "Suche: {title}\n"
            "(scanne bis zu 2000 Posts)"
        ),
        "tr": (
            "Aranıyor: {title}\n"
            "(en fazla 2000 gönderi taranacak)"
        ),
    },

    'from_title_proceeding': {
        "en": 'Confirmed. Scraping next {count} articles...',
        "ru": 'Подтверждено. Сбор следующих {count} статей...',
        "uz": "Tasdiqlandi. Keyingi {count} ta maqola yig'ilmoqda...",
        "de": 'Bestätigt. Lese die nächsten {count} Artikel...',
        "tr": 'Onaylandı. Sonraki {count} makale alınıyor...',
    },

    'confirm_anchor': {
        "en": (
            "Found this article — scrape forward from here?\n"
            "\n"
            "Title: {preview}\n"
            "Post ID: #{anchor_id}\n"
            "Date: {date}\n"
            "Will scrape: {count} articles starting from this one"
        ),
        "ru": (
            "Найдена эта статья — собрать вперёд от неё?\n"
            "\n"
            "Заголовок: {preview}\n"
            "ID поста: #{anchor_id}\n"
            "Дата: {date}\n"
            "Будет собрано: {count} статей, начиная с этой"
        ),
        "uz": (
            "Bu maqola topildi — shu joydan boshlab oldinga yig'ilsinmi?\n"
            "\n"
            "Sarlavha: {preview}\n"
            "Post ID: #{anchor_id}\n"
            "Sana: {date}\n"
            "Yig'iladi: shu maqoladan boshlab {count} ta"
        ),
        "de": (
            "Diesen Artikel gefunden — von hier vorwärts lesen?\n"
            "\n"
            "Titel: {preview}\n"
            "Post-ID: #{anchor_id}\n"
            "Datum: {date}\n"
            "Wird gelesen: {count} Artikel ab diesem"
        ),
        "tr": (
            "Bu makale bulundu — buradan ileri okunsun mu?\n"
            "\n"
            "Başlık: {preview}\n"
            "Post ID: #{anchor_id}\n"
            "Tarih: {date}\n"
            "Alınacak: bu makaleden başlayarak {count} adet"
        ),
    },

    'confirm_yes_btn': {
        "en": '✅ Confirm',
        "ru": '✅ Подтвердить',
        "uz": '✅ Tasdiqlash',
        "de": '✅ Bestätigen',
        "tr": '✅ Onayla',
    },

    'confirm_no_btn': {
        "en": '❌ Cancel',
        "ru": '❌ Отмена',
        "uz": '❌ Bekor qilish',
        "de": '❌ Abbrechen',
        "tr": '❌ İptal',
    },

    'confirm_cancelled': {
        "en": 'Cancelled. No articles scraped.',
        "ru": 'Отменено. Статьи не собраны.',
        "uz": "Bekor qilindi. Maqolalar yig'ilmadi.",
        "de": 'Abgebrochen. Keine Artikel gelesen.',
        "tr": 'İptal edildi. Makale alınmadı.',
    },

    'confirm_timeout': {
        "en": 'No response in 5 minutes. Cancelled.',
        "ru": 'Нет ответа за 5 минут. Отменено.',
        "uz": "5 daqiqa ichida javob yo'q. Bekor qilindi.",
        "de": 'Keine Antwort in 5 Minuten. Abgebrochen.',
        "tr": '5 dakika içinde yanıt yok. İptal edildi.',
    },

    'sending_articles': {
        "en": 'Sending {count} articles...',
        "ru": 'Отправка {count} статей...',
        "uz": '{count} ta maqola yuborilmoqda...',
        "de": 'Sende {count} Artikel...',
        "tr": '{count} makale gönderiliyor...',
    },

    'sending_images': {
        "en": 'Sending images...',
        "ru": 'Отправка изображений...',
        "uz": 'Rasmlar yuborilmoqda...',
        "de": 'Sende Bilder...',
        "tr": 'Görseller gönderiliyor...',
    },

    'combining_audio': {
        "en": 'Combining audio with announcements...',
        "ru": 'Объединение аудио с анонсами...',
        "uz": "Audio e'lonlar bilan birlashtirilmoqda...",
        "de": 'Kombiniere Audio mit Ankündigungen...',
        "tr": 'Ses, duyurularla birleştiriliyor...',
    },

    'chapters_header': {
        "en": '📑 Chapters (scrub the voice message above):',
        "ru": '📑 Главы (прокрутите голосовое выше):',
        "uz": "📑 Bo'limlar (yuqoridagi ovozni o'zgartiring):",
        "de": '📑 Kapitel (Sprachnachricht oben scrollen):',
        "tr": '📑 Bölümler (yukarıdaki sesli mesajı kaydır):',
    },

    'menu_configure': {
        "en": 'Configure your scrape:',
        "ru": 'Настройте сбор:',
        "uz": "Yig'ishni sozlang:",
        "de": 'Scrape konfigurieren:',
        "tr": "Scrape'i yapılandır:",
    },

    'menu_format_text': {
        "en": '📄 Text',
        "ru": '📄 Текст',
        "uz": '📄 Matn',
        "de": '📄 Text',
        "tr": '📄 Metin',
    },

    'menu_format_audio': {
        "en": '🎵 Audio',
        "ru": '🎵 Аудио',
        "uz": '🎵 Audio',
        "de": '🎵 Audio',
        "tr": '🎵 Ses',
    },

    'menu_format_combined': {
        "en": '🎙️ Combined',
        "ru": '🎙️ Общее',
        "uz": '🎙️ Umumiy',
        "de": '🎙️ Kombiniert',
        "tr": '🎙️ Birleşik',
    },

    'menu_order_newest': {
        "en": '⬆️ Newest',
        "ru": '⬆️ Новые',
        "uz": '⬆️ Yangi',
        "de": '⬆️ Neueste',
        "tr": '⬆️ En yeni',
    },

    'menu_order_oldest': {
        "en": '⬇️ Oldest',
        "ru": '⬇️ Старые',
        "uz": '⬇️ Eski',
        "de": '⬇️ Älteste',
        "tr": '⬇️ En eski',
    },

    'menu_start': {
        "en": '▶️ Start',
        "ru": '▶️ Старт',
        "uz": '▶️ Boshlash',
        "de": '▶️ Start',
        "tr": '▶️ Başlat',
    },

    'menu_cancel': {
        "en": '✖️ Cancel',
        "ru": '✖️ Отмена',
        "uz": '✖️ Bekor',
        "de": '✖️ Abbrechen',
        "tr": '✖️ İptal',
    },

    'menu_starting': {
        "en": 'Starting: /scrape {args}',
        "ru": 'Запуск: /scrape {args}',
        "uz": 'Boshlanmoqda: /scrape {args}',
        "de": 'Starte: /scrape {args}',
        "tr": 'Başlatılıyor: /scrape {args}',
    },

    'menu_cancelled': {
        "en": 'Menu cancelled.',
        "ru": 'Меню закрыто.',
        "uz": 'Menyu bekor qilindi.',
        "de": 'Menü abgebrochen.',
        "tr": 'Menü iptal edildi.',
    },

    'menu_expired': {
        "en": 'Menu expired. Send /scrape again.',
        "ru": 'Меню устарело. Отправьте /scrape снова.',
        "uz": 'Menyu eskirgan. /scrape ni qayta yuboring.',
        "de": 'Menü abgelaufen. Sende /scrape erneut.',
        "tr": "Menü süresi doldu. /scrape'i tekrar gönder.",
    },

    'unread_empty': {
        "en": "No reading history yet. Run /scrape first; I'll start tracking from there.",
        "ru": 'История пуста. Запустите /scrape — отсчёт начнётся с этого момента.',
        "uz": "Tarix bo'sh. Avval /scrape ni ishga tushiring; shundan boshlab kuzataman.",
        "de": 'Noch keine Lesehistorie. Starte mit /scrape; ich beginne ab dann zu zählen.',
        "tr": 'Henüz okuma geçmişi yok. Önce /scrape çalıştır; oradan saymaya başlarım.',
    },

    'unread_none': {
        "en": 'Up to date — no new articles since #{last}.',
        "ru": 'Всё актуально — новых статей нет с #{last}.',
        "uz": "Yangiliklar yo'q — #{last} dan keyin yangi maqola yo'q.",
        "de": 'Aktuell — keine neuen Artikel seit #{last}.',
        "tr": 'Güncel — #{last} sonrası yeni makale yok.',
    },

    'unread_count': {
        "en": (
            "{count} new articles since last scrape (#{last} → #{latest}).\n"
            "Run /scrape {latest}-{last} to fetch."
        ),
        "ru": (
            "{count} новых статей с прошлого сбора (#{last} → #{latest}).\n"
            "Запустите /scrape {latest}-{last}."
        ),
        "uz": (
            "Oxirgi yig'ishdan beri {count} ta yangi maqola (#{last} → #{latest}).\n"
            "Uni olish: /scrape {latest}-{last}"
        ),
        "de": (
            "{count} neue Artikel seit dem letzten Scrape (#{last} → #{latest}).\n"
            "/scrape {latest}-{last} zum Holen."
        ),
        "tr": (
            "Son scrape'den beri {count} yeni makale (#{last} → #{latest}).\n"
            "Almak için: /scrape {latest}-{last}"
        ),
    },

    'unread_error': {
        "en": "Couldn't reach the channel: {err}",
        "ru": 'Не удалось обратиться к каналу: {err}',
        "uz": "Kanalga ulanib bo'lmadi: {err}",
        "de": 'Konnte den Kanal nicht erreichen: {err}',
        "tr": 'Kanala erişilemedi: {err}',
    },

    'bookmark_save_btn': {
        "en": '🔖 Save',
        "ru": '🔖 Сохранить',
        "uz": '🔖 Saqlash',
        "de": '🔖 Speichern',
        "tr": '🔖 Kaydet',
    },

    'bookmark_saved_btn': {
        "en": '✅ Saved',
        "ru": '✅ Сохранено',
        "uz": '✅ Saqlandi',
        "de": '✅ Gespeichert',
        "tr": '✅ Kaydedildi',
    },

    'bookmark_saved_toast': {
        "en": 'Saved #{id}',
        "ru": 'Сохранено #{id}',
        "uz": '#{id} saqlandi',
        "de": 'Gespeichert #{id}',
        "tr": 'Kaydedildi #{id}',
    },

    'bookmarks_empty': {
        "en": 'No bookmarks yet. Tap 🔖 Save under any article to add one.',
        "ru": 'Закладок пока нет. Нажмите 🔖 Сохранить под статьёй.',
        "uz": "Hali xatcho'plar yo'q. Maqola ostidagi 🔖 Saqlash ni bosing.",
        "de": 'Noch keine Lesezeichen. Tippe 🔖 Speichern unter einem Artikel.',
        "tr": "Henüz yer imi yok. Bir makalenin altındaki 🔖 Kaydet'e dokun.",
    },

    'bookmarks_header': {
        "en": '🔖 {n} bookmarks:',
        "ru": '🔖 {n} закладок:',
        "uz": "🔖 {n} ta xatcho'p:",
        "de": '🔖 {n} Lesezeichen:',
        "tr": '🔖 {n} yer imi:',
    },

    'unbookmark_usage': {
        "en": 'Usage: /unbookmark <post_id>  (e.g. /unbookmark 35808)',
        "ru": 'Использование: /unbookmark <post_id>  (например /unbookmark 35808)',
        "uz": 'Foydalanish: /unbookmark <post_id>  (masalan /unbookmark 35808)',
        "de": 'Verwendung: /unbookmark <post_id>  (z.B. /unbookmark 35808)',
        "tr": 'Kullanım: /unbookmark <post_id>  (örn. /unbookmark 35808)',
    },

    'unbookmark_removed': {
        "en": 'Removed bookmark #{id}.',
        "ru": 'Закладка #{id} удалена.',
        "uz": "#{id} xatcho'pi o'chirildi.",
        "de": 'Lesezeichen #{id} entfernt.',
        "tr": 'Yer imi #{id} kaldırıldı.',
    },

    'unbookmark_not_found': {
        "en": 'No bookmark for #{id}.',
        "ru": 'Закладка #{id} не найдена.',
        "uz": "#{id} xatcho'pi topilmadi.",
        "de": 'Kein Lesezeichen für #{id}.',
        "tr": '#{id} için yer imi yok.',
    },

    'sources_empty': {
        "en": 'No sources configured. Add one with /addsource.',
        "ru": 'Источники не настроены. Добавьте через /addsource.',
        "uz": "Manbalar sozlanmagan. /addsource orqali qo'shing.",
        "de": 'Keine Quellen konfiguriert. Mit /addsource hinzufügen.',
        "tr": 'Yapılandırılmış kaynak yok. /addsource ile ekle.',
    },

    'sources_header': {
        "en": '📡 {n} sources:',
        "ru": '📡 {n} источников:',
        "uz": '📡 {n} ta manba:',
        "de": '📡 {n} Quellen:',
        "tr": '📡 {n} kaynak:',
    },

    'addsource_usage': {
        "en": (
            "Usage: /addsource <type> <url> [label]\n"
            "Types: telegram | rss\n"
            "  /addsource telegram https://t.me/s/spotuz Spot\n"
            "  /addsource rss https://kun.uz/news/rss Kun.uz"
        ),
        "ru": (
            "Использование: /addsource <тип> <url> [название]\n"
            "Типы: telegram | rss\n"
            "  /addsource telegram https://t.me/s/spotuz Spot\n"
            "  /addsource rss https://kun.uz/news/rss Kun.uz"
        ),
        "uz": (
            "Foydalanish: /addsource <turi> <url> [nomi]\n"
            "Turlari: telegram | rss\n"
            "  /addsource telegram https://t.me/s/spotuz Spot\n"
            "  /addsource rss https://kun.uz/news/rss Kun.uz"
        ),
        "de": (
            "Verwendung: /addsource <typ> <url> [Name]\n"
            "Typen: telegram | rss\n"
            "  /addsource telegram https://t.me/s/spotuz Spot\n"
            "  /addsource rss https://kun.uz/news/rss Kun.uz"
        ),
        "tr": (
            "Kullanım: /addsource <tür> <url> [etiket]\n"
            "Türler: telegram | rss\n"
            "  /addsource telegram https://t.me/s/spotuz Spot\n"
            "  /addsource rss https://kun.uz/news/rss Kun.uz"
        ),
    },

    'addsource_bad_type': {
        "en": "Type must be 'telegram' or 'rss'.",
        "ru": "Тип должен быть 'telegram' или 'rss'.",
        "uz": "Turi 'telegram' yoki 'rss' bo'lishi kerak.",
        "de": "Typ muss 'telegram' oder 'rss' sein.",
        "tr": "Tür 'telegram' veya 'rss' olmalı.",
    },

    'addsource_bad_url': {
        "en": 'URL must start with http:// or https://',
        "ru": 'URL должен начинаться с http:// или https://',
        "uz": 'URL http:// yoki https:// bilan boshlanishi kerak.',
        "de": 'URL muss mit http:// oder https:// beginnen',
        "tr": 'URL http:// veya https:// ile başlamalı',
    },

    'addsource_bad_telegram_url': {
        "en": 'Telegram source URL must start with https://t.me/s/',
        "ru": 'URL Telegram-источника должен начинаться с https://t.me/s/',
        "uz": 'Telegram manba URL https://t.me/s/ bilan boshlanishi kerak.',
        "de": 'Telegram-Quell-URL muss mit https://t.me/s/ beginnen',
        "tr": "Telegram kaynak URL'si https://t.me/s/ ile başlamalı",
    },

    'addsource_added': {
        "en": '✅ Added source: {id} ({label})',
        "ru": '✅ Источник добавлен: {id} ({label})',
        "uz": "✅ Manba qo'shildi: {id} ({label})",
        "de": '✅ Quelle hinzugefügt: {id} ({label})',
        "tr": '✅ Kaynak eklendi: {id} ({label})',
    },

    'removesource_usage': {
        "en": 'Usage: /removesource <id>  (see /sources for ids)',
        "ru": 'Использование: /removesource <id>  (см. /sources)',
        "uz": 'Foydalanish: /removesource <id>  (idlar /sources da)',
        "de": 'Verwendung: /removesource <id>  (siehe /sources)',
        "tr": 'Kullanım: /removesource <id>  (bkz. /sources)',
    },

    'removesource_removed': {
        "en": 'Removed source: {id}',
        "ru": 'Источник удалён: {id}',
        "uz": "Manba o'chirildi: {id}",
        "de": 'Quelle entfernt: {id}',
        "tr": 'Kaynak kaldırıldı: {id}',
    },

    'removesource_not_found': {
        "en": "No source with id '{id}'. Use /sources to list.",
        "ru": "Источник '{id}' не найден. См. /sources.",
        "uz": "'{id}' nomli manba topilmadi. /sources ni ko'ring.",
        "de": "Keine Quelle mit ID '{id}'. /sources zum Auflisten.",
        "tr": "'{id}' kimliğinde kaynak yok. /sources ile listele.",
    },

    'ads_status_on': {
        "en": 'Ads are currently INCLUDED. Use /ads off to filter them out.',
        "ru": 'Реклама сейчас ВКЛЮЧЕНА. Чтобы фильтровать — /ads off.',
        "uz": 'Reklamalar hozir KIRITILGAN. Filtrlash uchun /ads off.',
        "de": 'Werbung wird aktuell EINGESCHLOSSEN. /ads off zum Filtern.',
        "tr": 'Reklamlar şu anda DAHİL EDİLİYOR. Filtrelemek için /ads off.',
    },

    'ads_status_off': {
        "en": 'Ads are currently FILTERED OUT. Use /ads on to keep them.',
        "ru": 'Реклама сейчас ФИЛЬТРУЕТСЯ. Чтобы оставлять — /ads on.',
        "uz": 'Reklamalar hozir FILTRLANYAPTI. Saqlash uchun /ads on.',
        "de": 'Werbung wird aktuell GEFILTERT. /ads on zum Behalten.',
        "tr": 'Reklamlar şu anda FİLTRELENİYOR. Tutmak için /ads on.',
    },

    'ads_set_on': {
        "en": '✅ Ads will now be included in scraped articles.',
        "ru": '✅ Реклама теперь будет оставаться в собранных статьях.',
        "uz": '✅ Endi reklamalar maqolalarda saqlanadi.',
        "de": '✅ Werbung wird jetzt in Artikeln behalten.',
        "tr": '✅ Reklamlar artık makalelerde tutulacak.',
    },

    'ads_set_off': {
        "en": '✅ Ads will now be filtered out of scraped articles.',
        "ru": '✅ Реклама теперь будет фильтроваться из статей.',
        "uz": '✅ Endi reklamalar maqolalardan chiqariladi.',
        "de": '✅ Werbung wird jetzt herausgefiltert.',
        "tr": '✅ Reklamlar artık filtrelenecek.',
    },

    'ads_unknown': {
        "en": "Unknown choice '{choice}'. Use /ads on or /ads off.",
        "ru": "Непонятное значение '{choice}'. Используйте /ads on или /ads off.",
        "uz": "Noma'lum '{choice}'. /ads on yoki /ads off ni ishlating.",
        "de": "Unbekannt '{choice}'. Nutze /ads on oder /ads off.",
        "tr": "Bilinmiyor '{choice}'. /ads on veya /ads off kullan.",
    },

    'status_ads_on': {
        "en": 'Ads: included',
        "ru": 'Реклама: включена',
        "uz": 'Reklamalar: saqlanadi',
        "de": 'Werbung: enthalten',
        "tr": 'Reklamlar: dahil',
    },

    'status_ads_off': {
        "en": 'Ads: filtered',
        "ru": 'Реклама: фильтруется',
        "uz": 'Reklamalar: filtrlanyapti',
        "de": 'Werbung: gefiltert',
        "tr": 'Reklamlar: filtreli',
    },

    'date_label_today': {
        "en": "today's posts",
        "ru": 'посты за сегодня',
        "uz": 'bugungi postlar',
        "de": 'heutige Posts',
        "tr": 'bugünün gönderileri',
    },

    'date_label_yesterday': {
        "en": "yesterday's posts",
        "ru": 'посты за вчера',
        "uz": 'kechagi postlar',
        "de": 'gestrige Posts',
        "tr": 'dünün gönderileri',
    },

    'date_label_thisweek': {
        "en": 'the last 7 days',
        "ru": 'посты за последние 7 дней',
        "uz": "so'nggi 7 kun postlari",
        "de": 'die letzten 7 Tage',
        "tr": 'son 7 gün',
    },

    'date_label_since': {
        "en": 'posts since {date}',
        "ru": 'посты с {date}',
        "uz": '{date} dan beri postlar',
        "de": 'Posts seit {date}',
        "tr": "{date}'den beri gönderiler",
    },

    'date_resolving': {
        "en": 'Looking up {label}...',
        "ru": 'Ищу {label}...',
        "uz": '{label} qidirilmoqda...',
        "de": 'Suche {label}...',
        "tr": '{label} aranıyor...',
    },

    'date_none': {
        "en": 'No posts found for {label}.',
        "ru": 'Постов не найдено за {label}.',
        "uz": "{label} bo'yicha postlar topilmadi.",
        "de": 'Keine Posts gefunden für {label}.',
        "tr": '{label} için gönderi bulunamadı.',
    },

    'date_error': {
        "en": 'Date lookup failed: {err}',
        "ru": 'Ошибка поиска по дате: {err}',
        "uz": "Sana bo'yicha qidirish xatosi: {err}",
        "de": 'Datumssuche fehlgeschlagen: {err}',
        "tr": 'Tarih araması başarısız: {err}',
    },

    'date_found': {
        "en": 'Found {label}: posts #{oldest}-#{newest}. Starting...',
        "ru": 'Найдено {label}: посты #{oldest}-#{newest}. Запуск...',
        "uz": '{label} topildi: postlar #{oldest}-#{newest}. Boshlanmoqda...',
        "de": 'Gefunden {label}: Posts #{oldest}-#{newest}. Starte...',
        "tr": '{label} bulundu: gönderiler #{oldest}-#{newest}. Başlatılıyor...',
    },

    'since_usage': {
        "en": (
            "Usage: /since YYYY-MM-DD [audio combined images inline ...]\n"
            "Example: /since 2026-05-01 audio combined"
        ),
        "ru": (
            "Использование: /since YYYY-MM-DD [audio combined images inline ...]\n"
            "Пример: /since 2026-05-01 audio combined"
        ),
        "uz": (
            "Foydalanish: /since YYYY-MM-DD [audio combined images inline ...]\n"
            "Misol: /since 2026-05-01 audio combined"
        ),
        "de": (
            "Verwendung: /since YYYY-MM-DD [audio combined images inline ...]\n"
            "Beispiel: /since 2026-05-01 audio combined"
        ),
        "tr": (
            "Kullanım: /since YYYY-MM-DD [audio combined images inline ...]\n"
            "Örnek: /since 2026-05-01 audio combined"
        ),
    },

    'since_bad_date': {
        "en": 'Date must look like YYYY-MM-DD (e.g. 2026-05-01).',
        "ru": 'Дата должна быть в формате YYYY-MM-DD (напр. 2026-05-01).',
        "uz": "Sana YYYY-MM-DD ko'rinishida bo'lishi kerak (masalan 2026-05-01).",
        "de": 'Datum muss wie YYYY-MM-DD aussehen (z.B. 2026-05-01).',
        "tr": 'Tarih YYYY-MM-DD gibi olmalı (örn. 2026-05-01).',
    },

    'since_future': {
        "en": 'Date is in the future — nothing to scrape yet.',
        "ru": 'Дата в будущем — пока ничего собирать.',
        "uz": "Sana kelajakda — hozircha yig'iladigan narsa yo'q.",
        "de": 'Datum liegt in der Zukunft — nichts zu lesen.',
        "tr": 'Tarih gelecekte — alınacak bir şey yok.',
    },

    'find_usage': {
        "en": (
            "Usage: /find <query>\n"
            "Searches all articles you've ever received."
        ),
        "ru": (
            "Использование: /find <запрос>\n"
            "Ищет среди всех когда-либо полученных статей."
        ),
        "uz": (
            "Foydalanish: /find <so'rov>\n"
            "Olingan barcha maqolalar orasidan qidiradi."
        ),
        "de": (
            "Verwendung: /find <Suche>\n"
            "Sucht in allen jemals erhaltenen Artikeln."
        ),
        "tr": (
            "Kullanım: /find <sorgu>\n"
            "Almış olduğun tüm makalelerde arar."
        ),
    },

    'find_none': {
        "en": "No matches for '{query}'.",
        "ru": "Не найдено совпадений для '{query}'.",
        "uz": "'{query}' bo'yicha mos topilmadi.",
        "de": "Keine Treffer für '{query}'.",
        "tr": "'{query}' için eşleşme yok.",
    },

    'find_header': {
        "en": "🔎 {n} match(es) for '{query}':",
        "ru": "🔎 {n} совпадений для '{query}':",
        "uz": "🔎 '{query}' bo'yicha {n} ta moslik:",
        "de": "🔎 {n} Treffer für '{query}':",
        "tr": "🔎 '{query}' için {n} eşleşme:",
    },

    'resume_marked_toast': {
        "en": '📍 Resume point set',
        "ru": '📍 Точка возврата установлена',
        "uz": '📍 Davom etish nuqtasi belgilandi',
        "de": '📍 Wiederaufnahme-Punkt gesetzt',
        "tr": '📍 Devam noktası ayarlandı',
    },

    'resume_none': {
        "en": 'No resume point set yet. Tap 📍 Mark here under any voice message to set one.',
        "ru": 'Точка возврата не установлена. Нажмите 📍 Mark here под голосовым сообщением.',
        "uz": "Davom etish nuqtasi yo'q. Ovozli xabar ostidagi 📍 Mark here ni bosing.",
        "de": 'Noch kein Wiederaufnahme-Punkt. 📍 Mark here unter einer Sprachnachricht antippen.',
        "tr": "Henüz devam noktası yok. Bir sesli mesajın altındaki 📍 Mark here'a dokun.",
    },

    'resume_pointer': {
        "en": '📍 You marked this voice message. Tap to play, scrub to where you stopped.',
        "ru": '📍 Вы отметили это голосовое. Нажмите воспроизвести и прокрутите туда, где остановились.',
        "uz": "📍 Bu ovozli xabarni belgilagansiz. Bosing va qayerda to'xtagan bo'lsangiz, o'sha joyga o'tib oling.",
        "de": '📍 Du hast diese Sprachnachricht markiert. Antippen, zum Stopp-Punkt scrollen.',
        "tr": '📍 Bu sesli mesajı işaretledin. Oyna ve durduğun yere kaydır.',
    },

    'resume_lost': {
        "en": "Couldn't find the marked message — it may have been deleted from chat history.",
        "ru": 'Отмеченное сообщение не найдено — возможно, оно удалено.',
        "uz": "Belgilangan xabar topilmadi — ehtimol, o'chirilgan.",
        "de": 'Markierte Nachricht nicht gefunden — eventuell gelöscht.',
        "tr": 'İşaretli mesaj bulunamadı — silinmiş olabilir.',
    },

    'quality_off': {
        "en": 'Quality filter is OFF (no min length).',
        "ru": 'Фильтр качества ВЫКЛ.',
        "uz": "Sifat filtri O'CHIQ.",
        "de": 'Qualitätsfilter ist AUS.',
        "tr": 'Kalite filtresi KAPALI.',
    },

    'quality_status': {
        "en": 'Quality filter: drop articles under {n} chars.',
        "ru": 'Фильтр качества: пропускать статьи короче {n} символов.',
        "uz": 'Sifat filtri: {n} belgidan qisqa maqolalar tashlanadi.',
        "de": 'Qualitätsfilter: Artikel unter {n} Zeichen verwerfen.',
        "tr": 'Kalite filtresi: {n} karakterden kısa makaleler atılır.',
    },

    'quality_usage': {
        "en": (
            "Usage: /quality <chars>  (e.g. /quality 200)\n"
            "Use 0 to disable."
        ),
        "ru": (
            "Использование: /quality <число>  (напр. /quality 200)\n"
            "0 — отключить."
        ),
        "uz": (
            "Foydalanish: /quality <son>  (masalan /quality 200)\n"
            "0 — o'chirish."
        ),
        "de": (
            "Verwendung: /quality <Zeichen>  (z.B. /quality 200)\n"
            "0 = aus."
        ),
        "tr": (
            "Kullanım: /quality <karakter>  (örn. /quality 200)\n"
            "0 = kapalı."
        ),
    },

    'quality_range': {
        "en": 'Threshold must be 0..10000.',
        "ru": 'Порог должен быть 0..10000.',
        "uz": "Chegara 0..10000 bo'lishi kerak.",
        "de": 'Schwelle muss 0..10000 sein.',
        "tr": 'Eşik 0..10000 olmalı.',
    },

    'quality_set_off': {
        "en": '✅ Quality filter disabled.',
        "ru": '✅ Фильтр качества отключён.',
        "uz": "✅ Sifat filtri o'chirildi.",
        "de": '✅ Qualitätsfilter aus.',
        "tr": '✅ Kalite filtresi kapalı.',
    },

    'quality_set_on': {
        "en": '✅ Quality threshold set to {n} chars.',
        "ru": '✅ Порог качества: {n} символов.',
        "uz": '✅ Sifat chegarasi: {n} belgi.',
        "de": '✅ Qualitäts-Schwelle: {n} Zeichen.',
        "tr": '✅ Kalite eşiği: {n} karakter.',
    },

    'topics_off': {
        "en": 'Topic filter is OFF (all articles delivered).',
        "ru": 'Фильтр тем ВЫКЛ (доставляются все статьи).',
        "uz": "Mavzu filtri O'CHIQ (hamma maqolalar yuboriladi).",
        "de": 'Themenfilter AUS (alle Artikel).',
        "tr": 'Konu filtresi KAPALI (tüm makaleler).',
    },

    'topics_status': {
        "en": 'Topic filter ON. Keywords: {list}',
        "ru": 'Фильтр тем ВКЛ. Ключи: {list}',
        "uz": "Mavzu filtri YOQ. Kalit so'zlar: {list}",
        "de": 'Themenfilter AN. Keywords: {list}',
        "tr": 'Konu filtresi AÇIK. Anahtar kelimeler: {list}',
    },

    'topics_set_off': {
        "en": '✅ Topic filter disabled.',
        "ru": '✅ Фильтр тем отключён.',
        "uz": "✅ Mavzu filtri o'chirildi.",
        "de": '✅ Themenfilter aus.',
        "tr": '✅ Konu filtresi kapalı.',
    },

    'topics_set_on': {
        "en": '✅ Topic filter on: {list}',
        "ru": '✅ Фильтр тем включён: {list}',
        "uz": '✅ Mavzu filtri yoqildi: {list}',
        "de": '✅ Themenfilter an: {list}',
        "tr": '✅ Konu filtresi açık: {list}',
    },

    'dedup_off': {
        "en": 'Duplicate filter is OFF.',
        "ru": 'Фильтр дублей ВЫКЛ.',
        "uz": "Takrorlar filtri O'CHIQ.",
        "de": 'Duplikat-Filter AUS.',
        "tr": 'Tekrar filtresi KAPALI.',
    },

    'dedup_status': {
        "en": 'Duplicate filter: collapse titles ≥ {n}% similar.',
        "ru": 'Фильтр дублей: схлопывать заголовки от {n}% похожести.',
        "uz": "Takrorlar filtri: {n}% va undan yuqori o'xshash sarlavhalar birlashtiriladi.",
        "de": 'Duplikat-Filter: Titel ab {n}% Ähnlichkeit zusammenführen.',
        "tr": 'Tekrar filtresi: {n}% ve üstü benzerlikteki başlıkları birleştir.',
    },

    'dedup_usage': {
        "en": 'Usage: /dedup <0-100>  (100 = disabled)',
        "ru": 'Использование: /dedup <0-100>  (100 = выкл.)',
        "uz": "Foydalanish: /dedup <0-100>  (100 = o'chiq)",
        "de": 'Verwendung: /dedup <0-100>  (100 = aus)',
        "tr": 'Kullanım: /dedup <0-100>  (100 = kapalı)',
    },

    'dedup_range': {
        "en": 'Threshold must be 0..100.',
        "ru": 'Порог должен быть 0..100.',
        "uz": "Chegara 0..100 bo'lishi kerak.",
        "de": 'Schwelle muss 0..100 sein.',
        "tr": 'Eşik 0..100 olmalı.',
    },

    'dedup_set_off': {
        "en": '✅ Duplicate filter disabled.',
        "ru": '✅ Фильтр дублей отключён.',
        "uz": "✅ Takrorlar filtri o'chirildi.",
        "de": '✅ Duplikat-Filter aus.',
        "tr": '✅ Tekrar filtresi kapalı.',
    },

    'dedup_set_on': {
        "en": '✅ Duplicate threshold set to {n}%.',
        "ru": '✅ Порог дублей: {n}%.',
        "uz": '✅ Takrorlar chegarasi: {n}%.',
        "de": '✅ Duplikat-Schwelle: {n}%.',
        "tr": '✅ Tekrar eşiği: {n}%.',
    },

    'summarize_status_off': {
        "en": 'LLM summaries are OFF. /summarize on to enable.',
        "ru": 'Резюме (LLM) ВЫКЛ. /summarize on — включить.',
        "uz": "LLM xulosalar O'CHIQ. Yoqish uchun: /summarize on.",
        "de": 'LLM-Zusammenfassungen sind AUS. /summarize on zum Aktivieren.',
        "tr": 'LLM özetleri KAPALI. Açmak için /summarize on.',
    },

    'summarize_status_on': {
        "en": 'LLM summaries are ON. Each article gets a 2-3 sentence summary on top.',
        "ru": 'Резюме ВКЛ. К каждой статье добавляется 2-3 предложения сверху.',
        "uz": "LLM xulosalar YOQ. Har maqolaga 2-3 jumlali xulosa qo'shiladi.",
        "de": 'LLM-Zusammenfassungen sind AN. Jeder Artikel bekommt eine 2-3-Satz-Zusammenfassung obendrauf.',
        "tr": 'LLM özetleri AÇIK. Her makale 2-3 cümlelik özet alır.',
    },

    'summarize_status_no_key': {
        "en": "Setting is ON but GROQ_API_KEY isn't set — summaries are silently skipped.",
        "ru": 'Настройка ВКЛ, но GROQ_API_KEY не задан — резюме не создаются.',
        "uz": "Sozlama YOQ, lekin GROQ_API_KEY o'rnatilmagan — xulosalar tashlab yuboriladi.",
        "de": 'Einstellung AN, aber GROQ_API_KEY fehlt — Zusammenfassungen werden übersprungen.',
        "tr": 'Ayar AÇIK ama GROQ_API_KEY yok — özetler atlanır.',
    },

    'summarize_set_on': {
        "en": '✅ LLM summaries enabled.',
        "ru": '✅ LLM-резюме включены.',
        "uz": '✅ LLM xulosalar yoqildi.',
        "de": '✅ LLM-Zusammenfassungen an.',
        "tr": '✅ LLM özetleri açık.',
    },

    'summarize_set_on_no_key': {
        "en": '✅ Enabled — but set GROQ_API_KEY in your env to actually get summaries. Free key at console.groq.com.',
        "ru": '✅ Включено — но укажите GROQ_API_KEY в переменных окружения. Бесплатный ключ: console.groq.com.',
        "uz": "✅ Yoqildi — lekin GROQ_API_KEY ni env da o'rnating. Bepul kalit: console.groq.com.",
        "de": '✅ An — aber setze GROQ_API_KEY in deiner Umgebung. Kostenloser Schlüssel: console.groq.com.',
        "tr": "✅ Açık — ama env'de GROQ_API_KEY ayarla. Ücretsiz anahtar: console.groq.com.",
    },

    'summarize_set_off': {
        "en": '✅ LLM summaries disabled.',
        "ru": '✅ LLM-резюме отключены.',
        "uz": "✅ LLM xulosalar o'chirildi.",
        "de": '✅ LLM-Zusammenfassungen aus.',
        "tr": '✅ LLM özetleri kapalı.',
    },

    'summarize_unknown': {
        "en": "Unknown choice '{choice}'. Use /summarize on or /summarize off.",
        "ru": "Непонятное значение '{choice}'. /summarize on или /summarize off.",
        "uz": "Noma'lum '{choice}'. /summarize on yoki /summarize off.",
        "de": "Unbekannt '{choice}'. /summarize on oder /summarize off.",
        "tr": "Bilinmiyor '{choice}'. /summarize on veya /summarize off.",
    },

    'stats_body': {
        "en": (
            "📊 Stats\n"
            "\n"
            "Last 7 days: {articles_week} articles, {audio_week} min audio\n"
            "All time: {articles_total} articles, {audio_total} min audio\n"
            "Bookmarks: {bookmarks}\n"
            "Days active: {days_active}"
        ),
        "ru": (
            "📊 Статистика\n"
            "\n"
            "За 7 дней: {articles_week} статей, {audio_week} мин аудио\n"
            "Всего: {articles_total} статей, {audio_total} мин аудио\n"
            "Закладок: {bookmarks}\n"
            "Дней активности: {days_active}"
        ),
        "uz": (
            "📊 Statistika\n"
            "\n"
            "So'nggi 7 kun: {articles_week} ta maqola, {audio_week} daqiqa audio\n"
            "Jami: {articles_total} ta maqola, {audio_total} daqiqa audio\n"
            "Xatcho'plar: {bookmarks}\n"
            "Faol kunlar: {days_active}"
        ),
        "de": (
            "📊 Statistik\n"
            "\n"
            "Letzte 7 Tage: {articles_week} Artikel, {audio_week} Min. Audio\n"
            "Gesamt: {articles_total} Artikel, {audio_total} Min. Audio\n"
            "Lesezeichen: {bookmarks}\n"
            "Aktive Tage: {days_active}"
        ),
        "tr": (
            "📊 İstatistik\n"
            "\n"
            "Son 7 gün: {articles_week} makale, {audio_week} dk ses\n"
            "Toplam: {articles_total} makale, {audio_total} dk ses\n"
            "Yer imleri: {bookmarks}\n"
            "Aktif gün: {days_active}"
        ),
    },

    'bookmark_usage': {
        "en": (
            "Usage: /bookmark <post_id> [tag1 tag2 ...]\n"
            "Example: /bookmark 35808 economy interviews"
        ),
        "ru": (
            "Использование: /bookmark <post_id> [тег1 тег2 ...]\n"
            "Пример: /bookmark 35808 экономика интервью"
        ),
        "uz": (
            "Foydalanish: /bookmark <post_id> [teg1 teg2 ...]\n"
            "Misol: /bookmark 35808 iqtisodiyot intervyu"
        ),
        "de": (
            "Verwendung: /bookmark <post_id> [tag1 tag2 ...]\n"
            "Beispiel: /bookmark 35808 economy interviews"
        ),
        "tr": (
            "Kullanım: /bookmark <post_id> [tag1 tag2 ...]\n"
            "Örnek: /bookmark 35808 ekonomi röportaj"
        ),
    },

    'bookmark_added': {
        "en": '🔖 Saved #{id}',
        "ru": '🔖 Сохранено #{id}',
        "uz": '🔖 Saqlandi #{id}',
        "de": '🔖 Gespeichert #{id}',
        "tr": '🔖 Kaydedildi #{id}',
    },

    'bookmark_added_tags': {
        "en": '🔖 Saved #{id} (tags: {tags})',
        "ru": '🔖 Сохранено #{id} (теги: {tags})',
        "uz": '🔖 Saqlandi #{id} (teglar: {tags})',
        "de": '🔖 Gespeichert #{id} (Tags: {tags})',
        "tr": '🔖 Kaydedildi #{id} (etiketler: {tags})',
    },

    'bookmarks_header_tag': {
        "en": '🔖 {n} bookmark(s) tagged #{tag}:',
        "ru": '🔖 {n} закладок с тегом #{tag}:',
        "uz": "🔖 #{tag} tegli {n} ta xatcho'p:",
        "de": '🔖 {n} Lesezeichen mit Tag #{tag}:',
        "tr": '🔖 #{tag} etiketli {n} yer imi:',
    },

    'bookmarks_empty_tag': {
        "en": 'No bookmarks tagged #{tag}.',
        "ru": 'Закладок с тегом #{tag} нет.',
        "uz": "#{tag} tegli xatcho'plar yo'q.",
        "de": 'Keine Lesezeichen mit Tag #{tag}.',
        "tr": '#{tag} etiketli yer imi yok.',
    },

    'share_btn': {
        "en": '📤 Share',
        "ru": '📤 Поделиться',
        "uz": '📤 Ulashish',
        "de": '📤 Teilen',
        "tr": '📤 Paylaş',
    },

    'voice_engine_edge_on': {
        "en": '🎤 Engine: Edge TTS (Microsoft, online, free).',
        "ru": '🎤 Движок: Edge TTS (Microsoft, онлайн, бесплатно).',
        "uz": '🎤 Engine: Edge TTS (Microsoft, online, bepul).',
        "de": '🎤 Engine: Edge TTS (Microsoft, online, kostenlos).',
        "tr": '🎤 Motor: Edge TTS (Microsoft, çevrimiçi, ücretsiz).',
    },

    'voice_engine_piper_on': {
        "en": '🎤 Engine: Piper TTS (local, open-source).',
        "ru": '🎤 Движок: Piper TTS (локальный, open-source).',
        "uz": '🎤 Engine: Piper TTS (mahalliy, open-source).',
        "de": '🎤 Engine: Piper TTS (lokal, Open Source).',
        "tr": '🎤 Motor: Piper TTS (yerel, açık kaynak).',
    },

    'voice_engine_piper_no_model': {
        "en": 'Engine set to Piper but no voice model files found in /app/piper-models. Falling back to Edge TTS at runtime.',
        "ru": 'Движок Piper выбран, но в /app/piper-models нет моделей. На лету используется Edge TTS.',
        "uz": 'Piper tanlangan, lekin /app/piper-models da model topilmadi. Ish vaqtida Edge TTS ishlatiladi.',
        "de": 'Engine auf Piper, aber keine Stimm-Modelldateien in /app/piper-models. Fällt zur Laufzeit auf Edge TTS zurück.',
        "tr": "Motor Piper olarak ayarlandı ama /app/piper-models içinde model yok. Çalışma zamanında Edge TTS'e dönüyor.",
    },

    'voice_engine_unknown': {
        "en": 'Usage: /voice_engine edge | piper | supertonic',
        "ru": 'Использование: /voice_engine edge | piper | supertonic',
        "uz": 'Foydalanish: /voice_engine edge | piper | supertonic',
        "de": 'Verwendung: /voice_engine edge | piper | supertonic',
        "tr": 'Kullanım: /voice_engine edge | piper | supertonic',
    },

    'voice_engine_supertonic_on': {
        "en": '🎤 Engine: Supertonic-3 (open-source ONNX, RU/EN/+28 languages). Uzbek articles route to Edge TTS automatically.\n\n⚠️ First scrape will download the model (~99 MB, ~1 min). Per-article synthesis is ~10-25 sec on CPU. Edge TTS remains the faster default.',
        "ru": '🎤 Движок: Supertonic-3 (open-source ONNX, RU/EN/+28). Узбекские статьи идут через Edge TTS.\n\n⚠️ При первом запуске скачается модель (~99 МБ, ~1 мин). Синтез ~10-25 сек на статью (CPU). Edge TTS быстрее.',
        "uz": "🎤 Engine: Supertonic-3 (open-source ONNX, RU/EN/+28 til). O'zbek maqolalar avtomatik Edge TTS ga yo'naltiriladi.\n\n⚠️ Birinchi marta model yuklanadi (~99 MB, ~1 daqiqa). Har bir maqola ~10-25 soniya (CPU). Edge TTS tezroq.",
        "de": '🎤 Engine: Supertonic-3 (Open Source ONNX, RU/EN/+28 Sprachen). Usbekische Artikel werden automatisch zu Edge TTS geleitet.\n\n⚠️ Beim ersten Start wird das Modell geladen (~99 MB, ~1 Min). Synthese ~10-25 Sek pro Artikel (CPU). Edge TTS bleibt schneller.',
        "tr": "🎤 Motor: Supertonic-3 (açık kaynak ONNX, RU/EN/+28 dil). Özbek makaleler otomatik olarak Edge TTS'e yönlendirilir.\n\n⚠️ İlk taramada model indirilir (~99 MB, ~1 dk). Makale başına sentez ~10-25 sn (CPU). Edge TTS daha hızlı kalır.",
    },

    'voice_engine_set_supertonic': {
        "en": '✅ Voice engine: Supertonic-3 for RU/EN, Edge TTS auto-fallback for Uzbek.\n\n⚠️ First scrape will download the model (~99 MB, ~1 min). Per-article synthesis is ~10-25 sec on Railway CPU. Edge TTS remains the faster default.',
        "ru": '✅ Движок: Supertonic-3 для RU/EN, Edge TTS для узбекского.\n\n⚠️ При первом запуске скачается модель (~99 МБ, ~1 мин). Синтез ~10-25 сек на статью (CPU). Edge TTS быстрее.',
        "uz": "✅ Engine: RU/EN uchun Supertonic-3, o'zbek uchun Edge TTS.\n\n⚠️ Birinchi marta model yuklanadi (~99 MB, ~1 daqiqa). Har bir maqola ~10-25 soniya (CPU). Edge TTS tezroq.",
        "de": '✅ Stimm-Engine: Supertonic-3 für RU/EN, automatischer Edge-Fallback für Usbekisch.\n\n⚠️ Beim ersten Start wird das Modell geladen (~99 MB, ~1 Min). Synthese ~10-25 Sek pro Artikel (CPU). Edge TTS bleibt schneller.',
        "tr": '✅ Ses motoru: RU/EN için Supertonic-3, Özbekçe için otomatik Edge TTS.\n\n⚠️ İlk taramada model indirilir (~99 MB, ~1 dk). Makale başına sentez ~10-25 sn (CPU). Edge TTS daha hızlı kalır.',
    },

    'voice_engine_set_edge': {
        "en": '✅ Voice engine: Edge TTS',
        "ru": '✅ Движок: Edge TTS',
        "uz": '✅ Engine: Edge TTS',
        "de": '✅ Stimm-Engine: Edge TTS',
        "tr": '✅ Ses motoru: Edge TTS',
    },

    'voice_engine_set_piper': {
        "en": '✅ Voice engine: Piper TTS (local, open-source)',
        "ru": '✅ Движок: Piper TTS (локальный, open-source)',
        "uz": '✅ Engine: Piper TTS (mahalliy, open-source)',
        "de": '✅ Stimm-Engine: Piper TTS (lokal, Open Source)',
        "tr": '✅ Ses motoru: Piper TTS (yerel, açık kaynak)',
    },

    'voice_engine_set_piper_no_model': {
        "en": '✅ Set to Piper, but no model files found yet. Drop *.onnx into /app/piper-models (or set PIPER_VOICE_DIR). Until then, Edge TTS will be used at runtime.',
        "ru": '✅ Выбран Piper, но моделей нет. Положите *.onnx в /app/piper-models (или задайте PIPER_VOICE_DIR). Пока используется Edge TTS.',
        "uz": "✅ Piper tanlandi, lekin model fayllar yo'q. *.onnx ni /app/piper-models ga qo'ying (yoki PIPER_VOICE_DIR o'rnating). Hozircha Edge TTS ishlaydi.",
        "de": '✅ Auf Piper gestellt, aber keine Modelle. *.onnx in /app/piper-models legen (oder PIPER_VOICE_DIR setzen). Bis dahin Edge TTS.',
        "tr": "✅ Piper olarak ayarlandı ama model yok. *.onnx'i /app/piper-models'a koy (veya PIPER_VOICE_DIR ayarla). Şimdilik Edge TTS.",
    },

    'auto_usage': {
        "en": (
            "Usage:\n"
            "  /auto daily HH:MM [count] [flags]\n"
            "  /auto weekdays HH:MM [count] [flags]\n"
            "  /auto weekly Mon HH:MM [count] [flags]\n"
            "  /auto every N [count] [flags]\n"
            "  /auto off"
        ),
        "ru": (
            "Использование:\n"
            "  /auto daily HH:MM [count] [flags]\n"
            "  /auto weekdays HH:MM [count] [flags]\n"
            "  /auto weekly Mon HH:MM [count] [flags]\n"
            "  /auto every N [count] [flags]\n"
            "  /auto off"
        ),
        "uz": (
            "Foydalanish:\n"
            "  /auto daily HH:MM [count] [flags]\n"
            "  /auto weekdays HH:MM [count] [flags]\n"
            "  /auto weekly Mon HH:MM [count] [flags]\n"
            "  /auto every N [count] [flags]\n"
            "  /auto off"
        ),
        "de": (
            "Verwendung:\n"
            "  /auto daily HH:MM [count] [flags]\n"
            "  /auto weekdays HH:MM [count] [flags]\n"
            "  /auto weekly Mon HH:MM [count] [flags]\n"
            "  /auto every N [count] [flags]\n"
            "  /auto off"
        ),
        "tr": (
            "Kullanım:\n"
            "  /auto daily HH:MM [count] [flags]\n"
            "  /auto weekdays HH:MM [count] [flags]\n"
            "  /auto weekly Mon HH:MM [count] [flags]\n"
            "  /auto every N [count] [flags]\n"
            "  /auto off"
        ),
    },

    'auto_bad_syntax': {
        "en": (
            "Bad /auto syntax: {err}\n"
            "See /auto on its own for usage."
        ),
        "ru": (
            "Неверный синтаксис /auto: {err}\n"
            "Запустите /auto без параметров для подсказки."
        ),
        "uz": (
            "/auto sintaksisi noto'g'ri: {err}\n"
            "Ko'rsatma uchun /auto ni parametrsiz yuboring."
        ),
        "de": (
            "Falsche /auto Syntax: {err}\n"
            "/auto allein für Hilfe."
        ),
        "tr": (
            "Hatalı /auto sözdizimi: {err}\n"
            "Kullanım için sadece /auto."
        ),
    },

    'auto_enabled_cron': {
        "en": '✅ Auto-scrape: {days} at {hour:02d}:{minute:02d}, {count} articles{flags}',
        "ru": '✅ Авто-сбор: {days} в {hour:02d}:{minute:02d}, {count} статей{flags}',
        "uz": "✅ Avto-yig'ish: {days} {hour:02d}:{minute:02d} da, {count} ta maqola{flags}",
        "de": '✅ Auto-Scrape: {days} um {hour:02d}:{minute:02d}, {count} Artikel{flags}',
        "tr": "✅ Otomatik scrape: {days} {hour:02d}:{minute:02d}'de, {count} makale{flags}",
    },

    'days_every_day': {
        "en": 'every day',
        "ru": 'каждый день',
        "uz": 'har kuni',
        "de": 'täglich',
        "tr": 'her gün',
    },

    'days_weekdays': {
        "en": 'weekdays',
        "ru": 'по будням',
        "uz": 'ish kunlari',
        "de": 'wochentags',
        "tr": 'hafta içi',
    },

    'day_0': {
        "en": 'Mon',
        "ru": 'Пн',
        "uz": 'Du',
        "de": 'Mo',
        "tr": 'Pzt',
    },

    'day_1': {
        "en": 'Tue',
        "ru": 'Вт',
        "uz": 'Se',
        "de": 'Di',
        "tr": 'Sal',
    },

    'day_2': {
        "en": 'Wed',
        "ru": 'Ср',
        "uz": 'Ch',
        "de": 'Mi',
        "tr": 'Çar',
    },

    'day_3': {
        "en": 'Thu',
        "ru": 'Чт',
        "uz": 'Pa',
        "de": 'Do',
        "tr": 'Per',
    },

    'day_4': {
        "en": 'Fri',
        "ru": 'Пт',
        "uz": 'Ju',
        "de": 'Fr',
        "tr": 'Cum',
    },

    'day_5': {
        "en": 'Sat',
        "ru": 'Сб',
        "uz": 'Sh',
        "de": 'Sa',
        "tr": 'Cmt',
    },

    'day_6': {
        "en": 'Sun',
        "ru": 'Вс',
        "uz": 'Ya',
        "de": 'So',
        "tr": 'Paz',
    },

    'sending_combined': {
        "en": 'Sending combined audio...',
        "ru": 'Отправка общего аудио...',
        "uz": 'Umumiy audio yuborilmoqda...',
        "de": 'Sende kombiniertes Audio...',
        "tr": 'Birleşik ses gönderiliyor...',
    },

    'combined_too_large': {
        "en": 'Combined file too large, sending individually...',
        "ru": 'Общий файл слишком большой, отправка по отдельности...',
        "uz": 'Umumiy fayl juda katta, alohida yuborilmoqda...',
        "de": 'Kombinierte Datei zu groß, sende einzeln...',
        "tr": 'Birleşik dosya çok büyük, ayrı ayrı gönderiliyor...',
    },

    'sending_audio': {
        "en": 'Sending audio files...',
        "ru": 'Отправка аудиофайлов...',
        "uz": 'Audio fayllar yuborilmoqda...',
        "de": 'Sende Audiodateien...',
        "tr": 'Ses dosyaları gönderiliyor...',
    },

    'done_sent': {
        "en": 'Done! Sent {parts}.',
        "ru": 'Готово! Отправлено: {parts}.',
        "uz": 'Tayyor! Yuborildi: {parts}.',
        "de": 'Fertig! Gesendet: {parts}.',
        "tr": 'Tamam! Gönderildi: {parts}.',
    },

    'articles_count': {
        "en": '{n} articles',
        "ru": '{n} статей',
        "uz": '{n} ta maqola',
        "de": '{n} Artikel',
        "tr": '{n} makale',
    },

    'images_count': {
        "en": '{n} images',
        "ru": '{n} изображений',
        "uz": '{n} ta rasm',
        "de": '{n} Bilder',
        "tr": '{n} görsel',
    },

    'audio_count': {
        "en": '{n} audio',
        "ru": '{n} аудио',
        "uz": '{n} ta audio',
        "de": '{n} Audio',
        "tr": '{n} ses',
    },

    'posts_range': {
        "en": 'Posts #{oldest} to #{newest}.',
        "ru": 'Посты #{oldest} — #{newest}.',
        "uz": 'Postlar #{oldest} — #{newest}.',
        "de": 'Posts: #{oldest} (älteste) – #{newest} (neueste).',
        "tr": 'Gönderiler: #{oldest} (en eski) – #{newest} (en yeni).',
    },

    'next_batch': {
        "en": 'Next batch: /scrape {start}-{end}',
        "ru": 'Следующая партия: /scrape {start}-{end}',
        "uz": 'Keyingi partiya: /scrape {start}-{end}',
        "de": 'Nächste Charge: /scrape {start}-{end}',
        "tr": 'Sonraki parti: /scrape {start}-{end}',
    },

    'cancelled': {
        "en": 'Job cancelled.',
        "ru": 'Задание отменено.',
        "uz": 'Vazifa bekor qilindi.',
        "de": 'Abgebrochen.',
        "tr": 'İptal edildi.',
    },

    'error': {
        "en": 'Error: {e}',
        "ru": 'Ошибка: {e}',
        "uz": 'Xato: {e}',
        "de": 'Fehler: {e}',
        "tr": 'Hata: {e}',
    },

    'no_job': {
        "en": 'No active job to cancel.',
        "ru": 'Нет активных заданий для отмены.',
        "uz": "Bekor qilish uchun faol vazifa yo'q.",
        "de": 'Kein laufender Vorgang.',
        "tr": 'Çalışan iş yok.',
    },

    'cancelling': {
        "en": 'Cancelling...',
        "ru": 'Отмена...',
        "uz": 'Bekor qilinmoqda...',
        "de": 'Breche ab...',
        "tr": 'İptal ediliyor...',
    },

    'voice_current': {
        "en": (
            "Current voice: {voice}\n"
            "\n"
            "{voice_list}\n"
            "\n"
            "Usage: /voice andrew"
        ),
        "ru": (
            "Текущий голос: {voice}\n"
            "\n"
            "{voice_list}\n"
            "\n"
            "Использование: /voice dmitry"
        ),
        "uz": (
            "Joriy ovoz: {voice}\n"
            "\n"
            "{voice_list}\n"
            "\n"
            "Foydalanish: /voice sardor"
        ),
        "de": (
            "Aktuelle Stimme: {voice}\n"
            "\n"
            "Verfügbar:\n"
            "{voice_list}"
        ),
        "tr": (
            "Mevcut ses: {voice}\n"
            "\n"
            "Kullanılabilir:\n"
            "{voice_list}"
        ),
    },

    'voice_unknown': {
        "en": (
            "Unknown voice '{name}'.\n"
            "\n"
            "{voice_list}"
        ),
        "ru": (
            "Неизвестный голос '{name}'.\n"
            "\n"
            "{voice_list}"
        ),
        "uz": (
            "Noma'lum ovoz '{name}'.\n"
            "\n"
            "{voice_list}"
        ),
        "de": (
            "Unbekannte Stimme: {name}\n"
            "\n"
            "Verfügbar:\n"
            "{voice_list}"
        ),
        "tr": (
            "Bilinmeyen ses: {name}\n"
            "\n"
            "Kullanılabilir:\n"
            "{voice_list}"
        ),
    },

    'voice_set': {
        "en": 'Voice set to: {voice}',
        "ru": 'Голос изменён: {voice}',
        "uz": "Ovoz o'rnatildi: {voice}",
        "de": '✅ Stimme: {voice}',
        "tr": '✅ Ses: {voice}',
    },

    'lang_label_ru': {
        "en": 'Russian',
        "ru": 'Русские',
        "uz": 'Rus',
        "de": 'Russisch',
        "tr": 'Rusça',
    },

    'lang_label_en': {
        "en": 'English',
        "ru": 'Английские',
        "uz": 'Ingliz',
        "de": 'Englisch',
        "tr": 'İngilizce',
    },

    'lang_label_uz': {
        "en": 'Uzbek',
        "ru": 'Узбекские',
        "uz": "O'zbek",
        "de": 'Usbekisch',
        "tr": 'Özbekçe',
    },

    'speed_current': {
        "en": (
            "Current speed: {speed}\n"
            "Presets: {presets}\n"
            "Custom: /speed +30% or /speed -20%\n"
            "Usage: /speed fast"
        ),
        "ru": (
            "Текущая скорость: {speed}\n"
            "Пресеты: {presets}\n"
            "Свои значения: /speed +30% или /speed -20%\n"
            "Использование: /speed fast"
        ),
        "uz": (
            "Joriy tezlik: {speed}\n"
            "Tayyor sozlamalar: {presets}\n"
            "Maxsus: /speed +30% yoki /speed -20%\n"
            "Foydalanish: /speed fast"
        ),
        "de": (
            "Aktuelle Geschwindigkeit: {speed}\n"
            "\n"
            "Voreinstellungen: {presets}\n"
            "Auch eigene: +30%, -20%, etc."
        ),
        "tr": (
            "Mevcut hız: {speed}\n"
            "\n"
            "Ön ayarlar: {presets}\n"
            "Özel de: +30%, -20%, vb."
        ),
    },

    'speed_unknown': {
        "en": (
            "Unknown speed '{name}'.\n"
            "Presets: {presets}\n"
            "Or use custom: +30%, -20%, etc."
        ),
        "ru": (
            "Неизвестная скорость '{name}'.\n"
            "Пресеты: {presets}\n"
            "Или свои: +30%, -20% и т.д."
        ),
        "uz": (
            "Noma'lum tezlik '{name}'.\n"
            "Tayyor sozlamalar: {presets}\n"
            "Yoki maxsus: +30%, -20%, va h.k."
        ),
        "de": (
            "Unbekannt: {name}\n"
            "\n"
            "Voreinstellungen: {presets}\n"
            "Oder z.B.: +30%, -20%"
        ),
        "tr": (
            "Bilinmiyor: {name}\n"
            "\n"
            "Ön ayarlar: {presets}\n"
            "Veya örn.: +30%, -20%"
        ),
    },

    'speed_set': {
        "en": 'Speed set to: {speed}',
        "ru": 'Скорость изменена: {speed}',
        "uz": "Tezlik o'rnatildi: {speed}",
        "de": '✅ Geschwindigkeit: {speed}',
        "tr": '✅ Hız: {speed}',
    },

    'channel_current': {
        "en": (
            "Current channel: {url}\n"
            "\n"
            "To change: /channel https://t.me/s/channel_name"
        ),
        "ru": (
            "Текущий канал: {url}\n"
            "\n"
            "Изменить: /channel https://t.me/s/channel_name"
        ),
        "uz": (
            "Joriy kanal: {url}\n"
            "\n"
            "O'zgartirish: /channel https://t.me/s/channel_name"
        ),
        "de": 'Aktueller Kanal: {url}',
        "tr": 'Mevcut kanal: {url}',
    },

    'channel_invalid': {
        "en": (
            "URL must start with https://t.me/s/\n"
            "Example: /channel https://t.me/s/spotuz"
        ),
        "ru": (
            "URL должен начинаться с https://t.me/s/\n"
            "Пример: /channel https://t.me/s/spotuz"
        ),
        "uz": (
            "URL https://t.me/s/ bilan boshlanishi kerak\n"
            "Misol: /channel https://t.me/s/spotuz"
        ),
        "de": 'URL muss mit https://t.me/s/ beginnen',
        "tr": 'URL https://t.me/s/ ile başlamalı',
    },

    'channel_set': {
        "en": 'Channel set to: {url}',
        "ru": 'Канал изменён: {url}',
        "uz": "Kanal o'rnatildi: {url}",
        "de": '✅ Kanal: {url}',
        "tr": '✅ Kanal: {url}',
    },

    'status': {
        "en": (
            "Channel: {channel}\n"
            "Voice: {voice}\n"
            "Speed: {speed}\n"
            "Language: {language}\n"
            "Auto-scrape: {auto}\n"
            "Active job: {job}\n"
            "Default count: {default_count}\n"
            "Max count: {max_count}\n"
            "Max offset: {max_offset}"
        ),
        "ru": (
            "Канал: {channel}\n"
            "Голос: {voice}\n"
            "Скорость: {speed}\n"
            "Язык: {language}\n"
            "Авто-скрапинг: {auto}\n"
            "Активная задача: {job}\n"
            "По умолчанию: {default_count}\n"
            "Максимум: {max_count}\n"
            "Макс. смещение: {max_offset}"
        ),
        "uz": (
            "Kanal: {channel}\n"
            "Ovoz: {voice}\n"
            "Tezlik: {speed}\n"
            "Til: {language}\n"
            "Avto-skraping: {auto}\n"
            "Faol vazifa: {job}\n"
            "Standart son: {default_count}\n"
            "Maksimum: {max_count}\n"
            "Maks. siljish: {max_offset}"
        ),
        "de": (
            "📊 Status\n"
            "\n"
            "Kanal: {channel}\n"
            "Stimme: {voice}\n"
            "Geschwindigkeit: {speed}\n"
            "Sprache: {language}\n"
            "Auto-Scrape: {auto}\n"
            "Laufender Job: {job}\n"
            "\n"
            "Standardanzahl: {default_count}, Max: {max_count}\n"
            "Max-Versatz: {max_offset}"
        ),
        "tr": (
            "📊 Durum\n"
            "\n"
            "Kanal: {channel}\n"
            "Ses: {voice}\n"
            "Hız: {speed}\n"
            "Dil: {language}\n"
            "Otomatik scrape: {auto}\n"
            "Çalışan iş: {job}\n"
            "\n"
            "Varsayılan sayı: {default_count}, En fazla: {max_count}\n"
            "Maks kayma: {max_offset}"
        ),
    },

    'status_yes': {
        "en": 'Yes',
        "ru": 'Да',
        "uz": 'Ha',
        "de": 'Ja',
        "tr": 'Evet',
    },

    'status_no': {
        "en": 'No',
        "ru": 'Нет',
        "uz": "Yo'q",
        "de": 'Nein',
        "tr": 'Hayır',
    },

    'status_off': {
        "en": 'Off',
        "ru": 'Выключен',
        "uz": "O'chirilgan",
        "de": 'Aus',
        "tr": 'Kapalı',
    },

    'auto_status_on': {
        "en": 'Every {days}d, {count} articles',
        "ru": 'Каждые {days} дн., {count} статей',
        "uz": 'Har {days} kunda, {count} ta maqola',
        "de": 'An, alle {days} Tag(e), {count} Artikel',
        "tr": 'Açık, her {days} gün, {count} makale',
    },

    'auto_show_off': {
        "en": (
            "Auto-scrape: Off\n"
            "\n"
            "Usage:\n"
            "/auto on 3 — Enable every 3 days\n"
            "/auto 50 audio combined — Set options\n"
            "/auto off — Disable"
        ),
        "ru": (
            "Авто-скрапинг: Выключен\n"
            "\n"
            "Использование:\n"
            "/auto on 3 — Включить каждые 3 дня\n"
            "/auto 50 audio combined — Настроить\n"
            "/auto off — Отключить"
        ),
        "uz": (
            "Avto-skraping: O'chirilgan\n"
            "\n"
            "Foydalanish:\n"
            "/auto on 3 — Har 3 kunda yoqish\n"
            "/auto 50 audio combined — Sozlash\n"
            "/auto off — O'chirish"
        ),
        "de": 'Auto-Scrape ist AUS.',
        "tr": 'Otomatik scrape KAPALI.',
    },

    'auto_show_on': {
        "en": 'Auto-scrape: Every {days} day(s), {count} articles{flags}',
        "ru": 'Авто-скрапинг: Каждые {days} дн., {count} статей{flags}',
        "uz": 'Avto-skraping: Har {days} kunda, {count} ta maqola{flags}',
        "de": 'Auto-Scrape AN: alle {days} Tag(e), {count} Artikel{flags}',
        "tr": 'Otomatik scrape AÇIK: her {days} günde, {count} makale{flags}',
    },

    'auto_disabled': {
        "en": 'Auto-scrape disabled.',
        "ru": 'Авто-скрапинг отключён.',
        "uz": "Avto-skraping o'chirildi.",
        "de": '✅ Auto-Scrape deaktiviert.',
        "tr": '✅ Otomatik scrape devre dışı.',
    },

    'auto_enabled': {
        "en": 'Auto-scrape enabled: every {days} day(s), {count} articles{flags}.',
        "ru": 'Авто-скрапинг включён: каждые {days} дн., {count} статей{flags}.',
        "uz": 'Avto-skraping yoqildi: har {days} kunda, {count} ta maqola{flags}.',
        "de": '✅ Auto-Scrape: alle {days} Tag(e), {count} Artikel{flags}',
        "tr": '✅ Otomatik scrape: her {days} günde, {count} makale{flags}',
    },

    'auto_interval_invalid': {
        "en": 'Interval must be {min}-{max} days.',
        "ru": 'Интервал должен быть {min}-{max} дней.',
        "uz": "Interval {min}-{max} kun bo'lishi kerak.",
        "de": 'Intervall muss zwischen {min} und {max} Tagen liegen.',
        "tr": 'Aralık {min} ile {max} gün arasında olmalı.',
    },

    'auto_skipped': {
        "en": 'Auto-scrape skipped: a job is already running.',
        "ru": 'Авто-скрапинг пропущен: задание уже выполняется.',
        "uz": "Avto-skraping o'tkazib yuborildi: vazifa allaqachon bajarilmoqda.",
        "de": 'Auto-Scrape übersprungen — ein Job läuft bereits.',
        "tr": 'Otomatik scrape atlandı — bir iş çalışıyor.',
    },

    'auto_starting': {
        "en": 'Auto-scrape starting...',
        "ru": 'Авто-скрапинг запускается...',
        "uz": 'Avto-skraping boshlanmoqda...',
        "de": '🤖 Auto-Scrape startet...',
        "tr": '🤖 Otomatik scrape başlıyor...',
    },

    'lang_current': {
        "en": (
            "Current language: English\n"
            "\n"
            "Available:\n"
            "/lang en — English\n"
            "/lang ru — Русский\n"
            "/lang uz — O'zbek"
        ),
        "ru": (
            "Текущий язык: Русский\n"
            "\n"
            "Доступные:\n"
            "/lang en — English\n"
            "/lang ru — Русский\n"
            "/lang uz — O'zbek"
        ),
        "uz": (
            "Joriy til: O'zbek\n"
            "\n"
            "Mavjud:\n"
            "/lang en — English\n"
            "/lang ru — Русский\n"
            "/lang uz — O'zbek"
        ),
        "de": 'Sprache wählen: en, ru, uz, de, tr',
        "tr": 'Dil seç: en, ru, uz, de, tr',
    },

    'lang_unknown': {
        "en": "Unknown language '{code}'. Available: en, ru, uz",
        "ru": "Неизвестный язык '{code}'. Доступные: en, ru, uz",
        "uz": "Noma'lum til '{code}'. Mavjud: en, ru, uz",
        "de": 'Unbekannte Sprache: {code}. Verfügbar: en, ru, uz, de, tr',
        "tr": 'Bilinmeyen dil: {code}. Kullanılabilir: en, ru, uz, de, tr',
    },

    'lang_set': {
        "en": 'Language set to: English',
        "ru": 'Язык изменён: Русский',
        "uz": "Til o'rnatildi: O'zbek",
        "de": '✅ Sprache geändert.',
        "tr": '✅ Dil değiştirildi.',
    },

    'order_current': {
        "en": (
            "Current order: {order}\n"
            "\n"
            "Usage:\n"
            "/order newest — Newest articles first (default)\n"
            "/order oldest — Oldest articles first (chronological reading)\n"
            "\n"
            "One-off override on /scrape: add 'oldest' or 'newest' as a flag."
        ),
        "ru": (
            "Текущий порядок: {order}\n"
            "\n"
            "Использование:\n"
            "/order newest — Сначала новые (по умолчанию)\n"
            "/order oldest — Сначала старые (хронологическое чтение)\n"
            "\n"
            "Разовое переопределение для /scrape: добавьте флаг 'oldest' или 'newest'."
        ),
        "uz": (
            "Joriy tartib: {order}\n"
            "\n"
            "Foydalanish:\n"
            "/order newest — Avval yangilari (standart)\n"
            "/order oldest — Avval eskilari (xronologik o'qish)\n"
            "\n"
            "/scrape uchun bir martalik o'zgartirish: 'oldest' yoki 'newest' bayrog'ini qo'shing."
        ),
        "de": 'Reihenfolge: {order}',
        "tr": 'Sıra: {order}',
    },

    'order_unknown': {
        "en": "Unknown order '{name}'. Use 'newest' or 'oldest'.",
        "ru": "Неизвестный порядок '{name}'. Используйте 'newest' или 'oldest'.",
        "uz": "Noma'lum tartib '{name}'. 'newest' yoki 'oldest' ishlating.",
        "de": "Unbekannt: {name}. Nutze 'newest' oder 'oldest'.",
        "tr": "Bilinmiyor: {name}. 'newest' veya 'oldest' kullan.",
    },

    'order_set': {
        "en": 'Order set to: {order}',
        "ru": 'Порядок изменён: {order}',
        "uz": "Tartib o'rnatildi: {order}",
        "de": '✅ Reihenfolge: {order}',
        "tr": '✅ Sıra: {order}',
    },

    'announcement_prefix': {
        "en": 'Next article:',
        "ru": 'Следующая статья:',
        "uz": 'Keyingi maqola:',
        "de": 'Nächster Artikel:',
        "tr": 'Sonraki makale:',
    },

    # ===== Phase 15 redesign: identity, help, delivery card =====

    'bot_short_description': {
        "en": "Free, multilingual news bot. Read or listen to Spot.uz, Telegram channels, and RSS feeds. Auto-translation, summaries, voice messages.",
        "ru": "Бесплатный многоязычный новостной бот. Читайте и слушайте Spot.uz, Telegram-каналы и RSS. Авто-перевод, резюме, голосовые.",
        "uz": "Bepul, ko'p tilli yangiliklar boti. Spot.uz, Telegram va RSS dan o'qing yoki tinglang. Avto-tarjima, xulosalar, ovozli xabarlar.",
        "de": "Kostenloser, mehrsprachiger News-Bot. Spot.uz, Telegram-Kanäle, RSS-Feeds — lesen oder hören. Auto-Übersetzung, Zusammenfassungen, Sprachnachrichten.",
        "tr": "Ücretsiz, çok dilli haber botu. Spot.uz, Telegram kanalları ve RSS — oku veya dinle. Otomatik çeviri, özetler, sesli mesajlar.",
    },
    'bot_long_description': {
        "en": (
            "Tez News Bot — a free, multilingual news companion.\n\n"
            "Read or listen to articles from Spot.uz, public Telegram channels, "
            "and any RSS feed. Bot auto-translates between Russian, Uzbek, "
            "English, German, and Turkish, generates voice messages with mobile "
            "speed control, and writes 2-3-sentence LLM summaries. Free forever — "
            "no ads, no tracking, open source.\n\n"
            "Run /start to begin or /help for the full guide."
        ),
        "ru": (
            "Tez News Bot — бесплатный многоязычный новостной помощник.\n\n"
            "Читайте или слушайте статьи из Spot.uz, публичных Telegram-каналов "
            "и любых RSS-лент. Авто-перевод между русским, узбекским, английским, "
            "немецким и турецким, голосовые сообщения с регулировкой скорости "
            "на мобильном, LLM-резюме на 2-3 предложения. Бесплатно навсегда — "
            "без рекламы и трекинга, открытый код.\n\n"
            "Начните с /start или /help для полного руководства."
        ),
        "uz": (
            "Tez News Bot — bepul, ko'p tilli yangiliklar yordamchisi.\n\n"
            "Spot.uz, ochiq Telegram kanallar va istalgan RSS lentadan maqolalarni "
            "o'qing yoki tinglang. Rus, o'zbek, ingliz, nemis va turk tillari "
            "o'rtasida avto-tarjima, mobil tezlik boshqaruvi bilan ovozli xabarlar, "
            "2-3 jumlali LLM xulosalari. Doimo bepul — reklama va kuzatuvsiz, ochiq kodli.\n\n"
            "Boshlash uchun /start, to'liq qo'llanma uchun /help."
        ),
        "de": (
            "Tez News Bot — ein kostenloser, mehrsprachiger News-Begleiter.\n\n"
            "Lese oder höre Artikel von Spot.uz, öffentlichen Telegram-Kanälen "
            "und beliebigen RSS-Feeds. Auto-Übersetzung zwischen Russisch, "
            "Usbekisch, Englisch, Deutsch und Türkisch, Sprachnachrichten mit "
            "mobiler Geschwindigkeitssteuerung, 2-3-Satz-LLM-Zusammenfassungen. "
            "Für immer kostenlos — keine Werbung, kein Tracking, Open Source.\n\n"
            "Starte mit /start oder /help für die ganze Anleitung."
        ),
        "tr": (
            "Tez News Bot — ücretsiz, çok dilli haber asistanı.\n\n"
            "Spot.uz, açık Telegram kanalları ve herhangi bir RSS akışından "
            "makaleleri oku ya da dinle. Rusça, Özbekçe, İngilizce, Almanca ve "
            "Türkçe arası otomatik çeviri, mobilde hız kontrollü sesli mesajlar, "
            "2-3 cümlelik LLM özetleri. Sonsuza kadar ücretsiz — reklamsız, "
            "izlemesiz, açık kaynak.\n\n"
            "Başlamak için /start veya tam rehber için /help."
        ),
    },

    # /start welcome
    'start_welcome': {
        "en": (
            "👋 Welcome to Tez News Bot\n\n"
            "Your free, multilingual news companion. Read or listen to articles "
            "from Spot.uz, Telegram channels, and RSS feeds — in 5 languages.\n\n"
            "🚀 Quick start\n\n"
            "  /scrape 5 audio  → 5 latest articles + voice messages\n"
            "  /today           → today's news\n"
            "  /sources         → your news sources\n\n"
            "Tap below for the full guide."
        ),
        "ru": (
            "👋 Добро пожаловать в Tez News Bot\n\n"
            "Ваш бесплатный многоязычный новостной помощник. Читайте или слушайте "
            "статьи из Spot.uz, Telegram-каналов и RSS — на 5 языках.\n\n"
            "🚀 Быстрый старт\n\n"
            "  /scrape 5 audio  → 5 последних + голосовые\n"
            "  /today           → новости за сегодня\n"
            "  /sources         → ваши источники\n\n"
            "Полное руководство — кнопка ниже."
        ),
        "uz": (
            "👋 Tez News Bot ga xush kelibsiz\n\n"
            "Sizning bepul, ko'p tilli yangiliklar yordamchingiz. Spot.uz, Telegram "
            "kanallar va RSS dan maqolalarni 5 tilda o'qing yoki tinglang.\n\n"
            "🚀 Tez boshlash\n\n"
            "  /scrape 5 audio  → so'nggi 5 ta + ovozli xabarlar\n"
            "  /today           → bugungi yangiliklar\n"
            "  /sources         → sizning manbalaringiz\n\n"
            "To'liq qo'llanma uchun pastdagi tugmani bosing."
        ),
        "de": (
            "👋 Willkommen beim Tez News Bot\n\n"
            "Dein kostenloser, mehrsprachiger News-Begleiter. Lese oder höre "
            "Artikel von Spot.uz, Telegram-Kanälen und RSS-Feeds — in 5 Sprachen.\n\n"
            "🚀 Schnellstart\n\n"
            "  /scrape 5 audio  → 5 neueste + Sprachnachrichten\n"
            "  /today           → heutige Nachrichten\n"
            "  /sources         → deine Quellen\n\n"
            "Tippe unten für die ganze Anleitung."
        ),
        "tr": (
            "👋 Tez News Bot'a hoş geldin\n\n"
            "Ücretsiz, çok dilli haber asistanın. Spot.uz, Telegram kanalları ve "
            "RSS akışlarından makaleleri 5 dilde oku ya da dinle.\n\n"
            "🚀 Hızlı başlangıç\n\n"
            "  /scrape 5 audio  → son 5 + sesli mesajlar\n"
            "  /today           → bugünün haberleri\n"
            "  /sources         → kaynakların\n\n"
            "Tam rehber için aşağıdaki düğme."
        ),
    },

    'btn_full_help': {
        "en": "📚 Full help",
        "ru": "📚 Полное руководство",
        "uz": "📚 To'liq qo'llanma",
        "de": "📚 Komplette Anleitung",
        "tr": "📚 Tam rehber",
    },
    'btn_about': {
        "en": "🆘 About",
        "ru": "🆘 О боте",
        "uz": "🆘 Bot haqida",
        "de": "🆘 Über",
        "tr": "🆘 Hakkında",
    },
    'btn_back_to_help': {
        "en": "← Back to help",
        "ru": "← К меню помощи",
        "uz": "← Yordam menyusiga",
        "de": "← Zurück zur Hilfe",
        "tr": "← Yardıma dön",
    },

    # Help index
    'help_index': {
        "en": (
            "📚 Tez News Bot — Help\n\n"
            "Choose a topic below or type /help_<topic>:\n\n"
            "📡 scrape — Scrape news from your sources\n"
            "🤖 auto — Schedule recurring deliveries\n"
            "🎙️ audio — Voice messages, engines, voices, speed\n"
            "🔍 filter — Quality, topics, duplicates, ads\n"
            "📚 library — Bookmarks, search, stats, resume\n"
            "🌐 languages — UI, translation, sources, summaries"
        ),
        "ru": (
            "📚 Tez News Bot — Помощь\n\n"
            "Выберите тему ниже или введите /help_<тема>:\n\n"
            "📡 scrape — Сбор новостей из источников\n"
            "🤖 auto — Расписание повторных сборов\n"
            "🎙️ audio — Голосовые, движки, голоса, скорость\n"
            "🔍 filter — Качество, темы, дубли, реклама\n"
            "📚 library — Закладки, поиск, статистика, возврат\n"
            "🌐 languages — UI, перевод, источники, резюме"
        ),
        "uz": (
            "📚 Tez News Bot — Yordam\n\n"
            "Quyidagi mavzuni tanlang yoki /help_<mavzu> ni yozing:\n\n"
            "📡 scrape — Manbalardan yangiliklarni yig'ish\n"
            "🤖 auto — Takroriy yetkazib berishni rejalashtirish\n"
            "🎙️ audio — Ovozli xabarlar, ovozlar, tezlik\n"
            "🔍 filter — Sifat, mavzu, takrorlar, reklama\n"
            "📚 library — Xatcho'plar, qidiruv, statistika, davom etish\n"
            "🌐 languages — UI, tarjima, manbalar, xulosalar"
        ),
        "de": (
            "📚 Tez News Bot — Hilfe\n\n"
            "Wähle ein Thema unten oder tippe /help_<thema>:\n\n"
            "📡 scrape — Nachrichten von deinen Quellen abrufen\n"
            "🤖 auto — Wiederkehrende Lieferungen planen\n"
            "🎙️ audio — Sprachnachrichten, Engines, Stimmen, Tempo\n"
            "🔍 filter — Qualität, Themen, Duplikate, Werbung\n"
            "📚 library — Lesezeichen, Suche, Statistik, Fortsetzen\n"
            "🌐 languages — UI, Übersetzung, Quellen, Zusammenfassungen"
        ),
        "tr": (
            "📚 Tez News Bot — Yardım\n\n"
            "Aşağıdan bir konu seç veya /help_<konu> yaz:\n\n"
            "📡 scrape — Kaynaklardan haber çek\n"
            "🤖 auto — Yinelenen teslimatları zamanla\n"
            "🎙️ audio — Sesli mesajlar, motorlar, sesler, hız\n"
            "🔍 filter — Kalite, konu, tekrar, reklam\n"
            "📚 library — Yer imleri, arama, istatistik, devam\n"
            "🌐 languages — UI, çeviri, kaynaklar, özetler"
        ),
    },
    'help_btn_scrape': {
        "en": "📡 scrape", "ru": "📡 scrape", "uz": "📡 scrape",
        "de": "📡 scrape", "tr": "📡 scrape",
    },
    'help_btn_auto': {
        "en": "🤖 auto", "ru": "🤖 auto", "uz": "🤖 auto",
        "de": "🤖 auto", "tr": "🤖 auto",
    },
    'help_btn_audio': {
        "en": "🎙️ audio", "ru": "🎙️ audio", "uz": "🎙️ audio",
        "de": "🎙️ audio", "tr": "🎙️ audio",
    },
    'help_btn_filter': {
        "en": "🔍 filter", "ru": "🔍 filter", "uz": "🔍 filter",
        "de": "🔍 filter", "tr": "🔍 filter",
    },
    'help_btn_library': {
        "en": "📚 library", "ru": "📚 library", "uz": "📚 library",
        "de": "📚 library", "tr": "📚 library",
    },
    'help_btn_languages': {
        "en": "🌐 languages", "ru": "🌐 languages", "uz": "🌐 languages",
        "de": "🌐 languages", "tr": "🌐 languages",
    },

    # /help_scrape
    'help_scrape': {
        "en": (
            "📡 Scrape — Get news from your sources\n\n"
            "By count\n"
            "  /scrape 50 — 50 latest as .txt file\n"
            "  /scrape 50 inline — 50 as separate messages\n"
            "  /scrape 50 audio — 50 + individual voice messages\n"
            "  /scrape 50 audio combined — 50 + one combined voice (split at 1h)\n"
            "  /scrape 50 images — 50 + image albums per article\n\n"
            "By date\n"
            "  /today, /yesterday, /thisweek\n"
            "  /since 2026-05-01 — from a specific date\n\n"
            "By post ID\n"
            "  /scrape 35808-35758 — exact ID range\n"
            "  /scrape 2000-1950 — by offset from latest\n\n"
            "By title\n"
            '  /scrape from "metro" 50 — search, then scrape forward\n\n'
            "Translate per scrape\n"
            "  /scrape 50 audio translate=de — translate to German before TTS\n\n"
            "💡 Combine flags freely. Try:\n"
            "  /scrape 5 inline images audio translate=tr"
        ),
        "ru": (
            "📡 Сбор — Новости из ваших источников\n\n"
            "По количеству\n"
            "  /scrape 50 — 50 последних как .txt\n"
            "  /scrape 50 inline — 50 отдельными сообщениями\n"
            "  /scrape 50 audio — 50 + отдельные голосовые\n"
            "  /scrape 50 audio combined — 50 + общий голос (по 1ч)\n"
            "  /scrape 50 images — 50 + альбомы изображений\n\n"
            "По дате\n"
            "  /today, /yesterday, /thisweek\n"
            "  /since 2026-05-01 — с указанной даты\n\n"
            "По ID поста\n"
            "  /scrape 35808-35758 — точный диапазон ID\n"
            "  /scrape 2000-1950 — по смещению от последнего\n\n"
            "По заголовку\n"
            '  /scrape from "metro" 50 — поиск, затем сбор вперёд\n\n'
            "Перевод разово\n"
            "  /scrape 50 audio translate=de — перевести на немецкий перед озвучкой\n\n"
            "💡 Флаги комбинируются. Попробуйте:\n"
            "  /scrape 5 inline images audio translate=tr"
        ),
        "uz": (
            "📡 Yig'ish — Manbalardan yangiliklar\n\n"
            "Soni bo'yicha\n"
            "  /scrape 50 — so'nggi 50 ta .txt\n"
            "  /scrape 50 inline — 50 ta alohida xabar\n"
            "  /scrape 50 audio — 50 + alohida ovozli\n"
            "  /scrape 50 audio combined — 50 + umumiy ovoz (1 soat)\n"
            "  /scrape 50 images — 50 + rasm albomlari\n\n"
            "Sana bo'yicha\n"
            "  /today, /yesterday, /thisweek\n"
            "  /since 2026-05-01 — ma'lum sanadan\n\n"
            "Post ID bo'yicha\n"
            "  /scrape 35808-35758 — aniq ID oralig'i\n"
            "  /scrape 2000-1950 — so'nggidan siljish bo'yicha\n\n"
            "Sarlavha bo'yicha\n"
            '  /scrape from "metro" 50 — qidirish va oldinga\n\n'
            "Bir martalik tarjima\n"
            "  /scrape 50 audio translate=de — TTS oldidan nemis tiliga\n\n"
            "💡 Bayroqlarni birlashtiring:\n"
            "  /scrape 5 inline images audio translate=tr"
        ),
        "de": (
            "📡 Scrape — Nachrichten von deinen Quellen\n\n"
            "Nach Anzahl\n"
            "  /scrape 50 — die 50 neuesten als .txt\n"
            "  /scrape 50 inline — 50 als einzelne Nachrichten\n"
            "  /scrape 50 audio — 50 + einzelne Sprachnachrichten\n"
            "  /scrape 50 audio combined — 50 + kombinierte Sprache (geteilt bei 1h)\n"
            "  /scrape 50 images — 50 + Bilderalben pro Artikel\n\n"
            "Nach Datum\n"
            "  /today, /yesterday, /thisweek\n"
            "  /since 2026-05-01 — ab einem Datum\n\n"
            "Nach Post-ID\n"
            "  /scrape 35808-35758 — exakter ID-Bereich\n"
            "  /scrape 2000-1950 — nach Versatz vom neuesten\n\n"
            "Nach Titel\n"
            '  /scrape from "metro" 50 — suchen, dann vorwärts\n\n'
            "Pro Scrape übersetzen\n"
            "  /scrape 50 audio translate=de — vor TTS auf Deutsch\n\n"
            "💡 Flags frei kombinieren. Probier:\n"
            "  /scrape 5 inline images audio translate=tr"
        ),
        "tr": (
            "📡 Scrape — Kaynaklardan haber\n\n"
            "Sayıya göre\n"
            "  /scrape 50 — son 50 .txt olarak\n"
            "  /scrape 50 inline — 50 ayrı mesaj\n"
            "  /scrape 50 audio — 50 + ayrı sesli mesajlar\n"
            "  /scrape 50 audio combined — 50 + birleşik ses (1s'de bölünür)\n"
            "  /scrape 50 images — 50 + makale başına görsel albüm\n\n"
            "Tarihe göre\n"
            "  /today, /yesterday, /thisweek\n"
            "  /since 2026-05-01 — belirli tarihten\n\n"
            "Post ID'ye göre\n"
            "  /scrape 35808-35758 — tam ID aralığı\n"
            "  /scrape 2000-1950 — sondan kayma\n\n"
            "Başlığa göre\n"
            '  /scrape from "metro" 50 — ara, sonra ileri\n\n'
            "Tek seferlik çeviri\n"
            "  /scrape 50 audio translate=de — TTS öncesi Almancaya\n\n"
            "💡 Bayrakları birleştir:\n"
            "  /scrape 5 inline images audio translate=tr"
        ),
    },

    # /help_auto
    'help_auto': {
        "en": (
            "🤖 Auto — Recurring scheduled scrapes\n\n"
            "Daily at a fixed time\n"
            "  /auto daily 08:00 50 audio combined\n\n"
            "Weekdays only\n"
            "  /auto weekdays 08:00 50 audio\n\n"
            "Once a week\n"
            "  /auto weekly Mon 08:00 50 audio\n\n"
            "Every N days (interval)\n"
            "  /auto every 3 50 audio combined\n\n"
            "Disable\n"
            "  /auto off\n\n"
            "Show current\n"
            "  /auto\n\n"
            "💡 Times use Asia/Tashkent (UTC+5)."
        ),
    },

    # /help_audio
    'help_audio': {
        "en": (
            "🎙️ Audio — Voice messages and TTS\n\n"
            "Engines\n"
            "  /voice_engine edge — Microsoft Edge TTS (default, online, free)\n"
            "  /voice_engine supertonic — Open ONNX, RU/EN/+28; Uzbek auto-routes to Edge\n"
            "  /voice_engine piper — Local Piper (requires model files)\n\n"
            "Voices (Edge TTS)\n"
            "  /voice — list all available\n"
            "  /voice andrew — set global voice\n"
            "  /voice de katja — per-language voice (auto-picked by article language)\n\n"
            "Speed\n"
            "  /speed normal | fast | faster | fastest\n"
            "  /speed +30% — custom rate\n\n"
            "Modes\n"
            "  /scrape 5 audio — one voice per article\n"
            "  /scrape 5 audio combined — merged voice (split at 1h)\n\n"
            "💡 Combined voice messages get a chapter list with timestamps so "
            "you can scrub to a specific article."
        ),
    },

    # /help_filter
    'help_filter': {
        "en": (
            "🔍 Filter — Trim what reaches you\n\n"
            "Quality (skip short stubs)\n"
            "  /quality 200 — drop articles under 200 chars\n"
            "  /quality 0 — disable\n\n"
            "Topics (keyword filter)\n"
            "  /topics economy tech — only deliver matching\n"
            "  /topics off\n\n"
            "Duplicates (multi-source)\n"
            "  /dedup 85 — collapse titles ≥85% similar\n"
            "  /dedup 100 — disable\n\n"
            "Ads\n"
            "  /ads on — keep promotional content\n"
            "  /ads off — strip ad markers (default)\n\n"
            "Order\n"
            "  /order newest — newest first (default)\n"
            "  /order oldest — oldest first"
        ),
    },

    # /help_library
    'help_library': {
        "en": (
            "📚 Library — Track, save, find\n\n"
            "Stats\n"
            "  /stats — reading totals (week + all-time)\n\n"
            "Find anything you've received\n"
            "  /find metro — search past articles\n"
            "  /unread — count new since last scrape\n\n"
            "Save articles for later\n"
            "  /bookmark 35808 economy — save with optional tags\n"
            "  /bookmarks — list saved\n"
            "  /bookmarks economy — filter by tag\n"
            "  /unbookmark 35808\n\n"
            "Resume long voice messages\n"
            "  Tap 📍 Mark here under a voice message\n"
            "  /resume — jump to it later"
        ),
    },

    # /help_languages
    'help_languages': {
        "en": (
            "🌐 Languages — Multi-language listening\n\n"
            "Bot UI\n"
            "  /lang en | ru | uz | de | tr\n\n"
            "Article translation (read RU news in DE/TR)\n"
            "  /translate de — all articles to German before TTS\n"
            "  /translate tr — all to Turkish\n"
            "  /translate off — original language\n"
            "  Per scrape: /scrape 50 audio translate=de\n\n"
            "News sources (mix any languages)\n"
            "  /sources — list configured\n"
            "  /addsource rss <url> [name]\n"
            "  /addsource telegram <https://t.me/s/...> [name]\n"
            "  /removesource <id>\n\n"
            "LLM summaries (Groq free tier)\n"
            "  /summarize on — 2-3 sentence summary on top of each article\n"
            "  /summarize off"
        ),
    },

    # /about
    'about_body': {
        "en": (
            "🆘 Tez News Bot\n\n"
            "A free, open-source, multilingual news companion.\n\n"
            "Built with\n"
            "• python-telegram-bot — Telegram integration\n"
            "• httpx + selectolax — scraping (replaced Playwright)\n"
            "• Edge TTS / Supertonic-3 / Piper — speech synthesis\n"
            "• Groq (free Llama tier) — translation + summaries\n"
            "• ffmpeg — audio processing\n"
            "• SQLite — history + bookmarks + translation cache\n\n"
            "Free forever within free-tier API quotas. No ads, no tracking.\n\n"
            "Source on GitHub. Run /help for the full guide."
        ),
        "ru": (
            "🆘 Tez News Bot\n\n"
            "Бесплатный, многоязычный новостной помощник с открытым кодом.\n\n"
            "На основе\n"
            "• python-telegram-bot — интеграция с Telegram\n"
            "• httpx + selectolax — скрапинг (вместо Playwright)\n"
            "• Edge TTS / Supertonic-3 / Piper — синтез речи\n"
            "• Groq (free Llama) — перевод + резюме\n"
            "• ffmpeg — обработка аудио\n"
            "• SQLite — история + закладки + кэш перевода\n\n"
            "Бесплатно навсегда в пределах free-tier API. Без рекламы и трекинга.\n\n"
            "Исходники на GitHub. /help — полное руководство."
        ),
        "uz": (
            "🆘 Tez News Bot\n\n"
            "Bepul, ochiq kodli, ko'p tilli yangiliklar yordamchisi.\n\n"
            "Asoslari\n"
            "• python-telegram-bot — Telegram integratsiyasi\n"
            "• httpx + selectolax — skraping (Playwright o'rniga)\n"
            "• Edge TTS / Supertonic-3 / Piper — nutq sintezi\n"
            "• Groq (bepul Llama) — tarjima + xulosalar\n"
            "• ffmpeg — audio qayta ishlash\n"
            "• SQLite — tarix + xatcho'plar + tarjima keshi\n\n"
            "Free-tier API doirasida doimo bepul. Reklama va kuzatuvsiz.\n\n"
            "Manba kodi GitHub da. To'liq qo'llanma — /help."
        ),
        "de": (
            "🆘 Tez News Bot\n\n"
            "Ein kostenloser, mehrsprachiger Open-Source-News-Begleiter.\n\n"
            "Gebaut mit\n"
            "• python-telegram-bot — Telegram-Integration\n"
            "• httpx + selectolax — Scraping (statt Playwright)\n"
            "• Edge TTS / Supertonic-3 / Piper — Sprachsynthese\n"
            "• Groq (kostenlose Llama-Stufe) — Übersetzung + Zusammenfassungen\n"
            "• ffmpeg — Audioverarbeitung\n"
            "• SQLite — Verlauf + Lesezeichen + Übersetzungscache\n\n"
            "Für immer kostenlos innerhalb der Free-Tier-API-Limits. Werbefrei.\n\n"
            "Quellcode auf GitHub. /help für die ganze Anleitung."
        ),
        "tr": (
            "🆘 Tez News Bot\n\n"
            "Ücretsiz, açık kaynaklı, çok dilli haber asistanı.\n\n"
            "Bileşenler\n"
            "• python-telegram-bot — Telegram entegrasyonu\n"
            "• httpx + selectolax — kazıma (Playwright yerine)\n"
            "• Edge TTS / Supertonic-3 / Piper — konuşma sentezi\n"
            "• Groq (ücretsiz Llama) — çeviri + özetler\n"
            "• ffmpeg — ses işleme\n"
            "• SQLite — geçmiş + yer imleri + çeviri önbelleği\n\n"
            "Ücretsiz API kotaları dahilinde sonsuza kadar bedava. Reklamsız.\n\n"
            "Kaynak GitHub'da. Tam rehber için /help."
        ),
    },

    # Command-menu (the / autocomplete) labels — short and clear
    'cmdmenu_start': {
        "en": "Welcome and quick start",
        "ru": "Приветствие и быстрый старт",
        "uz": "Salomlashuv va tez boshlash",
        "de": "Willkommen und Schnellstart",
        "tr": "Karşılama ve hızlı başlangıç",
    },
    'cmdmenu_scrape': {
        "en": "Scrape news (50, range, by title)",
        "ru": "Сбор новостей (50, диапазон, по заголовку)",
        "uz": "Yangiliklarni yig'ish (50, oraliq, sarlavha bo'yicha)",
        "de": "News abrufen (50, Bereich, nach Titel)",
        "tr": "Haber çek (50, aralık, başlığa göre)",
    },
    'cmdmenu_today': {
        "en": "Today's news",
        "ru": "Новости за сегодня",
        "uz": "Bugungi yangiliklar",
        "de": "Heutige Nachrichten",
        "tr": "Bugünün haberleri",
    },
    'cmdmenu_auto': {
        "en": "Schedule daily / weekly delivery",
        "ru": "Ежедневная / еженедельная рассылка",
        "uz": "Kunlik / haftalik yetkazib berish",
        "de": "Tägliche / wöchentliche Lieferung",
        "tr": "Günlük / haftalık teslim",
    },
    'cmdmenu_voice': {
        "en": "TTS voice (per language)",
        "ru": "Голос TTS (по языкам)",
        "uz": "TTS ovozi (til bo'yicha)",
        "de": "TTS-Stimme (pro Sprache)",
        "tr": "TTS sesi (dile göre)",
    },
    'cmdmenu_speed': {
        "en": "Audio playback speed",
        "ru": "Скорость аудио",
        "uz": "Audio tezligi",
        "de": "Audiogeschwindigkeit",
        "tr": "Ses hızı",
    },
    'cmdmenu_translate': {
        "en": "Translate articles before TTS",
        "ru": "Перевод статей перед озвучкой",
        "uz": "TTS oldidan maqolalarni tarjima qilish",
        "de": "Artikel vor TTS übersetzen",
        "tr": "TTS öncesi makaleyi çevir",
    },
    'cmdmenu_summarize': {
        "en": "Add 2-3 sentence summary",
        "ru": "Добавить резюме на 2-3 предложения",
        "uz": "2-3 jumlali xulosa qo'shish",
        "de": "2-3-Satz-Zusammenfassung hinzufügen",
        "tr": "2-3 cümlelik özet ekle",
    },
    'cmdmenu_find': {
        "en": "Search past articles",
        "ru": "Поиск по прошлым статьям",
        "uz": "Eski maqolalardan qidirish",
        "de": "In früheren Artikeln suchen",
        "tr": "Geçmiş makalelerde ara",
    },
    'cmdmenu_bookmarks': {
        "en": "List bookmarks (with tags)",
        "ru": "Список закладок (с тегами)",
        "uz": "Xatcho'plar ro'yxati (teglar bilan)",
        "de": "Lesezeichen auflisten (mit Tags)",
        "tr": "Yer imleri (etiketlerle)",
    },
    'cmdmenu_stats': {
        "en": "Reading + audio stats",
        "ru": "Статистика чтения и аудио",
        "uz": "O'qish va audio statistikasi",
        "de": "Lese- und Audio-Statistik",
        "tr": "Okuma ve ses istatistikleri",
    },
    'cmdmenu_status': {
        "en": "Show current settings",
        "ru": "Текущие настройки",
        "uz": "Joriy sozlamalar",
        "de": "Aktuelle Einstellungen",
        "tr": "Mevcut ayarlar",
    },
    'cmdmenu_help': {
        "en": "Full guide",
        "ru": "Полное руководство",
        "uz": "To'liq qo'llanma",
        "de": "Komplette Anleitung",
        "tr": "Tam rehber",
    },
    'cmdmenu_about': {
        "en": "About this bot",
        "ru": "О боте",
        "uz": "Bot haqida",
        "de": "Über diesen Bot",
        "tr": "Bu bot hakkında",
    },

    # Phase 15D: structured delivery card
    'delivery_card': {
        "en": (
            "✅ Done\n\n"
            "📊 Delivered\n"
            "{summary}\n\n"
            "📌 Posts: #{oldest} → #{newest}{next_batch}"
        ),
        "ru": (
            "✅ Готово\n\n"
            "📊 Доставлено\n"
            "{summary}\n\n"
            "📌 Посты: #{oldest} → #{newest}{next_batch}"
        ),
        "uz": (
            "✅ Tayyor\n\n"
            "📊 Yetkazib berildi\n"
            "{summary}\n\n"
            "📌 Postlar: #{oldest} → #{newest}{next_batch}"
        ),
        "de": (
            "✅ Fertig\n\n"
            "📊 Geliefert\n"
            "{summary}\n\n"
            "📌 Posts: #{oldest} → #{newest}{next_batch}"
        ),
        "tr": (
            "✅ Tamam\n\n"
            "📊 Teslim edildi\n"
            "{summary}\n\n"
            "📌 Gönderiler: #{oldest} → #{newest}{next_batch}"
        ),
    },
    'delivery_next_batch': {
        "en": "\n📥 Next batch: /scrape {start}-{end}",
        "ru": "\n📥 Следующая партия: /scrape {start}-{end}",
        "uz": "\n📥 Keyingi partiya: /scrape {start}-{end}",
        "de": "\n📥 Nächste Charge: /scrape {start}-{end}",
        "tr": "\n📥 Sonraki parti: /scrape {start}-{end}",
    },
    'delivery_line_articles': {
        "en": "  • {n} articles",
        "ru": "  • {n} статей",
        "uz": "  • {n} ta maqola",
        "de": "  • {n} Artikel",
        "tr": "  • {n} makale",
    },
    'delivery_line_audio': {
        "en": "  • {n} voice messages",
        "ru": "  • {n} голосовых сообщений",
        "uz": "  • {n} ta ovozli xabar",
        "de": "  • {n} Sprachnachrichten",
        "tr": "  • {n} sesli mesaj",
    },
    'delivery_line_images': {
        "en": "  • {n} images",
        "ru": "  • {n} изображений",
        "uz": "  • {n} ta rasm",
        "de": "  • {n} Bilder",
        "tr": "  • {n} görsel",
    },

    'translate_status_off': {
        "en": "Article translation is OFF. /translate <lang> to enable (lang: en, ru, uz, de, tr).",
        "ru": "Перевод статей ВЫКЛ. /translate <язык> чтобы включить (en/ru/uz/de/tr).",
        "uz": "Maqola tarjimasi O'CHIQ. Yoqish: /translate <til> (en/ru/uz/de/tr).",
        "de": "Artikel-Übersetzung AUS. /translate <Sprache> zum Einschalten (en/ru/uz/de/tr).",
        "tr": "Makale çevirisi KAPALI. Açmak için /translate <dil> (en/ru/uz/de/tr).",
    },
    'translate_status_on': {
        "en": "Article translation is ON. Articles are translated to {target} before TTS.",
        "ru": "Перевод статей ВКЛ. Статьи переводятся на {target} перед озвучкой.",
        "uz": "Maqola tarjimasi YOQ. Maqolalar TTS oldidan {target} tiliga tarjima qilinadi.",
        "de": "Artikel-Übersetzung AN. Artikel werden vor TTS auf {target} übersetzt.",
        "tr": "Makale çevirisi AÇIK. Makaleler TTS'ten önce {target} diline çevrilir.",
    },
    'translate_no_key': {
        "en": "Translation is enabled but GROQ_API_KEY isn't set — articles will arrive untranslated.",
        "ru": "Перевод включён, но GROQ_API_KEY не задан — статьи будут без перевода.",
        "uz": "Tarjima yoqilgan, lekin GROQ_API_KEY yo'q — maqolalar tarjimasiz keladi.",
        "de": "Übersetzung an, aber GROQ_API_KEY fehlt — Artikel kommen unübersetzt.",
        "tr": "Çeviri açık ama GROQ_API_KEY yok — makaleler çevrilmeden gelir.",
    },
    'translate_set_on': {
        "en": "✅ Articles will now be translated to {target} before TTS. Override per-scrape with translate=<lang>.",
        "ru": "✅ Статьи будут переводиться на {target} перед озвучкой. Переопределить разово: translate=<lang>.",
        "uz": "✅ Maqolalar TTS oldidan {target} tiliga tarjima qilinadi. Bir martalik bekor: translate=<lang>.",
        "de": "✅ Artikel werden ab jetzt auf {target} übersetzt. Pro Scrape überschreiben: translate=<lang>.",
        "tr": "✅ Makaleler artık {target} diline çevrilecek. Tek seferlik geçersiz kıl: translate=<lang>.",
    },
    'translate_set_on_no_key': {
        "en": "✅ Set to {target} — but GROQ_API_KEY isn't set yet. Get a free key at console.groq.com.",
        "ru": "✅ Установлено: {target} — но GROQ_API_KEY ещё не задан. Бесплатный ключ: console.groq.com.",
        "uz": "✅ {target} ga o'rnatildi — lekin GROQ_API_KEY yo'q. Bepul kalit: console.groq.com.",
        "de": "✅ Auf {target} gesetzt — aber GROQ_API_KEY fehlt noch. Kostenloser Schlüssel: console.groq.com.",
        "tr": "✅ {target} olarak ayarlandı — ama GROQ_API_KEY yok. Ücretsiz: console.groq.com.",
    },
    'translate_set_off': {
        "en": "✅ Article translation disabled.",
        "ru": "✅ Перевод статей отключён.",
        "uz": "✅ Maqola tarjimasi o'chirildi.",
        "de": "✅ Artikel-Übersetzung deaktiviert.",
        "tr": "✅ Makale çevirisi devre dışı.",
    },
    'translate_unknown': {
        "en": "Unknown language '{choice}'. Use one of: en, ru, uz, de, tr, off.",
        "ru": "Неизвестный язык '{choice}'. Допустимо: en, ru, uz, de, tr, off.",
        "uz": "Noma'lum til '{choice}'. Mumkin: en, ru, uz, de, tr, off.",
        "de": "Unbekannte Sprache '{choice}'. Verfügbar: en, ru, uz, de, tr, off.",
        "tr": "Bilinmeyen dil '{choice}'. Kullanılabilir: en, ru, uz, de, tr, off.",
    },

    'untitled': {
        "en": 'Untitled',
        "ru": 'Без названия',
        "uz": 'Sarlavhasiz',
        "de": 'Ohne Titel',
        "tr": 'Başlıksız',
    },

}


def t(key, lang="en", **kwargs):
    """Get a translated string.

    Args:
        key: Translation key.
        lang: Language code (en, ru, uz, de, tr).
        **kwargs: Format arguments for the string.

    Returns:
        Translated and formatted string. Falls back to English if
        the key or language is missing.
    """
    strings = _STRINGS.get(key, {})
    text = strings.get(lang) or strings.get("en", key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
