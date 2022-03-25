# Validation service

## Build lite-client executable

Run `./infrastructure/scripts/build_lite_client.sh`, the built executable will be copied to `./distlib/`

## Run Validation Service

- (Optional) Set variables TON_VALIDATION_HTTP_PORT and TON_VALIDATION_WEBSERVERS_WORKERS.
- Create file `private/mongodb_password` with the only line without `\n` - password for MongoDB.
- Build the service: `sudo docker-compose build`
- Run `sudo docker-compose up -d`

To clean DB and nginx config: `sudo docker-compose down -v`

## Backup tasks

Daily backup:

- Create backup directory: `sudo mkdir /var/ton-backups`.
- Copy backup script to bin: `sudo cp ./backup.sh /usr/bin/ton-elections-backup`.
- Run `sudo crontab -e` and add the line `0 0 * * * ton-elections-backup >> /var/log/ton-elections-backup.log 2>&1`.
