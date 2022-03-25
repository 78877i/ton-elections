#!/bin/bash
set -e

MONGODB_PASSWORD=$(cat /home/toncenter/ton-elections/private/mongodb_password)
COMMAND="exec mongodump -u user1 -p $MONGODB_PASSWORD -d validation-db --authenticationDatabase admin --archive"

for COLLECTION in complaints elections validation 
do
    echo "Backup of $COLLECTION"
    docker exec ton-elections_mongodb_1 sh -c "$COMMAND -c ${COLLECTION}_data" > /var/ton-backup/elections_$COLLECTION.archive
done
