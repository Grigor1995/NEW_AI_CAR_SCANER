"""Stable error codes with native-client English, Armenian and Russian messages."""
MESSAGES = {
    'disabled': ('Ecosystem features are disabled.', 'Համակարգի նոր հնարավորություններն անջատված են։', 'Функции экосистемы отключены.'),
    'unauthorized': ('Authentication required or session expired.', 'Պահանջվում է մուտք, կամ սեսիայի ժամկետն ավարտվել է։', 'Требуется вход или срок сессии истёк.'),
    'forbidden': ('Permission denied.', 'Մուտքն արգելված է։', 'Доступ запрещён.'),
    'not_found': ('Resource not found.', 'Տվյալը չի գտնվել։', 'Ресурс не найден.'),
    'conflict': ('The resource already exists or was already processed.', 'Տվյալն արդեն գոյություն ունի կամ մշակված է։', 'Ресурс уже существует или обработан.'),
    'invalid_credentials': ('Invalid email or password.', 'Սխալ էլփոստ կամ գաղտնաբառ։', 'Неверная почта или пароль.'),
    'invalid_input': ('Invalid request fields.', 'Հարցման դաշտերը սխալ են։', 'Некорректные поля запроса.'),
    'rate_limited': ('Too many attempts. Try again later.', 'Չափազանց շատ փորձեր։ Փորձեք ավելի ուշ։', 'Слишком много попыток. Повторите позже.'),
    'database_unavailable': ('Configure the database and run ecosystem migrations first.', 'Նախ կարգավորեք տվյալների բազան և կատարեք միգրացիաները։', 'Сначала настройте базу данных и выполните миграции.'),
    'legacy_blocked': ('Legacy APIs are unavailable in ecosystem mode. Use authenticated v2 endpoints.', 'Նոր ռեժիմում հին API-ն հասանելի չէ։ Օգտագործեք նույնականացված v2 API-ն։', 'Старый API недоступен в режиме экосистемы. Используйте авторизованный API v2.'),
}


class DomainError(Exception):
    def __init__(self, code, status=403):
        self.code, self.status = code, status
        super().__init__(code)


def error_body(code, language='en'):
    language = language.split(',')[0].split(';')[0].split('-')[0].lower()
    index = {'en': 0, 'hy': 1, 'ru': 2}.get(language, 0)
    return {'code': code, 'detail': MESSAGES[code][index]}
