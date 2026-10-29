from __future__ import annotations

from copy import deepcopy
import re

from diagnostic.models import DiagnosticSession


LANGUAGE_ALIASES = {
    "en": "en",
    "ru": "ru",
    "hy": "hy",
    "arm": "hy",
    "am": "hy",
}


CATEGORY_LABELS = {
    "ru": {
        "ignition / combustion": "Зажигание / сгорание",
        "air-fuel / intake": "Смесь / впуск",
        "mechanical cylinder condition": "Механическое состояние цилиндра",
        "LPG fuel delivery / mixture": "Подача LPG / смесь",
        "LPG fuel delivery": "Подача LPG",
        "LPG injection": "Форсунки LPG",
        "ignition under LPG load": "Зажигание под нагрузкой LPG",
        "ignition": "Система зажигания",
        "intake": "Впускная система",
        "load-dependent behavior": "Поведение, зависящее от нагрузки",
        "load-dependent combustion": "Сгорание под нагрузкой",
        "idle stability / air-fuel control": "Стабильность холостого хода / управление смесью",
        "oil / combustion condition": "Состояние масла / сгорания",
        "lean mixture": "Бедная смесь",
        "rich mixture": "Богатая смесь",
        "air metering / MAF": "Измерение воздуха / MAF",
        "coolant temperature sensing": "Датчик температуры охлаждающей жидкости",
        "oxygen sensor / fuel feedback": "Лямбда-зонд / обратная связь по смеси",
        "catalyst efficiency": "Эффективность катализатора",
        "cam/crank correlation": "Синхронизация распредвал / коленвал",
        "transmission control / gear ratio": "Управление АКПП / передаточное отношение",
        "power supply / voltage": "Питание / напряжение",
        "vehicle network communication": "Связь по сети автомобиля",
        "starting system / engine start": "Система запуска двигателя",
        "engine stalling": "Остановка двигателя",
        "cooling system": "Система охлаждения",
        "electrical power supply": "Электропитание",

    },
    "hy": {
        "ignition / combustion": "Բոցավառում / այրում",
        "air-fuel / intake": "Օդ-վառելիք / ներծծման համակարգ",
        "mechanical cylinder condition": "Մխոցի մեխանիկական վիճակ",
        "LPG fuel delivery / mixture": "LPG-ի մատակարարում / խառնուրդ",
        "LPG fuel delivery": "LPG-ի մատակարարում",
        "LPG injection": "LPG ֆորսունկաներ",
        "ignition under LPG load": "Բոցավառում LPG բեռնվածության տակ",
        "ignition": "Բոցավառման համակարգ",
        "intake": "Ներծծման համակարգ",
        "load-dependent behavior": "Բեռնվածությունից կախված վարքագիծ",
        "load-dependent combustion": "Այրում բեռնվածության տակ",
        "idle stability / air-fuel control": "Պարապ ընթացքի կայունություն / խառնուրդի կառավարում",
        "oil / combustion condition": "Յուղի / այրման վիճակ",
        "lean mixture": "Նիհար խառնուրդ",
        "rich mixture": "Հարուստ խառնուրդ",
        "air metering / MAF": "Օդի չափում / MAF",
        "coolant temperature sensing": "Հովացուցիչ հեղուկի ջերմաստիճանի չափում",
        "oxygen sensor / fuel feedback": "Թթվածնի սենսոր / վառելիքի հետադարձ կապ",
        "catalyst efficiency": "Կատալիզատորի արդյունավետություն",
        "cam/crank correlation": "Ռասպրեդվալ / կոլենվալ համաժամացում",
        "transmission control / gear ratio": "Ավտոմատ փոխանցման կառավարում / փոխանցման հարաբերակցություն",
        "power supply / voltage": "Սնուցում / լարում",
        "vehicle network communication": "Մեքենայի ցանցային կապ",
        "starting system / engine start": "Գործարկման համակարգ / շարժիչի մեկնարկ",
        "engine stalling": "Շարժիչի կանգ",
        "cooling system": "Սառեցման համակարգ",
        "electrical power supply": "Էլեկտրական սնուցում",

    },
}


