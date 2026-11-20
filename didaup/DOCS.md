# DidaUP — Installazione e collaudo (0.1.0-alpha1)

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
