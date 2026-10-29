"""Portable diagnostic PDF rendering shared by backend and offline Desktop."""
from io import BytesIO
from pathlib import Path
from threading import RLock
from xml.sax.saxutils import escape

_font_lock = RLock()


def render_diagnostic_pdf(data: dict, language: str = 'en') -> bytes:
    """Render a privacy-filtered report without Qt or OS printer services."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    with _font_lock:
        if 'ScannerUnicode' not in pdfmetrics.getRegisteredFontNames():
            font = Path(__file__).resolve().parents[1] / 'backend/resources/fonts/DejaVuSans.ttf'
            if not font.is_file():
                import sys
                font = Path(getattr(sys, '_MEIPASS', '.')) / 'backend/resources/fonts/DejaVuSans.ttf'
            pdfmetrics.registerFont(TTFont('ScannerUnicode', str(font)))
    style = ParagraphStyle('body', fontName='ScannerUnicode', fontSize=10, leading=15, wordWrap='CJK')
    labels = {
        'hy': ['Ախտորոշման հաշվետվություն', 'Մեքենա', 'Ախտանիշներ', 'Վարկածներ', 'Առաջարկվող թեստեր', 'Թեստերի արդյունքներ'],
        'ru': ['Диагностический отчёт', 'Автомобиль', 'Симптомы', 'Гипотезы', 'Рекомендуемые тесты', 'Результаты тестов'],
    }.get(language, ['Diagnostic report', 'Vehicle', 'Symptoms', 'Hypotheses', 'Recommended tests', 'Test results'])
    title_style = ParagraphStyle('title', parent=style, fontSize=19, leading=25, textColor=HexColor('#0B3458'))
    heading_style = ParagraphStyle('heading', parent=style, fontSize=12, leading=18, textColor=HexColor('#0B567F'), spaceBefore=10, spaceAfter=7)
    field_labels = {
        'hy': {'raw_text':'Նկարագրություն', 'symptom':'Ախտանիշ', 'fact':'Դիտարկում', 'source':'Աղբյուր', 'confidence':'Վստահություն', 'make':'Արտադրող', 'model':'Մոդել', 'chassis':'Թափք', 'year':'Տարի', 'engine':'Շարժիչ', 'fuel':'Վառելիք', 'ecu':'ECU', 'name':'Անվանում', 'purpose':'Նպատակ', 'category':'Կատեգորիա', 'statement':'Վարկած', 'confidence_score':'Գնահատական', 'status':'Կարգավիճակ', 'result':'Արդյունք', 'result_label':'Արդյունքի անվանում', 'test_name':'Թեստ', 'measurements':'Չափումներ', 'notes':'Նշումներ'},
        'ru': {'raw_text':'Описание', 'symptom':'Симптом', 'fact':'Наблюдение', 'source':'Источник', 'confidence':'Уверенность', 'make':'Марка', 'model':'Модель', 'chassis':'Кузов', 'year':'Год', 'engine':'Двигатель', 'fuel':'Топливо', 'ecu':'ЭБУ', 'name':'Название', 'purpose':'Цель', 'category':'Категория', 'statement':'Гипотеза', 'confidence_score':'Оценка', 'status':'Состояние', 'result':'Результат', 'result_label':'Название результата', 'test_name':'Тест', 'measurements':'Измерения', 'notes':'Примечания'},
    }.get(language, {})
    story = [Paragraph('AI CAR SCANNER', heading_style), Paragraph(escape(labels[0]), title_style), Spacer(1, 16)]
    import json
    for title, key in zip(labels[1:], ['vehicle', 'symptoms', 'hypotheses', 'recommendations', 'test_results']):
        story.append(Paragraph(escape(title), heading_style))
        values = data.get(key) or []
        if not isinstance(values, list): values = [values]
        for value in values:
            # Render each field separately so large reports paginate cleanly.
            fields = value.items() if isinstance(value, dict) else [('value', value)]
            for field, content in fields:
                if field in {'id', 'metadata', 'normalized', 'source_ref', 'supporting_evidence_ids', 'contradicting_evidence_ids', 'target_hypotheses'} or (field == 'test_id' and isinstance(value, dict) and value.get('test_name')):
                    continue
                if content is None:
                    text = '—'
                elif isinstance(content, list) and all(isinstance(item, str) for item in content):
                    text = ', '.join(content) or '—'
                else:
                    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                label = field_labels.get(field, field.replace('_', ' ').capitalize())
                story.append(Paragraph(escape(f'{label}: {text}'), style))
            story.append(Spacer(1, 7))
        story.append(Spacer(1, 12))
    extra_titles = {'hy': ('Ապացույցներ', 'Գործողությունների պատմություն'), 'ru': ('Доказательства', 'История действий')}.get(language, ('Evidence', 'Activity'))
    for title, key in zip(extra_titles, ('evidence', 'audit_log')):
        story.append(Paragraph(escape(title), heading_style))
        for item in data.get(key, []):
            if key == 'evidence':
                text = str(item.get('fact') or '—')
                details = ' • '.join(str(item[k]) for k in ('status', 'source') if item.get(k))
                if details: text += ' — ' + details
            else:
                text = str(item.get('event') or '—')
                details = ', '.join(f'{k.replace("_", " ")}: {v}' for k, v in item.items() if k != 'event' and isinstance(v, (int, float)))
                if details: text += ' • ' + details
            story.append(Paragraph(escape(text), style))
        story.append(Spacer(1, 12))
    story.append(Paragraph('DTC', heading_style))
    for dtc in data.get('dtcs', []):
        story.append(Paragraph(escape(str(dtc.get('code', '')) + ' ' + str(dtc.get('description') or '')), style))
    output = BytesIO()
    SimpleDocTemplate(output, title=labels[0], author='AI CAR SCANNER').build(story)
    return output.getvalue()
