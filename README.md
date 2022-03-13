# Validation service

### Build lite-client executable

Run `./infrastructure/scripts/build_lite_client.sh`, the built executable will be copied to `./distlib/`

### Run Validation Service

- (Optional) Set variables TON_VALIDATION_HTTP_PORT and TON_VALIDATION_WEBSERVERS_WORKERS.
- Build the service: `sudo docker-compose build`
- Run `sudo docker-compose up -d`

To clean DB and nginx config: `sudo docker-compose down -v`