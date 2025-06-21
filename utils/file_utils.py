import os

def get_processed_files(db_path='processed_files.txt'):
    if not os.path.exists(db_path):
        return set()
    with open(db_path, 'r') as f:
        return set(f.read().splitlines())

def add_to_processed_files(filename, db_path='processed_files.txt'):
    with open(db_path, 'a') as f:
        f.write(filename + '\n')
