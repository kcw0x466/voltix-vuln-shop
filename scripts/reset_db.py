"""Explicit reset: python scripts/reset_db.py --yes"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
if __name__=='__main__':
    create_app().cli.main(args=['reset-db',*sys.argv[1:]],prog_name='reset_db.py')
