# ORMANET-UPSELLING

## Requisiti
- Windows 10/11
- Python embedded 3.10 (portabile) copiato in `runtime/python310`
- Dipendenza: `openpyxl` (installata dentro l'ambiente embedded)

## Struttura cartelle
```
ORMANET_UPSELLING/
  import/
    STOCK.xlsx
    CLIENTI.xlsx
    ORDINI/
      STORICO-<NRORDINE>-D.xlsx
      STORICO-<NRORDINE>-A.xlsx
      STORICO-<NRORDINE>-P.xlsx
      UPSELL-<NRORDINE>-D.xlsx
      UPSELL-<NRORDINE>-A.xlsx
      UPSELL-<NRORDINE>-P.xlsx
  output/
  runtime/
    python310/
  config/
  logs/
  app/
  scripts/
  start.ps1
  stop.ps1
  diagnose.ps1
  git_pull.ps1
```

## Avvio
1. Copia la Python embedded in `runtime/python310`.
2. Installa `openpyxl` nell'ambiente embedded.
3. Esegui:
   ```powershell
   .\start.ps1
   ```

## Arresto
```powershell
.\stop.ps1
```

## Diagnosi
Per creare un report da condividere:
```powershell
.\diagnose.ps1
```
Condividi il file `logs/ERRORS_FOR_CHATGPT.txt` e il file zip `logs/diagnose_bundle.zip`.

## Aggiornamento repository
Crea `runtime/.env` con le variabili:
```
GIT_USER=your_username
GIT_TOKEN=your_token
GIT_REPO=https://github.com/Thugboy666/ORMANET-UPSELLING
```
Poi esegui:
```powershell
.\git_pull.ps1
```

## Note GUI
- Seleziona il cliente da `CLIENTI.xlsx`.
- Carica lo stock, i 4 storici, e l'ordine corrente.
- Seleziona la causale e l'aggressività sconto.
- Calcola l'upsell, copia i valori o esporta l'Excel in `output/preventivo.xlsx`.
