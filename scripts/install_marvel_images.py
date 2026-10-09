"""Copy the generated Marvel art to the names the bot looks up (images/<name lowercased, spaces as _>.jpg or .png).

Existing files are never overwritten unless --force: a few Marvel names (Ares, Loki...) are also
characters of other games that already have their own picture.
"""
import csv
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(BASE_DIR, 'assets', 'characters', 'marvel')


def slugify(name):
    # Same rule the generator used to name the files
    out = ''.join(c if c.isalnum() else '_' for c in name.lower().replace("'", ""))
    while '__' in out:
        out = out.replace('__', '_')
    return out.strip('_')


def marvel_names():
    for filename, column, saga_column in (('characters.csv', 'nome', 'character_group'),
                                          ('mobs.csv', 'nome', 'saga'), ('bosses.csv', 'nome', 'saga')):
        with open(os.path.join(BASE_DIR, 'data', filename), encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row[saga_column] == 'Marvel':
                    yield filename, row[column]


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dest = args[0] if args else os.path.join(BASE_DIR, 'images')
    force, dry = '--force' in sys.argv, '--dry-run' in sys.argv
    copied, existing, missing, handled = [], [], [], set()
    for source_file, name in marvel_names():
        found = next((os.path.join(SOURCE, slugify(name) + ext) for ext in ('.jpg', '.png')
                      if os.path.exists(os.path.join(SOURCE, slugify(name) + ext))), None)
        stem = os.path.join(dest, name.lower().replace(' ', '_'))
        target = stem + (os.path.splitext(found)[1] if found else '.png')
        if stem in handled:
            continue  # a boss sharing its name with a character uses the same picture
        handled.add(stem)
        has_own = any(os.path.exists(stem + ext) for ext in ('.png', '.jpg', '.jpeg', '.webp'))
        if not found:
            missing.append(name)
        elif has_own and not force:
            existing.append((name, source_file))
        else:
            if not dry:
                for ext in ('.png', '.jpg', '.jpeg', '.webp'):
                    if force and os.path.exists(stem + ext) and stem + ext != target:
                        os.remove(stem + ext)  # the bot reads .png first: an old card would hide the new picture
                shutil.copyfile(found, target)
            copied.append(name)
    print(f"{'Would copy' if dry else 'Copied'} {len(copied)}; already present {len(existing)}; no art for {len(missing)}")
    for name, source_file in existing:
        print(f"  skipped (exists): {name} [{source_file}]")
    for name in missing:
        print(f"  missing art: {name}")
