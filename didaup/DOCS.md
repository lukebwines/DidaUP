# DidaUP — Installazione e collaudo (0.1.1-alpha1)

> Versione iniziale di sviluppo **non collaudata su una specifica istanza di Home Assistant**. Usare soltanto dati sintetici. Non caricare file reali dell'Ateneo.

## Installazione locale da repository privato

Il repository GitHub è **privato**. Non trattarlo come un repository pubblico per l'Add-on Store di Home Assistant.

1. Sul proprio PC, ottenere il codice con accesso GitHub autorizzato. **Non incorporare un token nell'URL del repository**.
2. Copiare **solo il contenuto della cartella `didaup/`** nella cartella dei componenti aggiuntivi locali di Home Assistant, per esempio `/addons/didaup/`. Nella cartella deve esserci `config.yaml` insieme a `Dockerfile`, `run.sh` e `app/`.
3. Aggiornare l'elenco dei componenti aggiuntivi locali tramite Home Assistant.
4. Aprire la configurazione DidaUP e impostare `bootstrap_username` e una `bootstrap_password` **unica di almeno 12 caratteri**. La password viene usata solo per la prima creazione dell'utente amministratore.
5. Avviare DidaUP. Dopo il primo accesso, aggiornare la password dall'area Sicurezza e **rimuovere `bootstrap_password` dalle opzioni**. La rimozione non elimina gli utenti già presenti.
6. Usare il selettore in alto per cambiare A.A.; il database viene mantenuto sotto la directory persistente `/data`.

Le operazioni amministrative e l'archivio non vengono esportati in GitHub.


## Recupero dell'account amministratore senza cancellare i dati

Se DidaUP risponde **Credenziali non valide** anche usando la password iniziale:

1. Accedere in Home Assistant come amministratore e aprire **DidaUP → Configurazione**.
2. Inserire temporaneamente una password nuova e robusta nel campo `admin_recovery_password` (almeno 12 caratteri). **Non** modificare `bootstrap_password` come metodo di recupero: viene usato soltanto quando il database non contiene utenti.
3. Salvare la configurazione e **riavviare l'add-on**. La procedura di recupero reimposta soltanto l'account specificato da `bootstrap_username`, revoca le sessioni di quell'account e cancella i tentativi di accesso falliti. Non elimina il database, le annualità o altri utenti.
4. Accedere con `bootstrap_username` e la nuova password.
5. Dopo aver verificato l'accesso, **rimuovere `admin_recovery_password` dalla configurazione e salvare**. È una credenziale amministrativa temporanea e non deve restare salvata nelle opzioni dell'add-on.
6. Dalla sezione Sicurezza di DidaUP cambiare la password con una definitiva e non riutilizzata.

Il sistema conserva una verifica salata dell'ultima password di recupero, così la stessa richiesta **non viene ripetuta ai riavvii successivi**. Per una nuova procedura di recupero è necessario usare una password diversa.

La password e il suo valore non vanno inseriti in GitHub, messaggi, screenshot o issue. Se si utilizza un backup precedente alla correzione, verificare la versione e seguire nuovamente questa procedura.


## Porta e tunnel

- Porta TCP interna dell'applicazione: **8097**.
- Porta host preimpostata nella configurazione dell'add-on: **8097**, modificabile nella scheda **Rete** di Home Assistant in caso di conflitto.
- Accesso tramite Ingress: rimane disponibile nella barra laterale di Home Assistant.
- Per Cloudflare Tunnel, configurare nel tunnel un hostname protetto con origine HTTP **all'indirizzo LAN di Home Assistant e alla porta host configurata**, senza aprire port forwarding sul router.
- Nella configurazione Cloudflare attivare **Access / Zero Trust** con utenti o gruppi autorizzati e autenticazione forte. Un semplice hostname pubblico senza Access non è sufficiente.
- Abilitare HTTPS lato browser; mantenere `secure_cookies: true` per qualsiasi accesso remoto.
- Se si collauda **esclusivamente in HTTP su una LAN isolata, senza tunnel**, si può impostare temporaneamente `secure_cookies: false`. Riportare il valore a true prima di usare HTTPS o il tunnel.

**Non creare un URL pubblico anonimo per DidaUP.** L'applicazione richiede comunque il proprio login, anche quando il browser passa da Ingress o da Cloudflare Access.

## Utenti e ruoli

- **Amministratore**: crea account, modifica ruoli e abilita/disabilita gli utenti, gestisce gli A.A. e i dati di lavoro.
- **Operatore**: seleziona l'A.A., censisce e include/esclude annualità dei CdS.
- **Sola lettura**: consulta gli anni accademici e le annualità senza modificarli.
- **Referenti SSD**: non vengono registrati come utenti, perché lavoreranno esclusivamente sugli XLSX.

Il backend applica i permessi agli endpoint, indipendentemente dagli elementi mostrati nella pagina. Password con hash salato PBKDF2, sessioni casuali archiviate tramite hash, cookie HttpOnly/SameSite, token CSRF, limitazione dei tentativi di accesso e log tecnici degli eventi privi di contenuto amministrativo.

## Limiti attuali

La versione 0.1 è un **primo nucleo tecnico**, non l'applicazione finale:
- non legge ancora il report `.xls` né importa gli incarichi;
- non genera né acquisisce XLSX dei referenti SSD;
- non automatizza la distribuzione via email o SharePoint;
- non integra ancora regole e avvertenze del regolamento;
- non dispone ancora di test di sicurezza end-to-end e collaudo su tunnel reale.

Prima di utilizzare dati dell'Ateneo sono necessari autorizzazioni, revisione della sicurezza, verifica del trattamento dei dati e collaudo sull'infrastruttura appropriata.