STATEMENT_TEMPLATES = {
    "ru": {
        "ignition / combustion": "Возможна проблема зажигания или сгорания. Проверьте цилиндровые данные и воспроизведение симптома при той же нагрузке.",
        "air-fuel / intake": "Возможен дисбаланс воздушно-топливной смеси или проблема впуска. Проверьте топливные коррекции, расход воздуха и герметичность впуска.",
        "mechanical cylinder condition": "Механическая причина цилиндровой неисправности остаётся возможной. Подтвердите или исключите её компрессией, leak-down и данными по фазам.",
        "LPG fuel delivery / mixture": "Симптом явно связан с работой на LPG. Проверьте давление газа, подачу форсунок и калибровку смеси до замены компонентов зажигания.",
        "LPG fuel delivery": "Проверьте давление LPG, стабильность подачи и работу форсунок в момент возникновения симптома.",
        "LPG injection": "Проверьте баланс и производительность LPG-форсунок по цилиндрам.",
        "ignition under LPG load": "Слабость системы зажигания может проявляться под повышенной нагрузкой LPG. Нужна цилиндровая проверка.",
        "ignition": "Система зажигания остаётся одной из возможных областей причины; подтвердите её измерениями.",
        "intake": "Нарушение герметичности или дисбаланс впуска может влиять на симптом. Проверьте впуск и данные смеси.",
        "load-dependent behavior": "Симптом зависит от режима работы. Воспроизведите его с синхронными данными RPM и нагрузки.",
        "load-dependent combustion": "Проблема сгорания может проявляться именно под нагрузкой. Сопоставьте цилиндровые данные с RPM и нагрузкой.",
        "idle stability / air-fuel control": "Нестабильность холостого хода требует разделить вклад воздуха, смеси, зажигания и механического состояния.",
        "oil / combustion condition": "Есть признаки, связанные с маслом или сгоранием; отделите вентиляцию картера, масло и механическое состояние.",
        "lean mixture": "Зафиксировано условие бедной смеси. Разделите подсос воздуха, недостаток топлива и ошибку измерения воздуха.",
        "rich mixture": "Зафиксировано условие богатой смеси. Разделите избыточную подачу топлива и ошибку измерения воздуха/лямбда-контроля.",
        "air metering / MAF": "Есть сигнал проблемы измерения воздуха. Проверьте правдоподобность MAF, проводку и негерметичный воздух.",
        "coolant temperature sensing": "Есть подозрение на измерение температуры охлаждающей жидкости. Сравните ECU-показание с независимым измерением.",
        "oxygen sensor / fuel feedback": "Проверьте поведение кислородного датчика и обратную связь по смеси перед заменой датчика.",
        "catalyst efficiency": "Контроль эффективности катализатора требует проверки поведения обоих кислородных датчиков и условий мониторинга.",
        "cam/crank correlation": "Есть признак проблемы корреляции распредвала и коленвала. Проверьте синхронизацию до механического вмешательства.",
        "transmission control / gear ratio": "Есть отклонение управления передачей или передаточного отношения. Сопоставьте заданную и фактическую передачу и проскальзывание.",
        "power supply / voltage": "Есть признак нестабильного напряжения. Проверьте аккумулятор, зарядку и стабильность напряжения под нагрузкой.",
        "vehicle network communication": "Есть проблема связи по сети автомобиля. Проверьте шину, питание, массы, доступность ECU и маршрутизацию gateway.",
        "starting system / engine start": "Проблема запуска требует разделить сигнал оборотов, питание, авторизацию, топливо и зажигание.",
        "engine stalling": "Остановку двигателя нужно сопоставить с RPM, давлением топлива и состоянием ECU в момент события.",
        "cooling system": "Перегрев требует подтверждения фактической температуры, работы вентилятора и циркуляции охлаждающей жидкости.",
        "electrical power supply": "Электрический симптом нужно подтвердить измерениями аккумулятора и системы зарядки.",
    },
    "hy": {
        "ignition / combustion": "Հնարավոր է բոցավառման կամ այրման խնդիր։ Ստուգեք բալոնային տվյալները և ախտանշանի կրկնությունը նույն բեռնվածության պայմաններում։",
        "air-fuel / intake": "Հնարավոր է օդ-վառելիք խառնուրդի անհավասարակշռություն կամ ներծծման խնդիր։ Ստուգեք fuel trim-երը, օդի հոսքը և ներծծման հերմետիկությունը։",
        "mechanical cylinder condition": "Մխոցի մեխանիկական պատճառը դեռ հնարավոր է։ Այն հաստատելու կամ բացառելու համար ստուգեք կոմպրեսիան, leak-down-ը և ֆազերի տվյալները։",
        "LPG fuel delivery / mixture": "Ախտանշանը հստակ կապված է LPG աշխատանքի հետ։ Ստուգեք գազի ճնշումը, ֆորսունկաների մատակարարումը և խառնուրդի կարգավորումը՝ բոցավառման բաղադրիչները փոխելուց առաջ։",
        "LPG fuel delivery": "Ստուգեք LPG ճնշումը, մատակարարման կայունությունը և ֆորսունկաների աշխատանքը ախտանշանի պահին։",
        "LPG injection": "Ստուգեք LPG ֆորսունկաների հավասարակշռությունը և արտադրողականությունը ըստ բալոնների։",
        "ignition under LPG load": "Թույլ բոցավառման համակարգը կարող է դրսևորվել LPG-ի բարձր բեռնվածության ժամանակ։ Անհրաժեշտ է բալոնային ստուգում։",
        "ignition": "Բոցավառման համակարգը շարունակում է մնալ հնարավոր պատճառների շարքում․ հաստատեք չափումներով։",
        "intake": "Ներծծման հերմետիկության խախտումը կամ անհավասարակշռությունը կարող է ազդել ախտանշանի վրա։ Ստուգեք ներծծումը և խառնուրդի տվյալները։",
        "load-dependent behavior": "Ախտանշանը կախված է աշխատանքի ռեժիմից։ Կրկնեք այն՝ համաժամանակյա RPM և բեռնվածության տվյալներով։",
        "load-dependent combustion": "Այրման խնդիրը կարող է դրսևորվել հենց բեռնվածության ժամանակ։ Համադրեք բալոնային տվյալները RPM-ի և բեռնվածության հետ։",
        "idle stability / air-fuel control": "Պարապ ընթացքի անկայունությունը պետք է բաժանել օդի, խառնուրդի, բոցավառման և մեխանիկական պատճառների միջև։",
        "oil / combustion condition": "Կան յուղի կամ այրման հետ կապված նշաններ․ տարանջատեք կարտերի օդափոխությունը, յուղը և մեխանիկական վիճակը։",
        "lean mixture": "Գրանցված է նիհար խառնուրդի պայման։ Տարանջատեք օդի արտահոսքը, վառելիքի պակասը և օդի չափման սխալը։",
        "rich mixture": "Գրանցված է հարուստ խառնուրդի պայման։ Տարանջատեք ավելցուկային վառելիքը օդի չափման կամ lambda կառավարման սխալից։",
        "air metering / MAF": "Կա օդի չափման համակարգի խնդրի նշան։ Ստուգեք MAF-ի տրամաբանությունը, լարերը և չչափված օդը։",
        "coolant temperature sensing": "Կա հովացուցիչ հեղուկի ջերմաստիճանի չափման կասկած։ Համեմատեք ECU-ի արժեքը անկախ չափման հետ։",
        "oxygen sensor / fuel feedback": "Մինչ սենսորը փոխելը ստուգեք թթվածնի սենսորի աշխատանքը և խառնուրդի հետադարձ կապը։",
        "catalyst efficiency": "Կատալիզատորի արդյունավետության ստուգումը պահանջում է երկու թթվածնի սենսորների աշխատանքի և մոնիթորինգի պայմանների գնահատում։",
        "cam/crank correlation": "Կա ռասպրեդվալ-կոլենվալ համաժամացման խնդրի նշան։ Մեխանիկական միջամտությունից առաջ ստուգեք համաժամացումը։",
        "transmission control / gear ratio": "Կա փոխանցման կառավարման կամ փոխանցման հարաբերակցության շեղում։ Համադրեք պահանջված և իրական փոխանցումն ու սայթաքումը։",
        "power supply / voltage": "Կա լարման անկայունության նշան։ Ստուգեք մարտկոցը, լիցքավորումը և լարման կայունությունը բեռնվածության տակ։",
        "vehicle network communication": "Կա մեքենայի ցանցային կապի խնդիր։ Ստուգեք շինան, սնուցումը, զանգվածները, ECU հասանելիությունը և gateway-ի երթուղին։",
        "starting system / engine start": "Գործարկման խնդիրը պետք է բաժանել RPM ազդանշանի, սնուցման, թույլտվության, վառելիքի և բոցավառման միջև։",
        "engine stalling": "Շարժիչի կանգը պետք է համադրել RPM-ի, վառելիքի ճնշման և ECU վիճակի հետ դեպքի պահին։",
        "cooling system": "Գերտաքացումը պետք է հաստատել իրական ջերմաստիճանով, օդափոխիչի աշխատանքի և հովացուցիչ հեղուկի շրջանառության ստուգմամբ։",
        "electrical power supply": "Էլեկտրական ախտանշանը պետք է հաստատել մարտկոցի և լիցքավորման համակարգի չափումներով։",
    },
}


