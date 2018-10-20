# ServerlessDay - Workshop back-end

Costruiamo un'applicazione di file sharing completamente serveless con chalice.\
Questo repository contiene il back-end dell'applicazione.

Per il codice di front-end e tutte le istruzioni correlate fare riferimento a questo repository: https://github.com/besharpsrl/serverless-day-fe

## Prerequisiti

- Account AWS
- Tre bucket S3 per
- Una Cognito User Pool
- Due tabelle DynamoDB


### Bucket S3

All’applicazione occorrerà un bucket S3 per gli upload dei file degli utenti.\
In questo caso si tratterà di un bucket privato. Provvediamo quindi alla sua creazione nello stesso modo utilizzato per il front-end, e prendiamo nota del nome del bucket, ci servirà per la configurazione dell’applicazione.

Occorrono anche 2 bucket aggiuntivi che saranno usati per la pipeline di CD/CI, uno per contenere configurazioni ed uno per i bundle delle release.\
Questi due bucket sono opzionali, e vanno creati solo se si decide di implementare la pipeline.


### Cognito User Pool

Durante il Wizard di creazione possiamo personalizzare alcuni comportamenti; per far funzionare l’applicazione bisogna creare un Pool che permetta gli utenti di registrarsi mediante email e di verificare l’indirizzo utilizzando un codice di sicurezza gestito da Cognito. Occorre anche creare un’app client e prendere nota del suo ID.

Scegliamo un nome per la User Pool e avviamo il wizard

![Cognito user pool](https://blog.besharp.it/wp-content/uploads/2018/09/SS_19-09-2018_124930.png)


Configuriamo il meccanismo di autenticazione e i campi del profilo.

![Cognito user pool](https://blog.besharp.it/wp-content/uploads/2018/09/SS_19-09-2018_125142.png)

Infine bisogna creare un app client e prendere nota del suo ID. Non bisogna far generare alcun segreto, non servirà per l’utilizzo di Cognito mediante web app.

![Cognito user pool](https://blog.besharp.it/wp-content/uploads/2018/09/SS_19-09-2018_125238.png)

![Cognito user pool](https://blog.besharp.it/wp-content/uploads/2018/09/SS_19-09-2018_125555.png)


### Tabelle di DynamoDB

Servirà anche una tabella di DynamoDB per contenere i metadati e le informazioni di share dei file. Procediamo quindi alla creazione di una tabella lasciando i valori di default e specificando "owner" con sort key "share_id" come chiave di partizione primaria. Va aggiunto un indice globale "share_id"

![Dettagli tabella DynamoDB](https://blog.besharp.it/wp-content/uploads/2018/09/SS_19-09-2018_171125.png)

Un'altra tabella sarà necessaria per l'audit log, anche in questo caso lasciamo tutti i settaggi di default e indichiamo come chiave primare lo `action_time`


## Ottenere il codice

```bash
git clone https://github.com/besharpsrl/serverless-day-be.git
```

Oppure è possibile scaricare uno zip utilizzando il pulsante in alto a destra sulla pagina github.


## Configurazione

Per settare gli ARN e gli ID delle risorse da utilizzare esiste un apposito file di configurazione in ` ./mydoctransfer-lambda/chalicelib/config.py `

```python
# Cognito
COGNITO_USER_POOL_NAME = 'CHANGE ME'
COGNITO_USER_POOL_ARN = 'CHANGE ME'
COGNITO_USER_POOL_ID = 'CHANGE ME'


# DynamoDB
DYNAMODB_FILE_TABLE_NAME = 'CHANGE ME'
DYNAMODB_AUDIT_TABLE_NAME = 'CHANGE ME'


# S3
S3_UPLOADS_BUCKET_NAME = 'CHANGE ME'
```

Indicare ARN, Name, o ID come richiesto.


## Modalità locale

Il bundle include anche un docker-compose.yml e un Dockerfile che è possibile utilizzare per avviare in locale il backend.

```bash
docker-compose up 
```

Nel caso si preferisca invece evitare docker e installare le dipendenze nel proprio sistema occorre installare python 3.6, pip e successivamente tutte le dipendenze contenute in requirements.txt. Consigliamo vivamente di utilizzare un **VirtualEnv** dedicato nel caso in cui Docker non sia un’opzione praticabile.

```bash
pip3 install -r requirements.txt --user
```


## Deploy

Chalice è in grado provvedere al deploy e alla configurazione di API Gateway e Lambda; le configurazioni sono espresse in modo idiomatico nel codice applicativo.

Una volta pronto il progetto si può effettuare il deploy automatico semplicemente invocando

```bash
chalice deploy
```

Il comando va invocato da uno IAM User o Role con i permessi di creare e gestire Lambda Function, API Gateway, e CloudWatch.
Per il workshop, un utente con policy `AdministratorAccess` andrà più che bene.


## CD/CI (Facoltativo)

Vogliamo completare l’architettura accennando alle pipeline automatiche per il deploy del codice.

Come prima cosa occorre creare una nuova applicazione su CodeBuild e configurarla per utilizzare il file buildspec.yml presente nella root del repository.

 ![Code build](https://blog.besharp.it/wp-content/uploads/2018/10/SS_09-10-2018_120438.png)

Bisogna passare a CodeBuild le seguenti variabili d'ambiente:\
`CONFIG_S3_BUCKET`\
`RELEASES_S3_BUCKET`\
e valorizzarle usando il nome dei bucket per le configurazioni e per le release.


Una volta creato e configurato CodeBuild, basta creare una Pipeline che faccia il source da CodeCommit e poi invochi CodeBuild. non occorre specificare lo stadio di deploy, perchè per questo esempio abbiamo incluso le istruzioni nel buildspec.yml in modo che siano eseguite dopo il processo di build.

Di conseguenza, gli IAM role associati ai CodeBuild devono avere il permesso di caricare ed eliminare file da S3, gestire API Gateway e Lambda.

Analizzando i buildspec possiamo osservare le operazioni eseguite per il build e deploy delle applicazioni.

```yaml
version: 0.1
phases:
  install:
    commands:
    - rm -rf mydoctransfer-lambda/.chalice/deployed
    - mkdir mydoctransfer-lambda/.chalice/deployed
    - cd mydoctransfer-lambda/.chalice/deployed && aws s3 sync --delete s3://$RELEASES_S3_BUCKET/backend/chalice .
    - cd mydoctransfer-lambda && pip3.6 install -r requirements.txt --user
    - aws s3 cp s3://$CONFIG_S3_BUCKET/backend/$ENV/modsam.py .
    - cd mydoctransfer-lambda/.chalice && aws s3 cp s3://$CONFIG_S3_BUCKET/backend/$ENV/config.json .
    - ./build.sh
    - cd mydoctransfer-lambda/.chalice/deployed && aws s3 sync --delete . s3://$RELEASES_S3_BUCKET/backend/chalice
artifacts:
  type: zip
  files:
    - build.sh
```
