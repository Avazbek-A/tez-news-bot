"""Localization strings for the Spot News Bot.

Supports English (en), Russian (ru), and Uzbek (uz).
"""

_STRINGS = {
    # /start help text
    "start_help": {
        "en": (
            "Spot News Bot\n\n"
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
            "/since YYYY-MM-DD [flags] — Everything since a date\n\n"
            "How \"from\" works:\n"
            "• Wrap the title in double quotes. A fragment is enough.\n"
            "• Match is case-insensitive; punctuation is ignored.\n"
            "• Bot scans the latest ~2000 posts; most-recent match wins.\n"
            "• The matched article becomes #1 (oldest) in the batch;\n"
            "  the next N-1 newer articles follow.\n"
            "• All flags work: audio, combined, images, inline, file.\n"
            "Example:\n"
            "  /scrape from \"Tashkent metro\" 10 audio combined\n\n"
            "Auto-scrape:\n"
            "/auto daily 08:00 50 audio combined — Every day at 08:00\n"
            "/auto weekdays 08:00 50 audio — Mon-Fri only\n"
            "/auto weekly Mon 08:00 50 audio — Once a week\n"
            "/auto every 3 50 audio combined — Every 3 days (interval)\n"
            "/auto off — Disable\n\n"
            "Control:\n"
            "/cancel — Stop a running job\n\n"
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
            "/status — Show current settings\n\n"
            "Reading log:\n"
            "/find <query> — Search past delivered articles\n"
            "/unread — Count new articles since last scrape\n"
            "/bookmarks — List saved articles\n"
            "/unbookmark <id> — Remove a bookmark\n"
            "/resume — Jump to last marked voice message (📍 button)\n\n"
            "Sources:\n"
            "/sources — List configured sources\n"
            "/addsource <type> <url> [label] — Add (type: telegram or rss)\n"
            "/removesource <id> — Remove"
        ),
        "ru": (
            "Spot News Bot\n\n"
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
            "/since YYYY-MM-DD [флаги] — Всё с указанной даты\n\n"
            "Как работает \"from\":\n"
            "• Заголовок — в двойных кавычках. Достаточно фрагмента.\n"
            "• Регистр и пунктуация не учитываются.\n"
            "• Сканируется до 2000 последних постов; берётся самый новый совпавший.\n"
            "• Найденная статья становится #1 (самой старой) в подборке;\n"
            "  далее идут N-1 более новых статей.\n"
            "• Все флаги работают: audio, combined, images, inline, file.\n"
            "Пример:\n"
            "  /scrape from \"Ташкентское метро\" 10 audio combined\n\n"
            "Авто-скрапинг:\n"
            "/auto daily 08:00 50 audio combined — Каждый день в 08:00\n"
            "/auto weekdays 08:00 50 audio — Только Пн-Пт\n"
            "/auto weekly Mon 08:00 50 audio — Раз в неделю\n"
            "/auto every 3 50 audio combined — Каждые 3 дня (интервал)\n"
            "/auto off — Отключить\n\n"
            "Управление:\n"
            "/cancel — Остановить текущую задачу\n\n"
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
            "/status — Текущие настройки\n\n"
            "История:\n"
            "/find <запрос> — Поиск по полученным статьям\n"
            "/unread — Сколько новых статей с прошлого сбора\n"
            "/bookmarks — Список сохранённых статей\n"
            "/unbookmark <id> — Удалить закладку\n"
            "/resume — Перейти к отмеченному голосовому (кнопка 📍)\n\n"
            "Источники:\n"
            "/sources — Список настроенных источников\n"
            "/addsource <тип> <url> [название] — Добавить (тип: telegram или rss)\n"
            "/removesource <id> — Удалить"
        ),
        "uz": (
            "Spot News Bot\n\n"
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
            "/since YYYY-MM-DD [bayroqlar] — Sanadan beri hammasi\n\n"
            "\"from\" qanday ishlaydi:\n"
            "• Sarlavhani qo'shtirnoq ichiga oling. Bo'lak ham yetadi.\n"
            "• Katta-kichik harf va tinish belgilari hisobga olinmaydi.\n"
            "• So'nggi ~2000 post ko'rib chiqiladi; eng yangi mosi olinadi.\n"
            "• Topilgan maqola partiyaning #1 (eng eskisi) bo'ladi;\n"
            "  keyin N-1 yangi maqola keladi.\n"
            "• Barcha flaglar ishlaydi: audio, combined, images, inline, file.\n"
            "Misol:\n"
            "  /scrape from \"Toshkent metro\" 10 audio combined\n\n"
            "Avto-skraping:\n"
            "/auto daily 08:00 50 audio combined — Har kuni 08:00 da\n"
            "/auto weekdays 08:00 50 audio — Faqat Du-Ju\n"
            "/auto weekly Mon 08:00 50 audio — Haftada bir marta\n"
            "/auto every 3 50 audio combined — Har 3 kunda (interval)\n"
            "/auto off — O'chirish\n\n"
            "Boshqaruv:\n"
            "/cancel — Joriy vazifani to'xtatish\n\n"
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
            "/status — Joriy sozlamalar\n\n"
            "O'qish tarixi:\n"
            "/find <so'rov> — Olingan maqolalar orasidan qidirish\n"
            "/unread — Oxirgi yig'ishdan beri qancha yangi maqola\n"
            "/bookmarks — Saqlangan maqolalar ro'yxati\n"
            "/unbookmark <id> — Xatcho'pni olib tashlash\n"
            "/resume — Belgilangan ovozli xabarga o'tish (📍 tugmasi)\n\n"
            "Manbalar:\n"
            "/sources — Sozlangan manbalar ro'yxati\n"
            "/addsource <turi> <url> [nomi] — Qo'shish (turi: telegram yoki rss)\n"
            "/removesource <id> — O'chirish"
        ),
    },

    # /scrape messages
    "job_running": {
        "en": "A job is already running. Use /cancel to stop it first.",
        "ru": "Задание уже выполняется. Используйте /cancel для отмены.",
        "uz": "Vazifa allaqachon bajarilmoqda. To'xtatish uchun /cancel ni bosing.",
    },
    "range_format": {
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
    },
    "max_range": {
        "en": "Max range size is {max} posts.",
        "ru": "Максимальный размер диапазона: {max} постов.",
        "uz": "Maksimal diapazon hajmi: {max} ta post.",
    },
    "max_offset": {
        "en": "Max offset is {max}. For larger numbers, use post IDs (both numbers > {max}).",
        "ru": "Максимальное смещение: {max}. Для больших чисел используйте ID постов (оба числа > {max}).",
        "uz": "Maksimal siljish: {max}. Kattaroq sonlar uchun post ID ishlating (ikkala son > {max}).",
    },
    "starting": {
        "en": "Starting: {desc}...",
        "ru": "Запуск: {desc}...",
        "uz": "Boshlanmoqda: {desc}...",
    },

    # _run_job messages
    "no_articles": {
        "en": "No articles found.",
        "ru": "Статьи не найдены.",
        "uz": "Maqolalar topilmadi.",
    },
    "from_title_quotes": {
        "en": "Mismatched quotes. Use: /scrape from \"<title>\" 50",
        "ru": "Кавычки не закрыты. Используйте: /scrape from \"<заголовок>\" 50",
        "uz": "Qo'shtirnoqlar yopilmagan. Foydalaning: /scrape from \"<sarlavha>\" 50",
    },
    "from_title_missing": {
        "en": "Missing title. Use: /scrape from \"<title>\" 50",
        "ru": "Не указан заголовок. Используйте: /scrape from \"<заголовок>\" 50",
        "uz": "Sarlavha ko'rsatilmagan. Foydalaning: /scrape from \"<sarlavha>\" 50",
    },
    "from_title_not_found": {
        "en": "No article found matching: {title}",
        "ru": "Не найдено статьи по запросу: {title}",
        "uz": "So'rov bo'yicha maqola topilmadi: {title}",
    },
    "from_title_found": {
        "en": "Found: {preview}\nScraping forward...",
        "ru": "Найдено: {preview}\nСбор продолжается...",
        "uz": "Topildi: {preview}\nYig'ish davom etmoqda...",
    },
    "from_title_anchor": {
        "en": "Anchor: post #{anchor_id}\n{preview}",
        "ru": "Якорь: пост #{anchor_id}\n{preview}",
        "uz": "Bog'lanish: post #{anchor_id}\n{preview}",
    },
    "from_title_searching": {
        "en": "Searching for: {title}\n(scanning up to 2000 recent posts)",
        "ru": "Поиск: {title}\n(сканирую до 2000 последних постов)",
        "uz": "Qidirilmoqda: {title}\n(so'nggi 2000 ta postgacha skanerlanadi)",
    },
    "from_title_proceeding": {
        "en": "Confirmed. Scraping next {count} articles...",
        "ru": "Подтверждено. Сбор следующих {count} статей...",
        "uz": "Tasdiqlandi. Keyingi {count} ta maqola yig'ilmoqda...",
    },
    "confirm_anchor": {
        "en": (
            "Found this article — scrape forward from here?\n\n"
            "Title: {preview}\n"
            "Post ID: #{anchor_id}\n"
            "Date: {date}\n"
            "Will scrape: {count} articles starting from this one"
        ),
        "ru": (
            "Найдена эта статья — собрать вперёд от неё?\n\n"
            "Заголовок: {preview}\n"
            "ID поста: #{anchor_id}\n"
            "Дата: {date}\n"
            "Будет собрано: {count} статей, начиная с этой"
        ),
        "uz": (
            "Bu maqola topildi — shu joydan boshlab oldinga yig'ilsinmi?\n\n"
            "Sarlavha: {preview}\n"
            "Post ID: #{anchor_id}\n"
            "Sana: {date}\n"
            "Yig'iladi: shu maqoladan boshlab {count} ta"
        ),
    },
    "confirm_yes_btn": {
        "en": "✅ Confirm",
        "ru": "✅ Подтвердить",
        "uz": "✅ Tasdiqlash",
    },
    "confirm_no_btn": {
        "en": "❌ Cancel",
        "ru": "❌ Отмена",
        "uz": "❌ Bekor qilish",
    },
    "confirm_cancelled": {
        "en": "Cancelled. No articles scraped.",
        "ru": "Отменено. Статьи не собраны.",
        "uz": "Bekor qilindi. Maqolalar yig'ilmadi.",
    },
    "confirm_timeout": {
        "en": "No response in 5 minutes. Cancelled.",
        "ru": "Нет ответа за 5 минут. Отменено.",
        "uz": "5 daqiqa ichida javob yo'q. Bekor qilindi.",
    },
    "sending_articles": {
        "en": "Sending {count} articles...",
        "ru": "Отправка {count} статей...",
        "uz": "{count} ta maqola yuborilmoqda...",
    },
    "sending_images": {
        "en": "Sending images...",
        "ru": "Отправка изображений...",
        "uz": "Rasmlar yuborilmoqda...",
    },
    "combining_audio": {
        "en": "Combining audio with announcements...",
        "ru": "Объединение аудио с анонсами...",
        "uz": "Audio e'lonlar bilan birlashtirilmoqda...",
    },
    "chapters_header": {
        "en": "📑 Chapters (scrub the voice message above):",
        "ru": "📑 Главы (прокрутите голосовое выше):",
        "uz": "📑 Bo'limlar (yuqoridagi ovozni o'zgartiring):",
    },

    # /scrape inline-keyboard menu
    "menu_configure": {
        "en": "Configure your scrape:",
        "ru": "Настройте сбор:",
        "uz": "Yig'ishni sozlang:",
    },
    "menu_format_text": {
        "en": "📄 Text",
        "ru": "📄 Текст",
        "uz": "📄 Matn",
    },
    "menu_format_audio": {
        "en": "🎵 Audio",
        "ru": "🎵 Аудио",
        "uz": "🎵 Audio",
    },
    "menu_format_combined": {
        "en": "🎙️ Combined",
        "ru": "🎙️ Общее",
        "uz": "🎙️ Umumiy",
    },
    "menu_order_newest": {
        "en": "⬆️ Newest",
        "ru": "⬆️ Новые",
        "uz": "⬆️ Yangi",
    },
    "menu_order_oldest": {
        "en": "⬇️ Oldest",
        "ru": "⬇️ Старые",
        "uz": "⬇️ Eski",
    },
    "menu_start": {
        "en": "▶️ Start",
        "ru": "▶️ Старт",
        "uz": "▶️ Boshlash",
    },
    "menu_cancel": {
        "en": "✖️ Cancel",
        "ru": "✖️ Отмена",
        "uz": "✖️ Bekor",
    },
    "menu_starting": {
        "en": "Starting: /scrape {args}",
        "ru": "Запуск: /scrape {args}",
        "uz": "Boshlanmoqda: /scrape {args}",
    },
    "menu_cancelled": {
        "en": "Menu cancelled.",
        "ru": "Меню закрыто.",
        "uz": "Menyu bekor qilindi.",
    },
    "menu_expired": {
        "en": "Menu expired. Send /scrape again.",
        "ru": "Меню устарело. Отправьте /scrape снова.",
        "uz": "Menyu eskirgan. /scrape ni qayta yuboring.",
    },

    # Reading log + bookmarks
    "unread_empty": {
        "en": "No reading history yet. Run /scrape first; I'll start tracking from there.",
        "ru": "История пуста. Запустите /scrape — отсчёт начнётся с этого момента.",
        "uz": "Tarix bo'sh. Avval /scrape ni ishga tushiring; shundan boshlab kuzataman.",
    },
    "unread_none": {
        "en": "Up to date — no new articles since #{last}.",
        "ru": "Всё актуально — новых статей нет с #{last}.",
        "uz": "Yangiliklar yo'q — #{last} dan keyin yangi maqola yo'q.",
    },
    "unread_count": {
        "en": "{count} new articles since last scrape (#{last} → #{latest}).\nRun /scrape {latest}-{last} to fetch.",
        "ru": "{count} новых статей с прошлого сбора (#{last} → #{latest}).\nЗапустите /scrape {latest}-{last}.",
        "uz": "Oxirgi yig'ishdan beri {count} ta yangi maqola (#{last} → #{latest}).\nUni olish: /scrape {latest}-{last}",
    },
    "unread_error": {
        "en": "Couldn't reach the channel: {err}",
        "ru": "Не удалось обратиться к каналу: {err}",
        "uz": "Kanalga ulanib bo'lmadi: {err}",
    },
    "bookmark_save_btn": {
        "en": "🔖 Save",
        "ru": "🔖 Сохранить",
        "uz": "🔖 Saqlash",
    },
    "bookmark_saved_btn": {
        "en": "✅ Saved",
        "ru": "✅ Сохранено",
        "uz": "✅ Saqlandi",
    },
    "bookmark_saved_toast": {
        "en": "Saved #{id}",
        "ru": "Сохранено #{id}",
        "uz": "#{id} saqlandi",
    },
    "bookmarks_empty": {
        "en": "No bookmarks yet. Tap 🔖 Save under any article to add one.",
        "ru": "Закладок пока нет. Нажмите 🔖 Сохранить под статьёй.",
        "uz": "Hali xatcho'plar yo'q. Maqola ostidagi 🔖 Saqlash ni bosing.",
    },
    "bookmarks_header": {
        "en": "🔖 {n} bookmarks:",
        "ru": "🔖 {n} закладок:",
        "uz": "🔖 {n} ta xatcho'p:",
    },
    "unbookmark_usage": {
        "en": "Usage: /unbookmark <post_id>  (e.g. /unbookmark 35808)",
        "ru": "Использование: /unbookmark <post_id>  (например /unbookmark 35808)",
        "uz": "Foydalanish: /unbookmark <post_id>  (masalan /unbookmark 35808)",
    },
    "unbookmark_removed": {
        "en": "Removed bookmark #{id}.",
        "ru": "Закладка #{id} удалена.",
        "uz": "#{id} xatcho'pi o'chirildi.",
    },
    "unbookmark_not_found": {
        "en": "No bookmark for #{id}.",
        "ru": "Закладка #{id} не найдена.",
        "uz": "#{id} xatcho'pi topilmadi.",
    },

    # Multi-source / RSS
    "sources_empty": {
        "en": "No sources configured. Add one with /addsource.",
        "ru": "Источники не настроены. Добавьте через /addsource.",
        "uz": "Manbalar sozlanmagan. /addsource orqali qo'shing.",
    },
    "sources_header": {
        "en": "📡 {n} sources:",
        "ru": "📡 {n} источников:",
        "uz": "📡 {n} ta manba:",
    },
    "addsource_usage": {
        "en": "Usage: /addsource <type> <url> [label]\nTypes: telegram | rss\n  /addsource telegram https://t.me/s/spotuz Spot\n  /addsource rss https://kun.uz/news/rss Kun.uz",
        "ru": "Использование: /addsource <тип> <url> [название]\nТипы: telegram | rss\n  /addsource telegram https://t.me/s/spotuz Spot\n  /addsource rss https://kun.uz/news/rss Kun.uz",
        "uz": "Foydalanish: /addsource <turi> <url> [nomi]\nTurlari: telegram | rss\n  /addsource telegram https://t.me/s/spotuz Spot\n  /addsource rss https://kun.uz/news/rss Kun.uz",
    },
    "addsource_bad_type": {
        "en": "Type must be 'telegram' or 'rss'.",
        "ru": "Тип должен быть 'telegram' или 'rss'.",
        "uz": "Turi 'telegram' yoki 'rss' bo'lishi kerak.",
    },
    "addsource_bad_url": {
        "en": "URL must start with http:// or https://",
        "ru": "URL должен начинаться с http:// или https://",
        "uz": "URL http:// yoki https:// bilan boshlanishi kerak.",
    },
    "addsource_bad_telegram_url": {
        "en": "Telegram source URL must start with https://t.me/s/",
        "ru": "URL Telegram-источника должен начинаться с https://t.me/s/",
        "uz": "Telegram manba URL https://t.me/s/ bilan boshlanishi kerak.",
    },
    "addsource_added": {
        "en": "✅ Added source: {id} ({label})",
        "ru": "✅ Источник добавлен: {id} ({label})",
        "uz": "✅ Manba qo'shildi: {id} ({label})",
    },
    "removesource_usage": {
        "en": "Usage: /removesource <id>  (see /sources for ids)",
        "ru": "Использование: /removesource <id>  (см. /sources)",
        "uz": "Foydalanish: /removesource <id>  (idlar /sources da)",
    },
    "removesource_removed": {
        "en": "Removed source: {id}",
        "ru": "Источник удалён: {id}",
        "uz": "Manba o'chirildi: {id}",
    },
    "removesource_not_found": {
        "en": "No source with id '{id}'. Use /sources to list.",
        "ru": "Источник '{id}' не найден. См. /sources.",
        "uz": "'{id}' nomli manba topilmadi. /sources ni ko'ring.",
    },

    # /ads — toggle ad/sponsored content inclusion
    "ads_status_on": {
        "en": "Ads are currently INCLUDED. Use /ads off to filter them out.",
        "ru": "Реклама сейчас ВКЛЮЧЕНА. Чтобы фильтровать — /ads off.",
        "uz": "Reklamalar hozir KIRITILGAN. Filtrlash uchun /ads off.",
    },
    "ads_status_off": {
        "en": "Ads are currently FILTERED OUT. Use /ads on to keep them.",
        "ru": "Реклама сейчас ФИЛЬТРУЕТСЯ. Чтобы оставлять — /ads on.",
        "uz": "Reklamalar hozir FILTRLANYAPTI. Saqlash uchun /ads on.",
    },
    "ads_set_on": {
        "en": "✅ Ads will now be included in scraped articles.",
        "ru": "✅ Реклама теперь будет оставаться в собранных статьях.",
        "uz": "✅ Endi reklamalar maqolalarda saqlanadi.",
    },
    "ads_set_off": {
        "en": "✅ Ads will now be filtered out of scraped articles.",
        "ru": "✅ Реклама теперь будет фильтроваться из статей.",
        "uz": "✅ Endi reklamalar maqolalardan chiqariladi.",
    },
    "ads_unknown": {
        "en": "Unknown choice '{choice}'. Use /ads on or /ads off.",
        "ru": "Непонятное значение '{choice}'. Используйте /ads on или /ads off.",
        "uz": "Noma'lum '{choice}'. /ads on yoki /ads off ni ishlating.",
    },
    "status_ads_on": {
        "en": "Ads: included",
        "ru": "Реклама: включена",
        "uz": "Reklamalar: saqlanadi",
    },
    "status_ads_off": {
        "en": "Ads: filtered",
        "ru": "Реклама: фильтруется",
        "uz": "Reklamalar: filtrlanyapti",
    },

    # Date-based scrape shortcuts
    "date_label_today": {
        "en": "today's posts",
        "ru": "посты за сегодня",
        "uz": "bugungi postlar",
    },
    "date_label_yesterday": {
        "en": "yesterday's posts",
        "ru": "посты за вчера",
        "uz": "kechagi postlar",
    },
    "date_label_thisweek": {
        "en": "the last 7 days",
        "ru": "посты за последние 7 дней",
        "uz": "so'nggi 7 kun postlari",
    },
    "date_label_since": {
        "en": "posts since {date}",
        "ru": "посты с {date}",
        "uz": "{date} dan beri postlar",
    },
    "date_resolving": {
        "en": "Looking up {label}...",
        "ru": "Ищу {label}...",
        "uz": "{label} qidirilmoqda...",
    },
    "date_none": {
        "en": "No posts found for {label}.",
        "ru": "Постов не найдено за {label}.",
        "uz": "{label} bo'yicha postlar topilmadi.",
    },
    "date_error": {
        "en": "Date lookup failed: {err}",
        "ru": "Ошибка поиска по дате: {err}",
        "uz": "Sana bo'yicha qidirish xatosi: {err}",
    },
    "date_found": {
        "en": "Found {label}: posts #{oldest}-#{newest}. Starting...",
        "ru": "Найдено {label}: посты #{oldest}-#{newest}. Запуск...",
        "uz": "{label} topildi: postlar #{oldest}-#{newest}. Boshlanmoqda...",
    },
    "since_usage": {
        "en": "Usage: /since YYYY-MM-DD [audio combined images inline ...]\nExample: /since 2026-05-01 audio combined",
        "ru": "Использование: /since YYYY-MM-DD [audio combined images inline ...]\nПример: /since 2026-05-01 audio combined",
        "uz": "Foydalanish: /since YYYY-MM-DD [audio combined images inline ...]\nMisol: /since 2026-05-01 audio combined",
    },
    "since_bad_date": {
        "en": "Date must look like YYYY-MM-DD (e.g. 2026-05-01).",
        "ru": "Дата должна быть в формате YYYY-MM-DD (напр. 2026-05-01).",
        "uz": "Sana YYYY-MM-DD ko'rinishida bo'lishi kerak (masalan 2026-05-01).",
    },
    "since_future": {
        "en": "Date is in the future — nothing to scrape yet.",
        "ru": "Дата в будущем — пока ничего собирать.",
        "uz": "Sana kelajakda — hozircha yig'iladigan narsa yo'q.",
    },
    "find_usage": {
        "en": "Usage: /find <query>\nSearches all articles you've ever received.",
        "ru": "Использование: /find <запрос>\nИщет среди всех когда-либо полученных статей.",
        "uz": "Foydalanish: /find <so'rov>\nOlingan barcha maqolalar orasidan qidiradi.",
    },
    "find_none": {
        "en": "No matches for '{query}'.",
        "ru": "Не найдено совпадений для '{query}'.",
        "uz": "'{query}' bo'yicha mos topilmadi.",
    },
    "find_header": {
        "en": "🔎 {n} match(es) for '{query}':",
        "ru": "🔎 {n} совпадений для '{query}':",
        "uz": "🔎 '{query}' bo'yicha {n} ta moslik:",
    },
    "resume_marked_toast": {
        "en": "📍 Resume point set",
        "ru": "📍 Точка возврата установлена",
        "uz": "📍 Davom etish nuqtasi belgilandi",
    },
    "resume_none": {
        "en": "No resume point set yet. Tap 📍 Mark here under any voice message to set one.",
        "ru": "Точка возврата не установлена. Нажмите 📍 Mark here под голосовым сообщением.",
        "uz": "Davom etish nuqtasi yo'q. Ovozli xabar ostidagi 📍 Mark here ni bosing.",
    },
    "resume_pointer": {
        "en": "📍 You marked this voice message. Tap to play, scrub to where you stopped.",
        "ru": "📍 Вы отметили это голосовое. Нажмите воспроизвести и прокрутите туда, где остановились.",
        "uz": "📍 Bu ovozli xabarni belgilagansiz. Bosing va qayerda to'xtagan bo'lsangiz, o'sha joyga o'tib oling.",
    },
    "resume_lost": {
        "en": "Couldn't find the marked message — it may have been deleted from chat history.",
        "ru": "Отмеченное сообщение не найдено — возможно, оно удалено.",
        "uz": "Belgilangan xabar topilmadi — ehtimol, o'chirilgan.",
    },

    # Smart filters
    "quality_off": {"en": "Quality filter is OFF (no min length).",
                    "ru": "Фильтр качества ВЫКЛ.",
                    "uz": "Sifat filtri O'CHIQ."},
    "quality_status": {"en": "Quality filter: drop articles under {n} chars.",
                       "ru": "Фильтр качества: пропускать статьи короче {n} символов.",
                       "uz": "Sifat filtri: {n} belgidan qisqa maqolalar tashlanadi."},
    "quality_usage": {"en": "Usage: /quality <chars>  (e.g. /quality 200)\nUse 0 to disable.",
                      "ru": "Использование: /quality <число>  (напр. /quality 200)\n0 — отключить.",
                      "uz": "Foydalanish: /quality <son>  (masalan /quality 200)\n0 — o'chirish."},
    "quality_range": {"en": "Threshold must be 0..10000.",
                      "ru": "Порог должен быть 0..10000.",
                      "uz": "Chegara 0..10000 bo'lishi kerak."},
    "quality_set_off": {"en": "✅ Quality filter disabled.",
                        "ru": "✅ Фильтр качества отключён.",
                        "uz": "✅ Sifat filtri o'chirildi."},
    "quality_set_on": {"en": "✅ Quality threshold set to {n} chars.",
                       "ru": "✅ Порог качества: {n} символов.",
                       "uz": "✅ Sifat chegarasi: {n} belgi."},

    "topics_off": {"en": "Topic filter is OFF (all articles delivered).",
                   "ru": "Фильтр тем ВЫКЛ (доставляются все статьи).",
                   "uz": "Mavzu filtri O'CHIQ (hamma maqolalar yuboriladi)."},
    "topics_status": {"en": "Topic filter ON. Keywords: {list}",
                      "ru": "Фильтр тем ВКЛ. Ключи: {list}",
                      "uz": "Mavzu filtri YOQ. Kalit so'zlar: {list}"},
    "topics_set_off": {"en": "✅ Topic filter disabled.",
                       "ru": "✅ Фильтр тем отключён.",
                       "uz": "✅ Mavzu filtri o'chirildi."},
    "topics_set_on": {"en": "✅ Topic filter on: {list}",
                      "ru": "✅ Фильтр тем включён: {list}",
                      "uz": "✅ Mavzu filtri yoqildi: {list}"},

    "dedup_off": {"en": "Duplicate filter is OFF.",
                  "ru": "Фильтр дублей ВЫКЛ.",
                  "uz": "Takrorlar filtri O'CHIQ."},
    "dedup_status": {"en": "Duplicate filter: collapse titles ≥ {n}% similar.",
                     "ru": "Фильтр дублей: схлопывать заголовки от {n}% похожести.",
                     "uz": "Takrorlar filtri: {n}% va undan yuqori o'xshash sarlavhalar birlashtiriladi."},
    "dedup_usage": {"en": "Usage: /dedup <0-100>  (100 = disabled)",
                    "ru": "Использование: /dedup <0-100>  (100 = выкл.)",
                    "uz": "Foydalanish: /dedup <0-100>  (100 = o'chiq)"},
    "dedup_range": {"en": "Threshold must be 0..100.",
                    "ru": "Порог должен быть 0..100.",
                    "uz": "Chegara 0..100 bo'lishi kerak."},
    "dedup_set_off": {"en": "✅ Duplicate filter disabled.",
                      "ru": "✅ Фильтр дублей отключён.",
                      "uz": "✅ Takrorlar filtri o'chirildi."},
    "dedup_set_on": {"en": "✅ Duplicate threshold set to {n}%.",
                     "ru": "✅ Порог дублей: {n}%.",
                     "uz": "✅ Takrorlar chegarasi: {n}%."},

    # /summarize
    "summarize_status_off": {
        "en": "LLM summaries are OFF. /summarize on to enable.",
        "ru": "Резюме (LLM) ВЫКЛ. /summarize on — включить.",
        "uz": "LLM xulosalar O'CHIQ. Yoqish uchun: /summarize on.",
    },
    "summarize_status_on": {
        "en": "LLM summaries are ON. Each article gets a 2-3 sentence summary on top.",
        "ru": "Резюме ВКЛ. К каждой статье добавляется 2-3 предложения сверху.",
        "uz": "LLM xulosalar YOQ. Har maqolaga 2-3 jumlali xulosa qo'shiladi.",
    },
    "summarize_status_no_key": {
        "en": "Setting is ON but GROQ_API_KEY isn't set — summaries are silently skipped.",
        "ru": "Настройка ВКЛ, но GROQ_API_KEY не задан — резюме не создаются.",
        "uz": "Sozlama YOQ, lekin GROQ_API_KEY o'rnatilmagan — xulosalar tashlab yuboriladi.",
    },
    "summarize_set_on": {
        "en": "✅ LLM summaries enabled.",
        "ru": "✅ LLM-резюме включены.",
        "uz": "✅ LLM xulosalar yoqildi.",
    },
    "summarize_set_on_no_key": {
        "en": "✅ Enabled — but set GROQ_API_KEY in your env to actually get summaries. Free key at console.groq.com.",
        "ru": "✅ Включено — но укажите GROQ_API_KEY в переменных окружения. Бесплатный ключ: console.groq.com.",
        "uz": "✅ Yoqildi — lekin GROQ_API_KEY ni env da o'rnating. Bepul kalit: console.groq.com.",
    },
    "summarize_set_off": {
        "en": "✅ LLM summaries disabled.",
        "ru": "✅ LLM-резюме отключены.",
        "uz": "✅ LLM xulosalar o'chirildi.",
    },
    "summarize_unknown": {
        "en": "Unknown choice '{choice}'. Use /summarize on or /summarize off.",
        "ru": "Непонятное значение '{choice}'. /summarize on или /summarize off.",
        "uz": "Noma'lum '{choice}'. /summarize on yoki /summarize off.",
    },

    # /auto cron-mode strings
    "auto_usage": {
        "en": "Usage:\n  /auto daily HH:MM [count] [flags]\n  /auto weekdays HH:MM [count] [flags]\n  /auto weekly Mon HH:MM [count] [flags]\n  /auto every N [count] [flags]\n  /auto off",
        "ru": "Использование:\n  /auto daily HH:MM [count] [flags]\n  /auto weekdays HH:MM [count] [flags]\n  /auto weekly Mon HH:MM [count] [flags]\n  /auto every N [count] [flags]\n  /auto off",
        "uz": "Foydalanish:\n  /auto daily HH:MM [count] [flags]\n  /auto weekdays HH:MM [count] [flags]\n  /auto weekly Mon HH:MM [count] [flags]\n  /auto every N [count] [flags]\n  /auto off",
    },
    "auto_bad_syntax": {
        "en": "Bad /auto syntax: {err}\nSee /auto on its own for usage.",
        "ru": "Неверный синтаксис /auto: {err}\nЗапустите /auto без параметров для подсказки.",
        "uz": "/auto sintaksisi noto'g'ri: {err}\nKo'rsatma uchun /auto ni parametrsiz yuboring.",
    },
    "auto_enabled_cron": {
        "en": "✅ Auto-scrape: {days} at {hour:02d}:{minute:02d}, {count} articles{flags}",
        "ru": "✅ Авто-сбор: {days} в {hour:02d}:{minute:02d}, {count} статей{flags}",
        "uz": "✅ Avto-yig'ish: {days} {hour:02d}:{minute:02d} da, {count} ta maqola{flags}",
    },
    "days_every_day": {"en": "every day", "ru": "каждый день", "uz": "har kuni"},
    "days_weekdays": {"en": "weekdays", "ru": "по будням", "uz": "ish kunlari"},
    "day_0": {"en": "Mon", "ru": "Пн", "uz": "Du"},
    "day_1": {"en": "Tue", "ru": "Вт", "uz": "Se"},
    "day_2": {"en": "Wed", "ru": "Ср", "uz": "Ch"},
    "day_3": {"en": "Thu", "ru": "Чт", "uz": "Pa"},
    "day_4": {"en": "Fri", "ru": "Пт", "uz": "Ju"},
    "day_5": {"en": "Sat", "ru": "Сб", "uz": "Sh"},
    "day_6": {"en": "Sun", "ru": "Вс", "uz": "Ya"},
    "sending_combined": {
        "en": "Sending combined audio...",
        "ru": "Отправка общего аудио...",
        "uz": "Umumiy audio yuborilmoqda...",
    },
    "combined_too_large": {
        "en": "Combined file too large, sending individually...",
        "ru": "Общий файл слишком большой, отправка по отдельности...",
        "uz": "Umumiy fayl juda katta, alohida yuborilmoqda...",
    },
    "sending_audio": {
        "en": "Sending audio files...",
        "ru": "Отправка аудиофайлов...",
        "uz": "Audio fayllar yuborilmoqda...",
    },
    "done_sent": {
        "en": "Done! Sent {parts}.",
        "ru": "Готово! Отправлено: {parts}.",
        "uz": "Tayyor! Yuborildi: {parts}.",
    },
    "articles_count": {
        "en": "{n} articles",
        "ru": "{n} статей",
        "uz": "{n} ta maqola",
    },
    "images_count": {
        "en": "{n} images",
        "ru": "{n} изображений",
        "uz": "{n} ta rasm",
    },
    "audio_count": {
        "en": "{n} audio",
        "ru": "{n} аудио",
        "uz": "{n} ta audio",
    },
    "posts_range": {
        "en": "Posts #{oldest} to #{newest}.",
        "ru": "Посты #{oldest} — #{newest}.",
        "uz": "Postlar #{oldest} — #{newest}.",
    },
    "next_batch": {
        "en": "Next batch: /scrape {start}-{end}",
        "ru": "Следующая партия: /scrape {start}-{end}",
        "uz": "Keyingi partiya: /scrape {start}-{end}",
    },
    "cancelled": {
        "en": "Job cancelled.",
        "ru": "Задание отменено.",
        "uz": "Vazifa bekor qilindi.",
    },
    "error": {
        "en": "Error: {e}",
        "ru": "Ошибка: {e}",
        "uz": "Xato: {e}",
    },

    # /cancel
    "no_job": {
        "en": "No active job to cancel.",
        "ru": "Нет активных заданий для отмены.",
        "uz": "Bekor qilish uchun faol vazifa yo'q.",
    },
    "cancelling": {
        "en": "Cancelling...",
        "ru": "Отмена...",
        "uz": "Bekor qilinmoqda...",
    },

    # /voice
    "voice_current": {
        "en": "Current voice: {voice}\n\n{voice_list}\n\nUsage: /voice andrew",
        "ru": "Текущий голос: {voice}\n\n{voice_list}\n\nИспользование: /voice dmitry",
        "uz": "Joriy ovoz: {voice}\n\n{voice_list}\n\nFoydalanish: /voice sardor",
    },
    "voice_unknown": {
        "en": "Unknown voice '{name}'.\n\n{voice_list}",
        "ru": "Неизвестный голос '{name}'.\n\n{voice_list}",
        "uz": "Noma'lum ovoz '{name}'.\n\n{voice_list}",
    },
    "voice_set": {
        "en": "Voice set to: {voice}",
        "ru": "Голос изменён: {voice}",
        "uz": "Ovoz o'rnatildi: {voice}",
    },
    "lang_label_ru": {
        "en": "Russian",
        "ru": "Русские",
        "uz": "Rus",
    },
    "lang_label_en": {
        "en": "English",
        "ru": "Английские",
        "uz": "Ingliz",
    },
    "lang_label_uz": {
        "en": "Uzbek",
        "ru": "Узбекские",
        "uz": "O'zbek",
    },

    # /speed
    "speed_current": {
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
    },
    "speed_unknown": {
        "en": "Unknown speed '{name}'.\nPresets: {presets}\nOr use custom: +30%, -20%, etc.",
        "ru": "Неизвестная скорость '{name}'.\nПресеты: {presets}\nИли свои: +30%, -20% и т.д.",
        "uz": "Noma'lum tezlik '{name}'.\nTayyor sozlamalar: {presets}\nYoki maxsus: +30%, -20%, va h.k.",
    },
    "speed_set": {
        "en": "Speed set to: {speed}",
        "ru": "Скорость изменена: {speed}",
        "uz": "Tezlik o'rnatildi: {speed}",
    },

    # /channel
    "channel_current": {
        "en": "Current channel: {url}\n\nTo change: /channel https://t.me/s/channel_name",
        "ru": "Текущий канал: {url}\n\nИзменить: /channel https://t.me/s/channel_name",
        "uz": "Joriy kanal: {url}\n\nO'zgartirish: /channel https://t.me/s/channel_name",
    },
    "channel_invalid": {
        "en": "URL must start with https://t.me/s/\nExample: /channel https://t.me/s/spotuz",
        "ru": "URL должен начинаться с https://t.me/s/\nПример: /channel https://t.me/s/spotuz",
        "uz": "URL https://t.me/s/ bilan boshlanishi kerak\nMisol: /channel https://t.me/s/spotuz",
    },
    "channel_set": {
        "en": "Channel set to: {url}",
        "ru": "Канал изменён: {url}",
        "uz": "Kanal o'rnatildi: {url}",
    },

    # /status
    "status": {
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
    },
    "status_yes": {
        "en": "Yes",
        "ru": "Да",
        "uz": "Ha",
    },
    "status_no": {
        "en": "No",
        "ru": "Нет",
        "uz": "Yo'q",
    },
    "status_off": {
        "en": "Off",
        "ru": "Выключен",
        "uz": "O'chirilgan",
    },
    "auto_status_on": {
        "en": "Every {days}d, {count} articles",
        "ru": "Каждые {days} дн., {count} статей",
        "uz": "Har {days} kunda, {count} ta maqola",
    },

    # /auto
    "auto_show_off": {
        "en": (
            "Auto-scrape: Off\n\n"
            "Usage:\n"
            "/auto on 3 — Enable every 3 days\n"
            "/auto 50 audio combined — Set options\n"
            "/auto off — Disable"
        ),
        "ru": (
            "Авто-скрапинг: Выключен\n\n"
            "Использование:\n"
            "/auto on 3 — Включить каждые 3 дня\n"
            "/auto 50 audio combined — Настроить\n"
            "/auto off — Отключить"
        ),
        "uz": (
            "Avto-skraping: O'chirilgan\n\n"
            "Foydalanish:\n"
            "/auto on 3 — Har 3 kunda yoqish\n"
            "/auto 50 audio combined — Sozlash\n"
            "/auto off — O'chirish"
        ),
    },
    "auto_show_on": {
        "en": "Auto-scrape: Every {days} day(s), {count} articles{flags}",
        "ru": "Авто-скрапинг: Каждые {days} дн., {count} статей{flags}",
        "uz": "Avto-skraping: Har {days} kunda, {count} ta maqola{flags}",
    },
    "auto_disabled": {
        "en": "Auto-scrape disabled.",
        "ru": "Авто-скрапинг отключён.",
        "uz": "Avto-skraping o'chirildi.",
    },
    "auto_enabled": {
        "en": "Auto-scrape enabled: every {days} day(s), {count} articles{flags}.",
        "ru": "Авто-скрапинг включён: каждые {days} дн., {count} статей{flags}.",
        "uz": "Avto-skraping yoqildi: har {days} kunda, {count} ta maqola{flags}.",
    },
    "auto_interval_invalid": {
        "en": "Interval must be {min}-{max} days.",
        "ru": "Интервал должен быть {min}-{max} дней.",
        "uz": "Interval {min}-{max} kun bo'lishi kerak.",
    },
    "auto_skipped": {
        "en": "Auto-scrape skipped: a job is already running.",
        "ru": "Авто-скрапинг пропущен: задание уже выполняется.",
        "uz": "Avto-skraping o'tkazib yuborildi: vazifa allaqachon bajarilmoqda.",
    },
    "auto_starting": {
        "en": "Auto-scrape starting...",
        "ru": "Авто-скрапинг запускается...",
        "uz": "Avto-skraping boshlanmoqda...",
    },

    # /lang
    "lang_current": {
        "en": "Current language: English\n\nAvailable:\n/lang en — English\n/lang ru — Русский\n/lang uz — O'zbek",
        "ru": "Текущий язык: Русский\n\nДоступные:\n/lang en — English\n/lang ru — Русский\n/lang uz — O'zbek",
        "uz": "Joriy til: O'zbek\n\nMavjud:\n/lang en — English\n/lang ru — Русский\n/lang uz — O'zbek",
    },
    "lang_unknown": {
        "en": "Unknown language '{code}'. Available: en, ru, uz",
        "ru": "Неизвестный язык '{code}'. Доступные: en, ru, uz",
        "uz": "Noma'lum til '{code}'. Mavjud: en, ru, uz",
    },
    "lang_set": {
        "en": "Language set to: English",
        "ru": "Язык изменён: Русский",
        "uz": "Til o'rnatildi: O'zbek",
    },

    # /order
    "order_current": {
        "en": (
            "Current order: {order}\n\n"
            "Usage:\n"
            "/order newest — Newest articles first (default)\n"
            "/order oldest — Oldest articles first (chronological reading)\n\n"
            "One-off override on /scrape: add 'oldest' or 'newest' as a flag."
        ),
        "ru": (
            "Текущий порядок: {order}\n\n"
            "Использование:\n"
            "/order newest — Сначала новые (по умолчанию)\n"
            "/order oldest — Сначала старые (хронологическое чтение)\n\n"
            "Разовое переопределение для /scrape: добавьте флаг 'oldest' или 'newest'."
        ),
        "uz": (
            "Joriy tartib: {order}\n\n"
            "Foydalanish:\n"
            "/order newest — Avval yangilari (standart)\n"
            "/order oldest — Avval eskilari (xronologik o'qish)\n\n"
            "/scrape uchun bir martalik o'zgartirish: 'oldest' yoki 'newest' bayrog'ini qo'shing."
        ),
    },
    "order_unknown": {
        "en": "Unknown order '{name}'. Use 'newest' or 'oldest'.",
        "ru": "Неизвестный порядок '{name}'. Используйте 'newest' или 'oldest'.",
        "uz": "Noma'lum tartib '{name}'. 'newest' yoki 'oldest' ishlating.",
    },
    "order_set": {
        "en": "Order set to: {order}",
        "ru": "Порядок изменён: {order}",
        "uz": "Tartib o'rnatildi: {order}",
    },

    # Audio announcements
    "announcement_prefix": {
        "en": "Next article:",
        "ru": "Следующая статья:",
        "uz": "Keyingi maqola:",
    },
    "untitled": {
        "en": "Untitled",
        "ru": "Без названия",
        "uz": "Sarlavhasiz",
    },
}


def t(key, lang="en", **kwargs):
    """Get a translated string.

    Args:
        key: Translation key.
        lang: Language code (en, ru, uz).
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
