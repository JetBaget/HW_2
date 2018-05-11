# -*-coding: utf-8 -*-

import lxml.html
import requests
import pymorphy2
import collections
from datetime import datetime, date, timedelta


def flat(_list):
    """
    Разворачивает вложенные массивы в один список
    [[1,2], [3,4,5], [6]] -> [1,2,3,4,5,6]
    :param _list:           Список, содержащий вложенные массивы
    :return:                Список элементов вложенных массивов
    """
    return [i for v in _list for i in v]


def purify_str_from_extra_chars(usual_readable_text):
    """
    Приведение текстовых данных к неформатированному виду:
    - lower_case
    - удаление из текста символов пунктуации

    :param usual_readable_text:             Читабельный текст
    :return:                                Неформатированный текст
    """
    lower_str = usual_readable_text.lower().replace('-', ' ')
    punctuation = """!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~«»—"""
    translator = str.maketrans('', '', punctuation)
    pure_str = lower_str.translate(translator)
    return pure_str


def make_datetime_from_str(date_time_str):
    """
    Преобразует дату/время из формата '4 мая в 09:47' в формат ISO 8601

    :param date_time_str:               Дата/время в строковом формате
    :return:                            Дата/время в ISO 8601
    """
    monthes = {'янв': 'jan', 'фев': 'feb', 'мар': 'mar',
               'апр': 'apr', 'мая': 'may', 'июн': 'jun',
               'июл': 'jul', 'авг': 'aug', 'сен': 'sep',
               'окт': 'oct', 'ноя': 'nov', 'дек': 'dec'}
    tokens = date_time_str.split(' ')
    year = '2018'
    if 'сегодня' in tokens:
        std_date = date.today()
    elif 'вчера' in tokens:
        std_date = date.today() - timedelta(days=1)
    else:
        day = tokens[0] if tokens[0] else tokens[1]
        month = monthes.get(tokens[-3][:3])
        if not month:
            year = tokens[-3]
            month = monthes.get(tokens[-4][:3])
        std_date = datetime.strptime('{} {} {}'.format(day, month, year), '%d %b %Y').date()

    std_time = datetime.strptime(tokens[-1], '%H:%M').time()
    full_date_str = ' '.join((str(std_date), str(std_time)))
    return datetime.strptime(full_date_str, '%Y-%m-%d %H:%M:%S')


def get_titles_data_from_page(str_with_html):
    """
    Получение значений заголовков из html

    :param str_with_html:           строка, содержащая html
    :return:                        список кортежей [(заголовок, дата)]
    """
    doc = lxml.html.document_fromstring(str_with_html)
    raw_titles = [title.text for title in list(doc.cssselect('h2.post__title a.post__title_link'))]
    raw_dates = [d.text for d in list(doc.cssselect('header.post__meta span.post__time'))]
    pure_titles = [purify_str_from_extra_chars(t) for t in raw_titles]
    std_datetimes = [make_datetime_from_str(d) for d in raw_dates]
    return zip(pure_titles, std_datetimes)


def collect_parsed_pages_data(posts_url, num_pages):
    """
    Возвращает данные заголовков, собранных со всех страниц

    :param posts_url:               url страницы с постами
    :param num_pages:               количество страниц для парсинга
    :return:                        список кортежей, отсортированный по дате публикации
    """
    pages_data = list()
    start_urls = [posts_url.format(i) for i in range(1, num_pages + 1)]
    for num_str, page_url in enumerate(start_urls):
        page_data = requests.get(page_url).text
        titles = get_titles_data_from_page(page_data)
        pages_data.extend(titles)
    return sorted(pages_data, key=lambda x: x[1], reverse=True)


def union_posts_by_day(posts_data):
    """
    Объединяет заголовки постов, созданных за сутки.
    Дата и время дня недели является датой и временем первого поста

    :param posts_data:              данные с html страниц
    :return:                        список кортежей [(дата/время, объединённые посты)]
    """
    simply_data = list()
    posts_of_day = str()
    last_publication_of_day = datetime.now()
    for p_text, p_date in posts_data:
        posts_of_day = ' '.join([posts_of_day, p_text])
        if p_date.date() < last_publication_of_day.date() or p_date is posts_data[-1][1]:
            simply_data.append((last_publication_of_day, posts_of_day))
            posts_of_day = str()
        last_publication_of_day = p_date
    return simply_data


def process_pages_data(posts_data, top_size):
    """
    Выполняет обработку заголовков и формирует список результатов обработки

    :param posts_data:              спарсенные данные постов с html страниц
    :param top_size:                объём выборки топа
    :return:                        список кортежей с результатами, отсортированный по неделям
    """
    result = list()
    words = list()
    high_day = datetime.now()

    simple_data = union_posts_by_day(posts_data)

    for post in simple_data:
        words.extend(extract_nouns_from_title(post[1]))
        low_day = post[0]
        if (low_day.weekday() == 0 and low_day.date() != high_day.date()) \
                or simple_data[-1] is post:
            top_words = pick_top(words, top_size)
            time_period = '{} / {}'.format(str(low_day)[:10], str(high_day)[:10])
            result.append((time_period, top_words))
            high_day = low_day - timedelta(days=1)
            words = list()
        elif low_day.date() == high_day.date() and simple_data[-1] is post:
            print('Недостаточно данных для статистики')

    return sorted(result, key=lambda x: x[0], reverse=True)


def display_results(list_with_results):
    """
    Отображает результаты обработки в консоль

    :param list_with_results:           Список кортежей [(объект, число)]
    :return:                            None
    """
    words_row_width = 85
    date_row_width = 16
    print('=' * words_row_width)
    print('| Период', ' '*date_row_width, '| Популярные слова')
    print('-' * words_row_width)
    for result in list_with_results:
        time_period = result[0]
        words = result[1]
        words = ', '.join(['{}({})'.format(w, n) for w, n in words])
        print('| {} | {}'.format(time_period, words))
    print('=' * words_row_width)


def extract_nouns_from_title(title):
    """
    Извлечение из текста слов, являющихся существительными

    :param title:               Текст заголовка на русском языке
    :return:                    Список существительных
    """
    morph = pymorphy2.MorphAnalyzer()
    words = title.split()
    nouns = [w[0].normal_form for w in map(morph.parse, words) if 'NOUN' in w[0].tag]
    return nouns


def pick_top(iterable, top_size=3):
    """
    Возвращает наиболее часто встречающиеся значения из массива iterable

    :param iterable:            Массив объектов
    :param top_size:            Объём выборки
    :return:                    Список кортежей [(объект, число)]
    """
    return collections.Counter(iterable).most_common(top_size)


def parse_habr(pages_url, top_size=3, pages=10):
    """
    Выполняет парсинг сайта habr.com
    Извлекает top популярных существительных из заголовков постов
    Отображает награбленное в виде таблицы

    :param pages_url:       url страницы с постами
    :param top_size:        размер топа
    :param pages:           кол-во страниц для парсинга
    :return:                None
    """
    posts = collect_parsed_pages_data(num_pages=pages, posts_url=pages_url)
    results = process_pages_data(posts, top_size)
    display_results(results)
