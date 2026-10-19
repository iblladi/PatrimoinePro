"""Point d'entrée de PatrimoinePro (à lancer avec pythonw pour masquer la console)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from app.main import main

if __name__ == "__main__":
    main()
