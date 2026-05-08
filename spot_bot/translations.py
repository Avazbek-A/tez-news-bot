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
            "/scrape 50 audio — .txt + individual MP3s\n"
            "/scrape 50 audio combined — .txt + one combined MP3\n"
            "/scrape 35808-35758 — Posts by ID (stable)\n"
            "/scrape 2000-1950 — Posts by offset from latest\n"
            "/scrape 50 images — .txt + article images\n"
            "/scrape from \"<title>\" 50 — Anchor on a title; scrape 50 forward\n"
            "/scrape from \"<title>\" 5 audio combined — Title-anchored + combined MP3\n\n"
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
            "/auto — Show auto-scrape status\n"
            "/auto on 3 — Enable every 3 days\n"
            "/auto 50 audio combined — Set options\n"
            "/auto off — Disable\n\n"
            "Control:\n"
            "/cancel — Stop a running job\n\n"
            "Settings:\n"
            "/voice andrew — Change TTS voice\n"
            "/speed fast — Change audio speed\n"
            "/lang en — Change language (en/ru/uz)\n"
            "/order newest|oldest — Default delivery order\n"
            "/channel — Show/change source channel\n"
            "/status — Show current settings"
        ),
        "ru": (
            "Spot News Bot\n\n"
            "Скрапинг:\n"
            "/scrape 50 — Последние 50 в .txt файле\n"
            "/scrape 50 inline — Отправить отдельными сообщениями\n"
            "/scrape 50 audio — .txt + отдельные MP3\n"
            "/scrape 50 audio combined — .txt + один общий MP3\n"
            "/scrape 35808-35758 — По ID постов (стабильно)\n"
            "/scrape 2000-1950 — По смещению от последнего\n"
            "/scrape 50 images — .txt + изображения статей\n"
            "/scrape from \"<заголовок>\" 50 — От заголовка вперёд на 50\n"
            "/scrape from \"<заголовок>\" 5 audio combined — От заголовка + общий MP3\n\n"
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
            "/auto — Статус авто-скрапинга\n"
            "/auto on 3 — Включить каждые 3 дня\n"
            "/auto 50 audio combined — Настроить параметры\n"
            "/auto off — Отключить\n\n"
            "Управление:\n"
            "/cancel — Остановить текущую задачу\n\n"
            "Настройки:\n"
            "/voice dmitry — Сменить голос TTS\n"
            "/speed fast — Скорость аудио\n"
            "/lang ru — Сменить язык (en/ru/uz)\n"
            "/order newest|oldest — Порядок отправки по умолчанию\n"
            "/channel — Канал-источник\n"
            "/status — Текущие настройки"
        ),
        "uz": (
            "Spot News Bot\n\n"
            "Skraping:\n"
            "/scrape 50 — So'nggi 50 ta .txt faylda\n"
            "/scrape 50 inline — Alohida xabarlar sifatida\n"
            "/scrape 50 audio — .txt + alohida MP3lar\n"
            "/scrape 50 audio combined — .txt + bitta umumiy MP3\n"
            "/scrape 35808-35758 — Post ID bo'yicha (barqaror)\n"
            "/scrape 2000-1950 — So'nggidan siljish bo'yicha\n"
            "/scrape 50 images — .txt + maqola rasmlari\n"
            "/scrape from \"<sarlavha>\" 50 — Sarlavhadan oldinga 50 ta\n"
            "/scrape from \"<sarlavha>\" 5 audio combined — Sarlavhadan + umumiy MP3\n\n"
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
            "/auto — Avto-skraping holati\n"
            "/auto on 3 — Har 3 kunda yoqish\n"
            "/auto 50 audio combined — Sozlamalarni o'rnatish\n"
            "/auto off — O'chirish\n\n"
            "Boshqaruv:\n"
            "/cancel — Joriy vazifani to'xtatish\n\n"
            "Sozlamalar:\n"
            "/voice sardor — TTS ovozini o'zgartirish\n"
            "/speed fast — Audio tezligi\n"
            "/lang uz — Tilni o'zgartirish (en/ru/uz)\n"
            "/order newest|oldest — Standart yetkazib berish tartibi\n"
            "/channel — Manba kanali\n"
            "/status — Joriy sozlamalar"
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
