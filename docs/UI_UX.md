# DidaUP — Specifiche UI/UX

## Visione
L'add-on è usato **dalla Segreteria**, non dai docenti. I referenti operano su **cinque file XLSX completi condivisi online**, una copia per dipartimento. Non accedono all'add-on. Interfaccia moderna, pulita, professionale, facilmente utilizzabile su desktop, coerente con gli altri software della famiglia ma con identità propria.

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
3. **Referenti e SSD** — organizzazione amministrativa delle competenze per SSD, distinta dalla distribuzione dei file. Non suddividere o filtrare le attività per dipartimento in fase di export.
4. **Prepara Excel** — seleziona l'anno e il report di offerta mappato, genera **uno ZIP con cinque copie XLSX complete e identiche**. Tutte le attività sono presenti in ogni file, senza suddivisione preventiva per dipartimento.
5. **Rientro Excel** — carica **esattamente cinque file**, effettua un controllo preliminare su identificativi e campi storici e segnala sovrapposizioni tra i file dello stesso insegnamento. Non importare, fondere o approvare automaticamente le proposte.
6. **Controlli e riepiloghi** — anomalie classificate, esito verifiche, coperture multiple, SSD insegnamento vs SSD docente, carichi; export riservato.

## Qualità d'uso
- Azione primaria ben visibile: **Genera 5 Excel identici**.
- Anteprima dell'XLSX prima della generazione, con distinzione visiva netta tra dati storici bloccati e nuove proposte.
- Filtri **all'interno dei file Excel condivisi** per SSD, CdS e sede, preferibilmente tramite **Visualizzazioni foglio** personali per evitare conflitti di visualizzazione. La generazione non filtra per dipartimento.
- Tabelle grandi con intestazioni fisse, colonne essenziali e dettagli espandibili; evitare griglie a 119 colonne nell'interfaccia.
- Conferme obbligatorie per operazioni che alterano lo stato, log di esito e possibilità di riprendere il lavoro.
- Indicatori di avanzamento e anomalie sempre verificabili nel dettaglio.
- Nessuna interfaccia pubblica accessibile ai docenti e nessuna anteprima con dati reali nei repository.

## XLSX per i referenti
La qualità grafica riguarda **anche i fogli prodotti**:
- titolo che distingua storico e proposta, filtri di foglio, intestazioni e legenda essenziali;
- informazioni e assegnazioni storiche chiaramente differenziate e bloccate;
- area nuove proposte con campi compilabili evidenti e convalide appropriate;
- messaggi regolamentari in apposita legenda/sezione, basati su fonti verificate;
- protezioni e confronto al reimport anche se il file Excel viene alterato esternamente.

Tutti gli esempi in mockup, test, screenshot e demo devono essere **sintetici e non riconducibili a persone reali**.


## Cinque file dipartimentali uguali — regola definitiva di distribuzione

DidaUP produce **cinque copie identiche** del medesimo tracciato e degli stessi record di storico, senza preattribuire attività ai dipartimenti. Ogni dipartimento lavora nella propria copia condivisa con i rispettivi referenti autorizzati. Il nome del file identifica la copia: non si introducono filtri dipartimentali né si assegnano insegnamenti tramite il dipartimento di afferenza del docente. Le quattro colonne di proposta sono **Tipo variazione, Nuovo docente, Ore, Note**.

Se una stessa attività compare con proposte in più file, l'interfaccia DidaUP deve segnalarla e impedirne la fusione automatica. La protezione Excel evita modifiche accidentali, ma non è una barriera di sicurezza. La condivisione in modifica del file non limita automaticamente ogni referente alle sole righe del proprio SSD; la sicurezza delle competenze dovrà essere gestita con controlli aggiuntivi.

**Stato implementativo 0.1.10-alpha1:** generazione ZIP e revisione preliminare disponibili; condivisione OneDrive istituzionale, pulsante «+» nel file Excel e approvazioni definitive ancora [DA IMPLEMENTARE / DA COLLAUDARE].
