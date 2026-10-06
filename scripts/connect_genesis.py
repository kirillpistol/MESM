"""Совместимый старый entrypoint: теперь запускает только самостоятельный MESM L3."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from mesm.access.server import main
if __name__=="__main__":
    print("MESM запускается как независимый L3. Менеджер GENESIS подключается отдельно.")
    main()
