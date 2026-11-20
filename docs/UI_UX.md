# DidaUP — Specifiche UI/UX

## Visione
L'add-on è usato **dalla Segreteria**, non dai docenti. I referenti ricevono soltanto **file XLSX**. Interfaccia moderna, pulita, professionale, facilmente utilizzabile su desktop, coerente con gli altri software della famiglia ma con identità propria.

## Direzione visiva
- Marchio **DidaUP**, con icona originale stilizzata basata su foglio di calcolo e flusso.
- Navigazione laterale compatta e coerente; intestazione con anno accademico selezionato e stato archivio.
- Palette proposta per prototipo: blu notte #15243B, blu accento #2563EB, azzurro #EAF3FF, grigio neutro #64748B; rosso riservato ad anomalie bloccanti, ambra alle verifiche.
- Layout a card sobrie, gerarchia visiva chiara, tipografia leggibile, spaziature ampie.
- Interfaccia responsive per controllo; progettazione **desktop-first** per la lettura dei dati.
- Modalità chiara come predefinita, predisposizione per modalità scura.
- Stati riconoscibili tramite testo + icona, **mai solo colore**. Accessibilità della tastiera e contrasti adeguati.

## Percorso principale
1. **Panoramica** — stato dell'anno, import completati, SSD pronti, Excel generati, restituzioni, anomalie.
2. **Archivio storico** — import 2026/27, mapping colonne e verifica; storico non modificabile.
3. **Referenti e SSD** — organizzazione per SSD dell'insegnamento, doppia codifica, relazioni con Dipartimenti e referente unico di Facoltà. Fonte referenti dal materiale di area medica, da validare.
4. **Prepara Excel** — procedura guidata: seleziona anno, SSD, controlla anteprima, scegli versione, genera XLSX o ZIP; nessuna pubblicazione di dati personali su GitHub.
5. **Rientro Excel** — import di uno o più file, controllo degli identificativi, campi storici, versioni e anomalie.
6. **Controlli e riepiloghi** — anomalie classificate, esito verifiche, coperture multiple, SSD insegnamento vs SSD docente, carichi; export riservato.

## Qualità d'uso
- Azione primaria ben visibile: **Genera Excel per SSD**.
- Anteprima dell'XLSX prima della generazione, con distinzione visiva netta tra dati storici bloccati e nuove proposte.
- Filtri per SSD, Dipartimento, CdS, sede, stato proposta, ma nessun dato scompare senza indicatore esplicito di filtro attivo.
- Tabelle grandi con intestazioni fisse, colonne essenziali e dettagli espandibili; evitare griglie a 119 colonne nell'interfaccia.
- Conferme obbligatorie per operazioni che alterano lo stato, log di esito e possibilità di riprendere il lavoro.
- Indicatori di avanzamento e anomalie sempre verificabili nel dettaglio.
- Nessuna interfaccia pubblica accessibile ai docenti e nessuna anteprima con dati reali nei repository.

## XLSX per i referenti
La qualità grafica riguarda **anche i fogli prodotti**:
- titolo, SSD vecchio/nuovo, referente (se verificato) e legenda essenziali;
- informazioni e assegnazioni storiche chiaramente differenziate e bloccate;
- area nuove proposte con campi compilabili evidenti e convalide appropriate;
- messaggi regolamentari in apposita legenda/sezione, basati su fonti verificate;
- protezioni e confronto al reimport anche se il file Excel viene alterato esternamente.

Tutti gli esempi in mockup, test, screenshot e demo devono essere **sintetici e non riconducibili a persone reali**.