RECOMMENDATION_TRANSLATIONS = {
    "ru": {
        "Measure LPG pressure at idle and under load": ("Измерить давление LPG на холостом ходу и под нагрузкой", "Проверить стабильность давления газа в диапазоне, где проявляется симптом."),
        "Compare STFT/LTFT on petrol versus LPG": ("Сравнить STFT/LTFT на бензине и LPG", "Отделить специфическую проблему смеси LPG от общей проблемы управления двигателем."),
        "Compare LPG injector contribution / balance": ("Сравнить вклад / баланс LPG-форсунок", "Проверить, получает ли один цилиндр заметно отличающуюся подачу LPG."),
        "Compare cylinder misfire counters under the same load": ("Сравнить счётчики пропусков по цилиндрам при одинаковой нагрузке", "Определить, остаётся ли событие локальным для конкретного цилиндра."),
        "Check ignition performance under controlled load": ("Проверить зажигание под контролируемой нагрузкой", "Связать работу зажигания с точным RPM, нагрузкой и режимом топлива."),
        "Validate MAF signal against RPM/load plausibility": ("Проверить правдоподобность сигнала MAF относительно RPM/нагрузки", "Определить, соответствует ли сигнал MAF рабочей точке двигателя."),
        "Inspect intake and MAF wiring/connectors": ("Проверить впуск и проводку/разъёмы MAF", "Отделить проблемы проводки и разъёмов от проблемы самого сигнала датчика."),
        "Compare fuel-trim and misfire behavior by fuel mode": ("Сравнить fuel trim и пропуски по режимам топлива", "Отделить проблему топливной системы LPG от общей проблемы зажигания или нагрузки."),
        "Inspect LPG pressure and injector behavior under load": ("Проверить давление LPG и работу форсунок под нагрузкой", "Проверить, сохраняется ли стабильная подача газа в окне RPM/нагрузки симптома."),
        "Check ignition performance under LPG load": ("Проверить зажигание под нагрузкой LPG", "Определить, связана ли повышенная нагрузка на зажигание с пропусками."),
        "Inspect intake system for an air leak": ("Проверить впуск на подсос воздуха", "Проверить наличие неучтённого воздуха, который проявляется в заявленном режиме."),
        "Compare cylinder-specific misfire counters and compression evidence": ("Сравнить счётчики пропусков и компрессию по цилиндрам", "Определить, остаётся ли проблема локальной для цилиндра и есть ли механические признаки."),
        "Check for unmetered-air leak": ("Проверить подсос неучтённого воздуха", "Проверить наличие воздуха, поступающего в двигатель в обход ожидаемого измерения."),
        "Measure fuel pressure under load": ("Измерить давление топлива под нагрузкой", "Проверить, сохраняется ли необходимое давление топлива в момент возникновения симптома."),
        "Check injector leakage / fuel pressure": ("Проверить герметичность форсунок и давление топлива", "Отделить избыточную подачу топлива от проблемы давления."),
        "Compare lambda response and fuel trims": ("Сравнить отклик lambda и топливные коррекции", "Определить характер и устойчивость богатой смеси по обратной связи."),
        "Check O2 sensor response and heater behavior": ("Проверить отклик O2-сенсора и работу нагревателя", "Проверить скорость отклика, правдоподобность сигнала и работу нагревателя."),
        "Compare upstream/downstream O2 behavior after warm-up": ("Сравнить работу O2 до и после катализатора после прогрева", "Проверить условия мониторинга катализатора до вывода о его неисправности."),
        "Compare ECU coolant temperature with independent measurement": ("Сравнить температуру ECU с независимым измерением", "Отделить проблему датчика от фактического температурного состояния двигателя."),
        "Verify cooling fan command and actual fan operation": ("Проверить команду вентилятора и фактическую работу", "Определить, соответствует ли включение вентилятора измеренной температуре."),
        "Compare cam/crank correlation data and timing values": ("Сравнить корреляцию распредвала/коленвала и фазы", "Проверить синхронизацию до механического вмешательства."),
        "Compare commanded gear, actual gear and slip": ("Сравнить заданную и фактическую передачу и проскальзывание", "Определить характер отклонения передаточного отношения."),
        "Check transmission fluid temperature and pressure evidence": ("Проверить температуру ATF и данные давления", "Связать симптом с рабочей температурой и доступными гидравлическими данными."),
        "Measure battery voltage at rest and during crank": ("Измерить напряжение аккумулятора в покое и при запуске", "Проверить достаточность и стабильность напряжения при стартерной нагрузке."),
        "Measure charging voltage under electrical load": ("Измерить напряжение зарядки под электрической нагрузкой", "Проверить работу генератора и регулятора при нагрузке."),
        "Capture CAN traffic and verify ECU/gateway responses": ("Проверить CAN-трафик и ответы ECU/gateway", "Отделить проблемы шины, gateway и доступности ECU."),
        "Verify engine speed, battery voltage and start authorization": ("Проверить обороты двигателя, напряжение и разрешение запуска", "Разделить проблемы сигнала RPM, питания и авторизации."),
        "Correlate stall event with RPM, fuel pressure and ECU status": ("Сопоставить остановку с RPM, давлением топлива и состоянием ECU", "Определить область причины в момент остановки."),
        "Compare idle fuel trims, MAF/MAP and misfire counters": ("Сравнить топливные коррекции, MAF/MAP и счётчики пропусков на холостом ходу", "Разделить вклад воздуха, смеси, зажигания и механики.")
    },
    "hy": {
        "Compare fuel-trim and misfire behavior by fuel mode": ("Համեմատել fuel trim-ը և բացթողումները ըստ վառելիքի ռեժիմի", "Տարբերակել LPG վառելիքային խնդիրը ընդհանուր բոցավառման կամ բեռնվածության խնդրից։"),
        "Inspect LPG pressure and injector behavior under load": ("Ստուգել LPG ճնշումը և ֆորսունկաների աշխատանքը բեռնվածության տակ", "Ստուգել՝ արդյոք գազի մատակարարումը կայուն է մնում ախտանշանի RPM/բեռնվածության միջակայքում։"),
        "Check ignition performance under LPG load": ("Ստուգել բոցավառումը LPG բեռնվածության տակ", "Պարզել՝ արդյոք բոցավառման բարձր պահանջը կապված է բացթողումների հետ։"),
        "Inspect intake system for an air leak": ("Ստուգել ներծծման համակարգը օդի արտահոսքի համար", "Պարզել՝ կա՞ չչափված օդ, որը դրսևորվում է նշված ռեժիմում։"),
        "Compare cylinder-specific misfire counters and compression evidence": ("Համեմատել բալոնային բացթողումների հաշվիչներն ու կոմպրեսիան", "Պարզել՝ խնդիրը մնում է կոնկրետ բալոնին կապված և կա՞ մեխանիկական ապացույց։"),
        "Check for unmetered-air leak": ("Ստուգել չչափված օդի արտահոսքը", "Պարզել՝ կա՞ օդի արտահոսք, որը մտնում է շարժիչ՝ սպասվող չափումից դուրս։"),
        "Measure fuel pressure under load": ("Չափել վառելիքի ճնշումը բեռնվածության տակ", "Ստուգել՝ անհրաժեշտ վառելիքի ճնշումը պահպանվո՞ւմ է ախտանշանի պահին։"),
        "Check injector leakage / fuel pressure": ("Ստուգել ֆորսունկաների հոսակորուստը և վառելիքի ճնշումը", "Տարբերակել ավելցուկային վառելիքի մատակարարումը ճնշման խնդրից։"),
        "Compare lambda response and fuel trims": ("Համեմատել lambda-ի արձագանքը և fuel trim-երը", "Պարզել խառնուրդի բնույթը և հետադարձ կապի կայունությունը։"),
        "Check O2 sensor response and heater behavior": ("Ստուգել O2 սենսորի արձագանքը և տաքացուցիչի աշխատանքը", "Ստուգել արձագանքի արագությունը, ազդանշանի տրամաբանությունը և տաքացուցիչը։"),
        "Compare upstream/downstream O2 behavior after warm-up": ("Տաքանալուց հետո համեմատել կատալիզատորից առաջ և հետո O2-ի աշխատանքը", "Կատալիզատորի անսարքության եզրակացությունից առաջ ստուգել մոնիթորինգի պայմանները։"),
        "Compare ECU coolant temperature with independent measurement": ("Համեմատել ECU-ի հովացուցիչ հեղուկի ջերմաստիճանը անկախ չափման հետ", "Տարբերակել սենսորի խնդիրը շարժիչի իրական ջերմաստիճանից։"),
        "Verify cooling fan command and actual fan operation": ("Ստուգել օդափոխիչի հրամանը և փաստացի աշխատանքը", "Պարզել՝ օդափոխիչի միացումը համապատասխանում է չափված ջերմաստիճանին։"),
        "Compare cam/crank correlation data and timing values": ("Համեմատել ռասպրեդվալ/կոլենվալ համաժամացման և ֆազերի տվյալները", "Ստուգել համաժամացումը՝ մինչև մեխանիկական միջամտությունը։"),
        "Compare commanded gear, actual gear and slip": ("Համեմատել պահանջված և իրական փոխանցումն ու սայթաքումը", "Պարզել փոխանցման հարաբերակցության շեղման բնույթը։"),
        "Check transmission fluid temperature and pressure evidence": ("Ստուգել ATF-ի ջերմաստիճանը և ճնշման տվյալները", "Կապել ախտանշանը աշխատանքային ջերմաստիճանի և հասանելի հիդրավլիկ տվյալների հետ։"),
        "Measure battery voltage at rest and during crank": ("Չափել մարտկոցի լարումը հանգստի և մեկնարկի պահին", "Ստուգել լարման բավարարությունն ու կայունությունը մեկնարկիչի բեռնվածության տակ։"),
        "Measure charging voltage under electrical load": ("Չափել լիցքավորման լարումը էլեկտրական բեռնվածության տակ", "Ստուգել գեներատորի և կարգավորիչի աշխատանքը բեռնվածության ժամանակ։"),
        "Capture CAN traffic and verify ECU/gateway responses": ("Գրանցել CAN տրաֆիկը և ստուգել ECU/gateway-ի պատասխանները", "Տարբերակել շղթայի, gateway-ի և ECU հասանելիության խնդիրները։"),
        "Verify engine speed, battery voltage and start authorization": ("Ստուգել շարժիչի RPM-ը, մարտկոցի լարումը և գործարկման թույլտվությունը", "Տարբերակել RPM ազդանշանի, սնուցման և թույլտվության խնդիրները։"),
        "Correlate stall event with RPM, fuel pressure and ECU status": ("Շարժիչի կանգը համադրել RPM-ի, վառելիքի ճնշման և ECU վիճակի հետ", "Պարզել պատճառի հնարավոր տարածքը կանգի պահին։"),
        "Compare idle fuel trims, MAF/MAP and misfire counters": ("Պարապ ընթացքի ժամանակ համեմատել fuel trim-երը, MAF/MAP-ը և բացթողումների հաշվիչները", "Տարբերակել օդի, խառնուրդի, բոցավառման և մեխանիկական պատճառների ներդրումը։"),
    },
}


