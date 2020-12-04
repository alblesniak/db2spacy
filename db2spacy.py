import argparse
import os
import sqlite3
import concurrent.futures
import spacy
import logging
import pickle
from tqdm import tqdm
from collections import defaultdict

def create_directories(issues_names):
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)
        logging.info(f'Created directory: {DATA_PATH}')
    for issue_name in issues_names:
        issue_path = os.path.join(DATA_PATH, issue_name)
        if not os.path.exists(issue_path):
            os.mkdir(issue_path)
            logging.info(f'Created directory: {issue_path}')
    return

def issues_from_db(issues_names):
    data = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for issue in tqdm(issues_names):
        unique_numbers = cursor.execute(f'''
            SELECT DISTINCT number FROM issue WHERE name = '{issue}';
        ''').fetchall()
        for number in [nr[0] for nr in unique_numbers if nr[0] != '']:
            data.append((issue, number))
    cursor.close()
    return data

def data_from_db(issue_name, issue_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data = cursor.execute(f'''
        SELECT article.id, intro, content, article_url, issue_id FROM article
        INNER JOIN issue ON issue_id = issue.id
        WHERE issue.name = '{issue_name}' AND issue.number = '{issue_number}';
    ''').fetchall()
    cursor.close()
    return data

def merge_text(intro, content):
    if intro != None and content != None:
        return intro + '\n' + content
    elif intro == None and content != None:
        return content
    elif intro != None and content == None:
        return intro
    else:
        return False

def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f

def spacy_document(issue_name, issue_number, article_id, article_text, issue_id, article_url):
    doc = nlp(article_text)
    doc.set_extension('issue_id', default=issue_id)
    doc.set_extension('issue_name', default=issue_name)
    doc.set_extension('issue_number', default=issue_number)
    doc.set_extension('article_id', default=article_id)
    doc.set_extension('article_url', default=article_url)
    return doc

def ids2paths_dict():
    for weekly in [w for w in listdir_nohidden(DATA_PATH) if os.path.isdir(w)]:
        articles_ids_paths = defaultdict(str)
        for issue_path in [i for i in listdir_nohidden(os.path.join(DATA_PATH, weekly)) if os.path.isdir(i)]:
            articles_ids = [int(file_name.split('.')[0]) for file_name in listdir_nohidden(issue_path) if file_name.endswith('.pickle')]
            for article_id in articles_ids:
                articles_ids_paths[article_id] = os.path.join(issue_path)
        with open(os.path.join(*[DATA_PATH, weekly, 'ids2paths.pickle']), 'wb') as articles_pickle:
            pickle.dump(articles_ids_paths, articles_pickle)

def vocab2ids_dict():
    for weekly in [w for w in listdir_nohidden(DATA_PATH) if os.path.isdir(w)]:
        vocab2ids = defaultdict(list)
        for issue_path in [i for i in listdir_nohidden(os.path.join(DATA_PATH, weekly)) if os.path.isdir(i)]:
            for article_id in [a.split('.')[0] for a in listdir_nohidden(issue_path) if a.endswith('.pickle')]:
                with open(os.path.join(issue_path, f'{article_id}.pickle'), 'rb') as article_pickle:
                    lemmas = article_pickle.load().keys()
                for lemma in lemmas:
                    vocab2ids[lemma].append(int(article_id))
        with open(os.path.join(*[DATA_PATH, weekly, 'vocab2ids.pickle']), 'wb') as vocab_pickle:
            pickle.dump(vocab2ids, vocab_pickle)

def count_lemmas(doc):
    tf_vocab = defaultdict(int)
    for word in doc:
        tf_vocab[word.lemma_] += 1
    return tf_vocab

def process_data(issues_data):
    issue_name = issues_data[0]
    issue_number=issues_data[1]
    issue_year = issue_number.split('/')[0]
    issue_week = issue_number.split('/')[1]
    data = data_from_db(issue_name=issue_name, issue_number=issue_number)
    for article_id, article_intro, article_content, article_url, issue_id in data:
        article_text = merge_text(article_intro, article_content)
        doc = spacy_document(issue_name, issue_number, article_id, article_text, issue_id, article_url)
        tf_vocab = count_lemmas(doc=doc)
        doc_path = os.path.join(*[DATA_PATH, issue_name, f'{issue_year}_{issue_week}'])
        if not os.path.exists(doc_path):
            os.mkdir(doc_path)
        file_path = os.path.join(doc_path, f'{article_id.zfill(6)}')
        print(file_path)
        # doc.to_disk(f'{file_path}.spaCy_doc')
        # with open(f'{file_path}.pickle', 'wb') as vocab_pickle:
        #     pickle.dump(tf_vocab, vocab_pickle)
        # logging.info('saved')

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser(description='Generate Bag of Words matrices from corpus saved as sqlite3 database.')
    parser.add_argument('-db', '--db_path',
                        metavar='',
                        default='../scraper/scrapy_magazines.db',
                        help='Path to database.')
    parser.add_argument('-w', '--weeklies',
                        metavar='',
                        action='append',
                        default=['gosc_niedzielny', 'niedziela', 'przewodnik_katolicki', 'newsweek_polska', 'newsweek_wydanie_amerykanskie', 'wprost'],
                        help='List of issues names that have to be included in process.')
    parser.add_argument('-lm', '--lang_model',
                        metavar='',
                        default='pl_core_news_lg',
                        help='spaCy language model to use.')
    parser.add_argument('-dp', '--data_path',
                        metavar='',
                        default='data/',
                        help='Data directory'
                        )
    args = parser.parse_args()
    DB_PATH = os.path.abspath(args.db_path)
    DATA_PATH = os.path.abspath(args.data_path)
    LANG_MODEL = args.lang_model
    WEEKLIES = args.weeklies
    logging.info(f'Loading spaCy model: {LANG_MODEL}')
    nlp = spacy.load(LANG_MODEL, disable=["parser"])
    logging.info(f'spaCy model {LANG_MODEL} loaded.')
    # create_directories(issues_names=WEEKLIES)
    issues_data = issues_from_db(issues_names=WEEKLIES)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        logging.info('Multiprocessing executing...')
        executor.map(process_data, issues_data)
    # ids2paths_dict()
    # logging.info('Articles_ids map into directories.')
    # vocab2ids_dict()
    # logging.info('Vocabulary map into articles_ids.')
    # logging.info('Done.')



