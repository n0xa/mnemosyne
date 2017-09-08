#!/bin/bash

set -e

DAYS=30

DATE=$(date -d "${DAYS} days ago" +%FT00:00:00.000Z)
echo "[`date`] Deleting session and hpfeeds data older than $DATE..."

for COLLECTION in session hpfeed;
do
    REMOVE_CMD="db.${COLLECTION}.remove( { timestamp: {\$lt: ISODate(\"${DATE}\") }  } )"
    /usr/bin/mongo mnemosyne --eval "$REMOVE_CMD"
done

echo "[`date`] Deleting precomputed counts for sensors and channels"
DATE=$(date -d "${DAYS} days ago" +%Y%m%d)
REMOVE_CMD="db.counts.remove( { date: {\$lt: \"${DATE}\" }  } )"
/usr/bin/mongo mnemosyne --eval "$REMOVE_CMD"

echo "[`date`] done"