EVIDENCE_STATUS_LABELS = {
    "ru": {
        "reported": "заявлено",
        "measured": "измерено",
        "calculated": "рассчитано",
        "inferred": "выведено",
        "confirmed": "подтверждено",
        "rejected": "отклонено",
    },
    "hy": {
        "reported": "հայտարարված",
        "measured": "չափված",
        "calculated": "հաշվարկված",
        "inferred": "եզրակացված",
        "confirmed": "հաստատված",
        "rejected": "մերժված",
    },
}

AUDIT_EVENT_LABELS = {
    "ru": {
        "VEHICLE_UPDATED": "Автомобиль обновлён",
        "SYMPTOM_ADDED": "Добавлен симптом",
        "DTC_ADDED": "Добавлен DTC",
        "DTC_UPDATED": "DTC обновлён",
        "DTC_DELETED": "DTC удалён",
        "INTELLIGENCE_ANALYSIS_COMPLETED": "Диагностический анализ завершён",
        "DECISION_PLAN_UPDATED": "План диагностики обновлён",
        "TEST_RESULT_INTERPRETED": "Результат теста интерпретирован",
        "LIVE_DATA_SAMPLES_RECEIVED": "Получены Live Data",
        "TELEMETRY_ANALYSIS_COMPLETED": "Анализ телеметрии завершён",
        "DEVICE_BOUND": "Диагностическое устройство подключено",
        "VIN_RECEIVED": "VIN получен",
        "OBD_SESSION_SYNC": "OBD-сессия синхронизирована",
        "QUESTIONS_IDENTIFIED": "Выявлены вопросы для дальнейшей диагностики",
    },
    "hy": {
        "VEHICLE_UPDATED": "Մեքենայի տվյալները թարմացվել են",
        "SYMPTOM_ADDED": "Ավելացվել է ախտանշան",
        "DTC_ADDED": "Ավելացվել է DTC",
        "DTC_UPDATED": "DTC-ն թարմացվել է",
        "DTC_DELETED": "DTC-ն ջնջվել է",
        "INTELLIGENCE_ANALYSIS_COMPLETED": "Ախտորոշիչ վերլուծությունն ավարտվել է",
        "DECISION_PLAN_UPDATED": "Ախտորոշման պլանը թարմացվել է",
        "TEST_RESULT_INTERPRETED": "Թեստի արդյունքը մեկնաբանվել է",
        "LIVE_DATA_SAMPLES_RECEIVED": "Ստացվել են Live Data տվյալներ",
        "TELEMETRY_ANALYSIS_COMPLETED": "Տելեմետրիայի վերլուծությունն ավարտվել է",
        "DEVICE_BOUND": "Ախտորոշիչ սարքը միացվել է",
        "VIN_RECEIVED": "VIN-ը ստացվել է",
        "OBD_SESSION_SYNC": "OBD սեսիան համաժամացվել է",
        "QUESTIONS_IDENTIFIED": "Հաջորդ ախտորոշման հարցերը հայտնաբերվել են",
    },
}

def _localized_evidence_status(status: str, language: str) -> str:
    return EVIDENCE_STATUS_LABELS.get(language, {}).get(status, status)

def _localized_event(event: str, language: str) -> str:
    return AUDIT_EVENT_LABELS.get(language, {}).get(event, event)

def _localized_test_result_fact(fact: str, language: str) -> str:
    # Support the original compact evidence string and the richer test-result
    # evidence written by DiagnosticIntelligenceEngine. Keep notes/measurements
    # visible instead of dropping information from the technician's submission.
    legacy = re.match(r"^Test ([^ ]+) result: (PASS|FAIL|UNKNOWN|INCOMPLETE)$", fact)
    detailed = re.match(
        r"^Completed diagnostic test(?:: (.+?)| ID: ([^;]+));\s*result:\s*(PASS|FAIL|UNKNOWN|INCOMPLETE)(?:;\s*(.*))?$",
        fact,
    )
    if legacy:
        test_label = legacy.group(1)
        result_value = legacy.group(2)
        details = ""
    elif detailed:
        test_label = (detailed.group(1) or detailed.group(2) or "").strip()
        result_value = detailed.group(3)
        details = (detailed.group(4) or "").strip()
    else:
        return fact

    result_labels = {
        "ru": {
            "PASS": "ПРОЙДЕН",
            "FAIL": "НЕ ПРОЙДЕН",
            "UNKNOWN": "НЕИЗВЕСТНО",
            "INCOMPLETE": "НЕ ЗАВЕРШЁН",
        },
        "hy": {
            "PASS": "ԱՆՑԱՎ",
            "FAIL": "ՉԱՆՑԱՎ",
            "UNKNOWN": "ԱՆՀԱՅՏ",
            "INCOMPLETE": "ԱՆԱՎԱՐՏ",
        },
    }
    prefix = {"ru": "Результат теста", "hy": "Թեստի արդյունք"}.get(language, "Test result")
    localized = f"{prefix} {test_label}: {result_labels.get(language, {}).get(result_value, result_value)}"
    if details:
        localized = f"{localized}; {details}"
    return localized


