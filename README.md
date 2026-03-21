# BoardGameCafe

Repo for boardgamecafe in dat240

## Setup

Oppdater/installer dependencies i terminalen:
```bash
pip install -r boardgame_cafe/requirements.txt
```
Kjør flask(debug):
```bash
flask --app run.py run --debug
```
Flask serveren skal da, for meg, lytte på http://127.0.0.1:5000, som er spesifisert i run.py filen

Dersom du prøver ulike paths så vil alle gi error kode "404", og i nettleser får man opp error: "Resource not found", som igjen er spesifisert i enden av src/app.py: 
```py
@app.error_handler(404)
def not_found(error):
    return {"error": "Resource not found"}, 404
```
    