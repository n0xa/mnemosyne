var channels = ["amun.events", "dionaea.connections", "dionaea.capture", "glastopf.events", "beeswarm.hive", "kippo.sessions", "conpot.events", "snort.alert", "wordpot.events", "shockpot.events", "p0f.events", "suricata.events"];

for(c in channels) { 
    var channel = channels[c]; 
    db.auth_key.update({'identifier': 'mnemosyne', subscribe:{$nin:[channel]}}, {$push: {subscribe: channel}})
    db.auth_key.update({'identifier': 'geoloc', subscribe:{$nin:[channel]}}, {$push: {subscribe: channel}})
}

