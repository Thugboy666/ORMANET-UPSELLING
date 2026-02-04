# ORMANET-UPSELLING

## Requisiti
- Windows 10/11
- Python embedded 3.10 (portabile) copiato in `runtime/python310`
- Dipendenza: `openpyxl` (installata dentro l'ambiente embedded)

## Git setup
Opzione consigliata:
- **Installa Git per Windows** (consigliato). Assicurati che `git.exe` sia disponibile nel PATH oppure in `C:\Program Files\Git\cmd\git.exe`.

Alternativa portable:
- **Portable Git**: copia Git in `runtime/git/` in modo che esista `runtime/git/cmd/git.exe`.

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
4. Si apre il browser su `http://127.0.0.1:8765`.

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

## Note Web UI
- Premi **Carica default** per leggere `CLIENTI.xlsx` e `STOCK.xlsx`.
- Seleziona il cliente, l'ordine upsell e 4 storici (STORICO-*.xlsx).
- Seleziona la causale e l'aggressività sconto.
- Calcola l'upsell, copia i valori o esporta l'Excel in `output/preventivo.xlsx`.
- **PREZZO_ALT**: prezzo promo ex IVA (solo articoli altovendenti).
- **Modalità ALTOVENDENTI**: usa `PREZZO_ALT` come LM di partenza; il prezzo finale segue le regole normali (RIC + sconto).

## Field mapping
- Usa **Mappa campi** per verificare o modificare gli alias dei campi delle tabelle ORDINI, STOCK e CLIENTI.
- **Salva mapping** scrive `config/field_mapping.json`; **Reset default** ripristina i valori di base.
- **Test mapping** legge solo le intestazioni degli Excel selezionati e segnala eventuali campi obbligatori mancanti.
