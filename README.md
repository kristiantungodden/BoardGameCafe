# BoardGameCafe

Repo for boardgamecafe in dat240

## Setup

Opprett virtual environment (første gang):

```powershell
py -m venv .venv
```

Installer/oppdater dependencies via startup-script:

```powershell
.\startup.bat --install-deps
```

Start appen normalt:

```powershell
.\startup.bat
```

Alternativ manuel start med venv-python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r boardgame_cafe\requirements.txt
.\.venv\Scripts\python.exe -m flask --app run.py run --debug
```

MacOS startup:
```bash
chmod +x startup.sh
./startup.sh --install-deps   # optional first time / updates
./startup.sh
```

Når flask serveren kjører skal det da lytte på http://127.0.0.1:5000, som er spesifisert i [run.py](run.py)

Dersom du prøver ulike paths så vil alle gi error kode "404", og i nettleser får man opp error: "Resource not found", som igjen er spesifisert i enden av [src/app.py](boardgame_cafe/src/app.py):

```py
@app.error_handler(404)
def not_found(error):
    return {"error": "Resource not found"}, 404
```

## Domain

Har lagt til simpel implementasjon av TableReservation i [src/domain/models/reservation.py](boardgame_cafe/src/domain/models/reservation.py). Kan bruke dette som "mal" for de andre domene emnene. Minner også veldig om DDD i C# fra labbene
NB: Kan være greit å lese seg opp på dataclass og typing i python. Eks:

```py
from dataclasses import dataclass

@dataclass
class Ball:
    x_coord: float
    y_coord: float
    radius: int
    color: str
    ...
```

Syntaks minner litt om flask routes med '@app'.

Også, i [src/domain/exceptions.py](boardgame_cafe/src/domain/exceptions.py) er det lagt til noen basic exceptions. Dette minner også om de vi hadde i C# labbene.

`__init__.py` filene gjør at alt i det directoryet blir sett på som en modul/package, som man kan eksportere. Dette gjør at man slipper importere hver fil, men heller importere fra packagen, som inneholder flere filer og også flere packages.

For eksempel i [src/infrastructure](boardgame_cafe/src/infrastructure) eksporterer [__init__.py](boardgame_cafe/src/infrastructure/__init__.py) både fra [extensions.py](boardgame_cafe/src/infrastructure/extensions.py) og fra packagen i [message_bus](boardgame_cafe/src/infrastructure/message_bus). Dette gjør at i [src/app.py](boardgame_cafe/src/app.py) kan man importere alt i samme import:

```py
from infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery
```

Hvordan domene blir brukt vil bli implementert senere igjennom [src/application](boardgame_cafe/src/application), hovedsakelig i [src/application/use_cases](boardgame_cafe/src/application/use_cases).