HYPOTHESIS_LABELS = {
    "ru": {
        "LPG injection": "Форсунки LPG",
        "LPG calibration": "Калибровка LPG",
        "ignition under LPG load": "Зажигание под нагрузкой LPG",
        "ignition": "Зажигание",
        "load-dependent combustion": "Сгорание под нагрузкой",
        "intake": "Впуск",
        "lean mixture": "Бедная смесь",
        "rich mixture": "Богатая смесь",
        "oxygen sensor / fuel feedback": "Лямбда-зонд / обратная связь по смеси",
        "catalyst efficiency": "Эффективность катализатора",
        "coolant temperature sensing": "Датчик температуры охлаждающей жидкости",
        "cooling system": "Система охлаждения",
        "cam/crank correlation": "Синхронизация распредвала / коленвала",
        "transmission control / gear ratio": "Управление АКПП / передаточное отношение",
        "power supply / voltage": "Питание / напряжение",
        "electrical power supply": "Электропитание",
        "vehicle network communication": "Связь по сети автомобиля",
        "starting system / engine start": "Система запуска двигателя",
        "engine stalling": "Остановка двигателя",
        "air metering / MAF": "Измерение воздуха / MAF",
        "idle stability / air-fuel control": "Стабильность холостого хода / управление смесью",
    },
    "hy": {
        "LPG injection": "LPG ֆորսունկաներ",
        "LPG calibration": "LPG կարգավորում",
        "ignition under LPG load": "Բոցավառում LPG բեռնվածության տակ",
        "ignition": "Բոցավառում",
        "load-dependent combustion": "Այրում բեռնվածության տակ",
        "intake": "Ներծծման համակարգ",
        "lean mixture": "Նիհար խառնուրդ",
        "rich mixture": "Հարուստ խառնուրդ",
        "oxygen sensor / fuel feedback": "Թթվածնի սենսոր / վառելիքի հետադարձ կապ",
        "catalyst efficiency": "Կատալիզատորի արդյունավետություն",
        "coolant temperature sensing": "Հովացուցիչ հեղուկի ջերմաստիճանի չափում",
        "cooling system": "Սառեցման համակարգ",
        "cam/crank correlation": "Ռասպրեդվալ / կոլենվալ համաժամացում",
        "transmission control / gear ratio": "Ավտոմատ փոխանցման կառավարում / փոխանցման հարաբերակցություն",
        "power supply / voltage": "Սնուցում / լարում",
        "electrical power supply": "Էլեկտրական սնուցում",
        "vehicle network communication": "Մեքենայի ցանցային կապ",
        "starting system / engine start": "Գործարկման համակարգ / շարժիչի մեկնարկ",
        "engine stalling": "Շարժիչի կանգ",
        "air metering / MAF": "Օդի չափում / MAF",
        "idle stability / air-fuel control": "Պարապ ընթացքի կայունություն / խառնուրդի կառավարում",
    },
}

def _localized_hypothesis_targets(targets: list[str], language: str) -> list[str]:
    mapping = HYPOTHESIS_LABELS.get(language, {})
    return [mapping.get(item, CATEGORY_LABELS.get(language, {}).get(item, item)) for item in targets]

PREREQUISITE_LABELS = {
    "ru": {
        "fuel_mode_lpg": "режим работы LPG",
        "petrol normal": "нормальная работа на бензине",
        "misfire": "пропуски зажигания",
    },
    "hy": {
        "fuel_mode_lpg": "LPG աշխատանքի ռեժիմ",
        "petrol normal": "բենզինով նորմալ աշխատանք",
        "misfire": "բոցավառման բացթողումներ",
    },
}

for _lang, _items in {
    "hy": {"fuel_mode_petrol": "Բենզինի ռեժիմ", "fuel_mode_lpg": "LPG ռեժիմ", "petrol_normal": "Բենզինով նորմալ աշխատանք", "acceleration": "Արագացում / բեռնվածություն", "below_2000_rpm": "2000 RPM-ից ցածր", "misfire": "Այրման բացթողումներ"},
    "ru": {"fuel_mode_petrol": "Работа на бензине", "fuel_mode_lpg": "Режим LPG", "petrol_normal": "Нормальная работа на бензине", "acceleration": "Разгон / нагрузка", "below_2000_rpm": "Ниже 2000 RPM", "misfire": "Пропуски воспламенения"},
}.items():
    PREREQUISITE_LABELS[_lang].update(_items)

def _localized_prerequisite(value: str, language: str) -> str:
    return PREREQUISITE_LABELS.get(language, {}).get(value, value)

def _localized_safety_note(note: str, language: str) -> str:
    if language == "ru":
        return {
            "Follow LPG system manufacturer procedures; avoid leaks and ignition sources.": "Следуйте процедурам производителя LPG; исключите утечки и источники воспламенения.",
            "Use insulated/properly rated test equipment and follow workshop ignition-safety procedures.": "Используйте изолированное/подходящее по классу измерительное оборудование и соблюдайте правила безопасности при работе с зажиганием.",
            "Use the approved leak-test procedure and protect hot/electrical components.": "Используйте утверждённую процедуру проверки утечек и защищайте горячие/электрические компоненты.",
            "Compression testing requires proper engine shutdown and manufacturer procedures.": "Проверка компрессии требует правильной остановки двигателя и соблюдения процедур производителя.",
        }.get(note, note)
    if language == "hy":
        return {
            "Follow LPG system manufacturer procedures; avoid leaks and ignition sources.": "Հետևեք LPG համակարգի արտադրողի ընթացակարգերին, բացառեք արտահոսքերը և բոցավառման աղբյուրները։",
            "Use insulated/properly rated test equipment and follow workshop ignition-safety procedures.": "Օգտագործեք մեկուսացված/համապատասխան դասի չափիչ սարքավորում և պահպանեք բոցավառման համակարգի անվտանգության կանոնները։",
            "Use the approved leak-test procedure and protect hot/electrical components.": "Օգտագործեք արտահոսքի ստուգման հաստատված ընթացակարգը և պաշտպանեք տաք/էլեկտրական բաղադրիչները։",
            "Compression testing requires proper engine shutdown and manufacturer procedures.": "Կոմպրեսիայի ստուգումը պահանջում է շարժիչի ճիշտ կանգնեցում և արտադրողի ընթացակարգերի պահպանում։",
        }.get(note, note)
    return note


