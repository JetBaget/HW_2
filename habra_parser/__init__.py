# -*- coding: utf-8 -*-

import argparse
import sys

from habra_parser.scraper import parse_habr


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pages', type=int, nargs='?', default=10,
                        help='Количество страниц для пагинации')
    parser.add_argument('-s', '--size_of_top', type=int, nargs='?', default=5,
                        help='Рармер топа популярных слов')
    parser.add_argument('-t', '--target', type=str, nargs='?', default='ALL',
                        help='Цель парсинга. ALL - все посты, BEST - лучшие за год')
    args = parser.parse_args(sys.argv[1:])

    pages = args.pages
    top_size = args.size_of_top

    pages_url = None
    if args.target == 'BEST':
        pages_url = 'https://habr.com/top/yearly/page{}'
    elif args.target == 'ALL':
        pages_url = 'https://habr.com/all/page{}'

    if pages_url:
        parse_habr(pages_url, top_size)