# All deterministic recommendation texts used by the rules engine. Keep these
# complete so a requested app language never silently falls back to English.
for _lang, _entries in {
    "ru": {
        "Measure LPG pressure at idle and under load": ("Измерить давление LPG на холостом ходу и под нагрузкой", "Определить, сохраняется ли стабильное давление газа в момент возникновения симптома."),
        "Compare STFT/LTFT on petrol versus LPG": ("Сравнить STFT/LTFT на бензине и LPG", "Отделить специфическую проблему топливной системы от общей проблемы управления двигателем."),
        "Compare LPG injector contribution / balance": ("Сравнить вклад и баланс форсунок LPG", "Проверить, получает ли один цилиндр заметно отличающуюся подачу LPG."),
        "Compare cylinder misfire counters under the same load": ("Сравнить счётчики пропусков по цилиндрам при одинаковой нагрузке", "Определить, остаётся ли событие локальным для одного цилиндра и в каком режиме топлива оно возникает."),
        "Check ignition performance under controlled load": ("Проверить работу зажигания под контролируемой нагрузкой", "Сопоставить работу зажигания с точным диапазоном RPM, нагрузки и топлива, где возникает пропуск."),
        "Validate MAF signal against RPM/load plausibility": ("Проверить правдоподобность сигнала MAF относительно RPM и нагрузки", "Определить, соответствует ли сигнал расхода воздуха режиму работы двигателя."),
        "Inspect intake and MAF wiring/connectors": ("Проверить впуск и проводку/разъёмы MAF", "Отделить проблему проводки и разъёмов от проблемы самого сигнала датчика."),
        "Check for unmetered-air leak": ("Проверить подсос неучтённого воздуха", "Проверить наличие воздуха, поступающего в двигатель в обход ожидаемого измерения."),
        "Measure fuel pressure under load": ("Измерить давление топлива под нагрузкой", "Проверить, сохраняется ли необходимое давление топлива в момент возникновения симптома."),
        "Check injector leakage / fuel pressure": ("Проверить герметичность форсунок и давление топлива", "Отделить избыточную подачу топлива от проблемы давления или обратной связи."),
        "Compare lambda response and fuel trims": ("Сравнить отклик lambda и топливные коррекции", "Определить характер и устойчивость состояния смеси по обратной связи."),
        "Check O2 sensor response and heater behavior": ("Проверить отклик O2-сенсора и работу нагревателя", "Проверить скорость отклика, правдоподобность сигнала и работу нагревателя."),
        "Compare upstream/downstream O2 behavior after warm-up": ("Сравнить работу O2 до и после катализатора после прогрева", "Проверить условия мониторинга катализатора до вывода о его неисправности."),
        "Compare ECU coolant temperature with independent measurement": ("Сравнить температуру ECU с независимым измерением", "Отделить проблему датчика от фактического температурного состояния двигателя."),
        "Verify cooling fan command and actual fan operation": ("Проверить команду вентилятора и фактическую работу", "Определить, соответствует ли включение вентилятора измеренной температуре."),
        "Compare cam/crank correlation data and timing values": ("Сравнить корреляцию распредвала/коленвала и значения фаз", "Проверить синхронизацию до механического вмешательства."),
        "Compare commanded gear, actual gear and slip": ("Сравнить заданную и фактическую передачу и проскальзывание", "Определить характер отклонения передаточного отношения."),
        "Check transmission fluid temperature and pressure evidence": ("Проверить температуру ATF и данные давления", "Связать симптом с рабочей температурой и доступными гидравлическими данными."),
        "Measure battery voltage at rest and during crank": ("Измерить напряжение аккумулятора в покое и при запуске", "Проверить достаточность и стабильность напряжения при стартерной нагрузке."),
        "Measure charging voltage under electrical load": ("Измерить напряжение зарядки под электрической нагрузкой", "Проверить работу генератора и регулятора при нагрузке."),
        "Capture CAN traffic and verify ECU/gateway responses": ("Проверить CAN-трафик и ответы ECU/gateway", "Отделить проблемы шины, gateway и доступности ECU."),
        "Verify engine speed, battery voltage and start authorization": ("Проверить обороты двигателя, напряжение и разрешение запуска", "Разделить проблемы сигнала RPM, питания и авторизации."),
        "Correlate stall event with RPM, fuel pressure and ECU status": ("Сопоставить остановку с RPM, давлением топлива и состоянием ECU", "Определить область причины в момент остановки."),
        "Compare idle fuel trims, MAF/MAP and misfire counters": ("Сравнить топливные коррекции, MAF/MAP и счётчики пропусков на холостом ходу", "Разделить вклад воздуха, смеси, зажигания и механики."),
        "Collect baseline live data and reproduce the symptom": ("Собрать базовые Live Data и воспроизвести симптом", "Получить синхронизированные RPM, нагрузку, температуру и релевантные данные до сужения области неисправности."),
        "Read ECU DTCs and freeze-frame data": ("Считать DTC ECU и freeze-frame данные", "Получить данные, сообщённые ECU, и условия работы, связанные с событием."),
    },
    "hy": {
        "Measure LPG pressure at idle and under load": ("Չափել LPG ճնշումը պարապ ընթացքի և բեռնվածության տակ", "Պարզել՝ արդյոք գազի ճնշումը կայուն է մնում ախտանշանի պահին։"),
        "Compare STFT/LTFT on petrol versus LPG": ("Համեմատել STFT/LTFT-ը բենզինով և LPG-ով", "Տարբերակել վառելիքային համակարգին հատուկ խնդիրը շարժիչի ընդհանուր կառավարման խնդրից։"),
        "Compare LPG injector contribution / balance": ("Համեմատել LPG ֆորսունկաների ներդրումն ու հավասարակշռությունը", "Ստուգել՝ արդյոք որևէ բալոն ստանում է էապես տարբեր LPG մատակարարում։"),
        "Compare cylinder misfire counters under the same load": ("Համեմատել բալոնների բացթողումների հաշվիչները նույն բեռնվածության դեպքում", "Պարզել՝ արդյոք խնդիրը մնում է մեկ բալոնին կապված և որ վառելիքի ռեժիմում է առաջանում։"),
        "Check ignition performance under controlled load": ("Ստուգել բոցավառումը վերահսկվող բեռնվածության տակ", "Համադրել բոցավառման աշխատանքը RPM-ի, բեռնվածության և վառելիքի այն պայմանների հետ, որտեղ առաջանում է բացթողումը։"),
        "Validate MAF signal against RPM/load plausibility": ("Ստուգել MAF ազդանշանի համապատասխանությունը RPM/բեռնվածությանը", "Պարզել՝ օդի հոսքի ազդանշանը համապատասխանում է շարժիչի աշխատանքի ռեժիմին, թե ոչ։"),
        "Inspect intake and MAF wiring/connectors": ("Ստուգել ներծծման համակարգը և MAF-ի լարերը/միակցիչները", "Տարբերակել լարերի ու միակցիչների խնդիրը հենց սենսորի ազդանշանի խնդրից։"),
        "Check for unmetered-air leak": ("Ստուգել չչափված օդի արտահոսքը", "Պարզել՝ կա՞ օդի արտահոսք, որը մտնում է շարժիչ՝ սպասվող չափումից դուրս։"),
        "Measure fuel pressure under load": ("Չափել վառելիքի ճնշումը բեռնվածության տակ", "Ստուգել՝ արդյոք անհրաժեշտ վառելիքի ճնշումը պահպանվում է ախտանշանի պահին։"),
        "Check injector leakage / fuel pressure": ("Ստուգել ֆորսունկաների հոսակորուստը և վառելիքի ճնշումը", "Տարբերակել ավելցուկային վառելիքի մատակարարումը ճնշման կամ հետադարձ կապի խնդրից։"),
        "Compare lambda response and fuel trims": ("Համեմատել lambda-ի արձագանքը և fuel trim-երը", "Պարզել խառնուրդի վիճակի բնույթը և հետադարձ կապի կայունությունը։"),
        "Check O2 sensor response and heater behavior": ("Ստուգել O2 սենսորի արձագանքը և տաքացուցիչի աշխատանքը", "Ստուգել արձագանքի արագությունը, ազդանշանի տրամաբանությունը և տաքացուցիչը։"),
        "Compare upstream/downstream O2 behavior after warm-up": ("Տաքանալուց հետո համեմատել կատալիզատորից առաջ և հետո O2-ի աշխատանքը", "Կատալիզատորի անսարքության եզրակացությունից առաջ ստուգել մոնիթորինգի պայմանները։"),
        "Compare ECU coolant temperature with independent measurement": ("Համեմատել ECU-ի հովացուցիչ հեղուկի ջերմաստիճանը անկախ չափման հետ", "Տարբերակել սենսորի խնդիրը շարժիչի իրական ջերմաստիճանից։"),
        "Verify cooling fan command and actual fan operation": ("Ստուգել օդափոխիչի հրամանը և փաստացի աշխատանքը", "Պարզել՝ օդափոխիչի միացումը համապատասխանում է չափված ջերմաստիճանին։"),
        "Compare cam/crank correlation data and timing values": ("Համեմատել ռասպրեդվալ/կոլենվալ համաժամացման և ֆազերի տվյալները", "Ստուգել համաժամացումը՝ մինչև մեխանիկական միջամտությունը։"),
        "Compare commanded gear, actual gear and slip": ("Համեմատել պահանջված և իրական փոխանցումն ու սայթաքումը", "Պարզել փոխանցման հարաբերակցության շեղման բնույթը։"),
        "Check transmission fluid temperature and pressure evidence": ("Ստուգել ATF-ի ջերմաստիճանը և ճնշման տվյալները", "Կապել ախտանշանը աշխատանքային ջերմաստիճանի և հասանելի հիդրավլիկ տվյալների հետ։"),
        "Measure battery voltage at rest and during crank": ("Չափել մարտկոցի լարումը հանգստի և մեկնարկի պահին", "Ստուգել լարման բավարարությունն ու կայունությունը մեկնարկիչի բեռնվածության տակ։"),
        "Measure charging voltage under electrical load": ("Չափել լիցքավորման լարումը էլեկտրական բեռնվածության տակ", "Ստուգել գեներատորի և կարգավորիչի աշխատանքը բեռնվածության ժամանակ։"),
        "Capture CAN traffic and verify ECU/gateway responses": ("Գրանցել CAN տրաֆիկը և ստուգել ECU/gateway-ի պատասխանները", "Տարբերակել շղթայի, gateway-ի և ECU հասանելիության խնդիրները։"),
        "Verify engine speed, battery voltage and start authorization": ("Ստուգել շարժիչի RPM-ը, մարտկոցի լարումը և գործարկման թույլտվությունը", "Տարբերակել RPM ազդանշանի, սնուցման և թույլտվության խնդիրները։"),
        "Correlate stall event with RPM, fuel pressure and ECU status": ("Շարժիչի կանգը համադրել RPM-ի, վառելիքի ճնշման և ECU վիճակի հետ", "Պարզել պատճառի հնարավոր տարածքը կանգի պահին։"),
        "Compare idle fuel trims, MAF/MAP and misfire counters": ("Պարապ ընթացքի ժամանակ համեմատել fuel trim-երը, MAF/MAP-ը և բացթողումների հաշվիչները", "Տարբերակել օդի, խառնուրդի, բոցավառման և մեխանիկական պատճառների ներդրումը։"),
        "Collect baseline live data and reproduce the symptom": ("Հավաքել հիմնական Live Data-ն և վերարտադրել ախտանշանը", "Ստանալ համաժամացված RPM, բեռնվածություն, ջերմաստիճան և համապատասխան սենսորային տվյալներ՝ պատճառի շրջանակը նեղացնելուց առաջ։"),
        "Read ECU DTCs and freeze-frame data": ("Կարդալ ECU DTC-ները և freeze-frame տվյալները", "Ստանալ ECU-ի գրանցած ապացույցները և դեպքի հետ կապված աշխատանքային պայմանները։"),
    },
}.items():
    RECOMMENDATION_TRANSLATIONS[_lang].update(_entries)

RECOMMENDATION_STATUS_TRANSLATIONS = {
    "ru": {"PASS": "ПРОЙДЕН", "FAIL": "НЕ ПРОЙДЕН", "INCONCLUSIVE": "НЕОДНОЗНАЧНО", "NOT_TESTED": "НЕ ТЕСТИРОВАЛОСЬ", "INCOMPLETE": "НЕ ЗАВЕРШЁН"},
    "hy": {"PASS": "ԱՆՑԱՎ", "FAIL": "ՉԱՆՑԱՎ", "INCONCLUSIVE": "ԱՆՈՐՈՇ", "NOT_TESTED": "ՉԻ ԹԵՍՏԱՎՈՐՎԵԼ", "INCOMPLETE": "ԱՆԱՎԱՐՏ"},
}

def _localized_safety_note(note: str, language: str) -> str:
    if language == "ru":
        return {
            "Follow LPG system manufacturer procedures; avoid leaks and ignition sources.": "Соблюдайте процедуры производителя LPG; исключите утечки и источники воспламенения.",
            "Follow LPG system manufacturer procedures.": "Соблюдайте процедуры производителя LPG.",
            "Perform on a secure vehicle with appropriate workshop precautions.": "Закрепите автомобиль и соблюдайте меры безопасности мастерской.",
            "Use insulated/properly rated test equipment and follow workshop ignition-safety procedures.": "Используйте изолированное оборудование с подходящими характеристиками и соблюдайте правила безопасности при работе с зажиганием.",
            "Use the approved leak-test procedure and protect hot/electrical components.": "Используйте утверждённую процедуру проверки утечек и защищайте горячие и электрические компоненты.",
            "Compression testing requires proper engine shutdown and manufacturer procedures.": "Для проверки компрессии требуется корректно заглушить двигатель и соблюдать процедуры производителя.",
        }.get(note, note)
    if language == "hy":
        return {
            "Follow LPG system manufacturer procedures; avoid leaks and ignition sources.": "Հետևեք LPG համակարգի արտադրողի ընթացակարգերին և բացառեք արտահոսքն ու բռնկման աղբյուրները։",
            "Follow LPG system manufacturer procedures.": "Հետևեք LPG համակարգի արտադրողի ընթացակարգերին։",
            "Perform on a secure vehicle with appropriate workshop precautions.": "Ամրացրեք մեքենան և պահպանեք արհեստանոցի անվտանգության կանոնները։",
            "Use insulated/properly rated test equipment and follow workshop ignition-safety procedures.": "Օգտագործեք համապատասխան մեկուսացված չափիչ սարքավորում և պահպանեք բոցավառման համակարգի աշխատանքի անվտանգության կանոնները։",
            "Use the approved leak-test procedure and protect hot/electrical components.": "Օգտագործեք հաստատված արտահոսքի ստուգման ընթացակարգը և պաշտպանեք տաք ու էլեկտրական բաղադրիչները։",
            "Compression testing requires proper engine shutdown and manufacturer procedures.": "Կոմպրեսիայի ստուգման համար ճիշտ անջատեք շարժիչը և հետևեք արտադրողի ընթացակարգերին։",
        }.get(note, note)
    return note


def _localized_evidence_fact(fact: str, language: str) -> str:
    match = re.match(r"^Test ([0-9a-fA-F-]+) result: (.+)$", fact)
    if not match or language == "en":
        return fact
    result = RECOMMENDATION_STATUS_TRANSLATIONS.get(language, {}).get(match.group(2), match.group(2))
    prefix = "Результат теста" if language == "ru" else "Թեստի արդյունք"
    return f"{prefix} {match.group(1)}: {result}"

def normalize_language(language: str | None) -> str:
    return LANGUAGE_ALIASES.get((language or "en").strip().lower(), "en")


def _localized_status(status: str, language: str) -> str:
    if language == "en":
        return status
    if ":" in status:
        prefix, score = status.split(":", 1)
        suffix = f":{score}"
    else:
        prefix, suffix = status, ""
    labels = {
        "ru": {
            "possible": "возможно",
            "supported_by_test": "подтверждено тестом",
            "disfavored_by_test": "ослаблено тестом",
            "rejected": "отклонено",
        },
        "hy": {
            "possible": "հնարավոր",
            "supported_by_test": "աջակցվում է թեստով",
            "disfavored_by_test": "թուլացվել է թեստով",
            "rejected": "մերժված",
        },
    }
    return labels.get(language, {}).get(prefix, prefix) + suffix


def _localized_question(question: str, language: str) -> str:
    if language == "ru":
        return {
            "What is LPG gas pressure at idle and during the reported load/RPM window?": "Какое давление газа LPG на холостом ходу и в заявленном диапазоне нагрузки/RPM?",
            "What are STFT/LTFT values on petrol versus LPG at idle and under load?": "Какие значения STFT/LTFT на бензине и LPG на холостом ходу и под нагрузкой?",
        }.get(question, question)
    if language == "hy":
        return {
            "What is LPG gas pressure at idle and during the reported load/RPM window?": "Որքա՞ն է LPG-ի գազի ճնշումը պարապ ընթացքի և նշված RPM/բեռնվածության միջակայքում։",
            "What are STFT/LTFT values on petrol versus LPG at idle and under load?": "Որո՞նք են STFT/LTFT արժեքները բենզինով և LPG-ով պարապ ընթացքի ու բեռնվածության ժամանակ։",
        }.get(question, question)
    return question


def _localized_dtc_description(code: str, description: str | None, language: str) -> str | None:
    # Preserve custom notes. Only supply standard definitions when the caller did
    # not provide a description; the code itself never changes.
    if description or language == "en":
        return description
    cylinder = re.fullmatch(r"P030([1-8])", code.upper())
    if cylinder:
        return {"hy": f"{cylinder[1]}-րդ գլանում այրման բացթողում", "ru": f"Пропуски воспламенения в цилиндре {cylinder[1]}"}.get(language, description)
    labels = {
        "P0300": ("Պատահական կամ բազմագլան այրման բացթողումներ", "Случайные или множественные пропуски воспламенения"),
        "P0171": ("Աղքատ վառելիքային խառնուրդ՝ բանկ 1", "Бедная топливная смесь, банк 1"),
        "P0174": ("Աղքատ վառելիքային խառնուրդ՝ բանկ 2", "Бедная топливная смесь, банк 2"),
        "P0172": ("Հարուստ վառելիքային խառնուրդ՝ բանկ 1", "Богатая топливная смесь, банк 1"),
        "P0175": ("Հարուստ վառելիքային խառնուրդ՝ բանկ 2", "Богатая топливная смесь, банк 2"),
        "P0100": ("Օդի զանգվածային հոսքի սենսորի շղթա", "Цепь датчика массового расхода воздуха"),
        "P0101": ("Օդի զանգվածային հոսքի սենսորի աշխատանքի տիրույթ", "Диапазон / работа датчика массового расхода воздуха"),
        "P0115": ("Հովացուցիչ հեղուկի ջերմաստիճանի սենսորի շղթա", "Цепь датчика температуры охлаждающей жидкости"),
        "P0122": ("Դրոսելի դիրքի սենսորի ցածր մուտքային ազդանշան", "Низкий входной сигнал датчика положения дросселя"),
        "P0130": ("Թթվածնի սենսորի շղթա՝ բանկ 1, սենսոր 1", "Цепь датчика кислорода, банк 1, датчик 1"),
        "P0420": ("Կատալիզատորի արդյունավետությունը շեմից ցածր է՝ բանկ 1", "Эффективность катализатора ниже порога, банк 1"),
        "P0430": ("Կատալիզատորի արդյունավետությունը շեմից ցածր է՝ բանկ 2", "Эффективность катализатора ниже порога, банк 2"),
        "P0562": ("Համակարգի ցածր լարում", "Низкое напряжение системы"),
        "P0700": ("Փոխանցման կառավարման համակարգի անսարքության ազդանշան", "Сигнал неисправности системы управления трансмиссией"),
        "U0100": ("Շարժիչի կառավարման մոդուլի հետ կապի կորուստ", "Потеря связи с модулем управления двигателем"),
    }
    label = labels.get(code.upper())
    return label[0 if language == "hy" else 1] if label else description


def _localized_rationale(text: str, language: str) -> str:
    phrases = {
        "Required evidence is present.": ("Պահանջվող տվյալներն առկա են։", "Необходимые данные присутствуют."),
        "A prior test supports a related hypothesis; this follow-up can help isolate the cause.": ("Նախորդ թեստն աջակցում է հարակից վարկածին․ այս ստուգումը կօգնի առանձնացնել պատճառը։", "Предыдущий тест поддерживает связанную гипотезу; последующая проверка поможет выделить причину."),
        "A prior negative result lowers the priority of repeating checks aimed at this hypothesis.": ("Նախորդ բացասական արդյունքը նվազեցնում է այս վարկածի կրկնակի ստուգման առաջնահերթությունը։", "Предыдущий отрицательный результат снижает приоритет повторной проверки этой гипотезы."),
    }
    index = 0 if language == "hy" else 1
    if text in phrases:
        return phrases[text][index]
    if text.startswith("Targets "):
        targets = text[len("Targets "):].rstrip(".").split(", ")
        return ("Թիրախ՝ " if language == "hy" else "Цели: ") + ", ".join(_localized_hypothesis_targets(targets, language)) + "."
    if text.startswith("Estimated information gain: "):
        return ("Ակնկալվող տեղեկատվական արժեք՝ " if language == "hy" else "Ожидаемая информационная ценность: ") + text.split(": ", 1)[1]
    if text.startswith("Missing evidence: "):
        values = text[len("Missing evidence: "):].rstrip(".").split(", ")
        return ("Բացակայող տվյալներ՝ " if language == "hy" else "Недостающие данные: ") + ", ".join(_localized_prerequisite(value, language) for value in values) + "."
    return text


def localize_session_analysis(session: DiagnosticSession, language: str | None) -> DiagnosticSession:
    language = normalize_language(language)
    result = deepcopy(session)
    if language == "en":
        return result

    for code in result.dtcs:
        code.description = _localized_dtc_description(code.code, code.description, language)

    for hypothesis in result.hypotheses:
        original_category = hypothesis.category
        hypothesis.category = CATEGORY_LABELS.get(language, {}).get(original_category, original_category)
        template = STATEMENT_TEMPLATES.get(language, {}).get(original_category)
        if template:
            hypothesis.statement = template
        hypothesis.status = _localized_status(hypothesis.status, language)

    for recommendation in result.recommendations:
        translated = RECOMMENDATION_TRANSLATIONS.get(language, {}).get(recommendation.name)
        if translated:
            recommendation.name, recommendation.purpose = translated

        recommendation.safety_notes = [
            _localized_safety_note(note, language) for note in recommendation.safety_notes
        ]
        recommendation.prerequisites = [
            _localized_prerequisite(item, language) for item in recommendation.prerequisites
        ]
        recommendation.target_hypotheses = _localized_hypothesis_targets(
            recommendation.target_hypotheses, language
        )

    for test_result in result.test_results:
        translated = RECOMMENDATION_TRANSLATIONS.get(language, {}).get(test_result.test_name or "")
        if translated:
            test_result.test_name = translated[0]
        test_result.result_label = RECOMMENDATION_STATUS_TRANSLATIONS.get(language, {}).get(
            test_result.result.upper(), test_result.result
        )

    for evidence in result.evidence:
        if evidence.metadata.get("derived_from"):
            evidence.fact = _localized_prerequisite(evidence.fact, language)
        evidence.fact = _localized_test_result_fact(evidence.fact, language)

    for evidence in result.evidence:
        evidence.fact = _localized_evidence_fact(evidence.fact, language)

    for event in result.audit_log:
        event["event"] = _localized_event(event.get("event", ""), language)
        questions = event.get("questions")
        if questions:
            event["questions"] = [_localized_question(q, language) for q in questions]

    return result


def localize_decision_plan(plan, language):
    """Translate presentation text without mutating canonical plan IDs/scores."""
    language = normalize_language(language)
    result = plan.model_copy(deep=True)
    if language == 'en':
        return result
    for candidate in result.candidates:
        translated = RECOMMENDATION_TRANSLATIONS.get(language, {}).get(candidate.name)
        if translated:
            candidate.name, candidate.purpose = translated
        candidate.safety_notes = [_localized_safety_note(note, language) for note in candidate.safety_notes]
        candidate.prerequisite_gaps = [_localized_prerequisite(note, language) for note in candidate.prerequisite_gaps]
        candidate.rationale = [_localized_rationale(note, language) for note in candidate.rationale]
    messages = {
        'ru': {
            'No diagnostic hypotheses are available yet; run initial analysis first.': 'Диагностических гипотез пока нет; сначала выполните анализ.',
            'No unused diagnostic test has sufficient expected value for the current hypotheses.': 'Для текущих гипотез нет дополнительных тестов с достаточной ожидаемой ценностью.',
        },
        'hy': {
            'No diagnostic hypotheses are available yet; run initial analysis first.': 'Ախտորոշիչ վարկածներ դեռ չկան․ նախ գործարկեք վերլուծությունը։',
            'No unused diagnostic test has sufficient expected value for the current hypotheses.': 'Ընթացիկ վարկածների համար բավարար օգտակարությամբ լրացուցիչ թեստեր չկան։',
        },
    }
    result.stop_reasons = [messages.get(language, {}).get(reason, reason) for reason in result.stop_reasons]
    return result
