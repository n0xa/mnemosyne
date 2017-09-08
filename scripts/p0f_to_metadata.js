var clone = function(obj) {
    var ret = {};
    for(var name in obj) {
        ret[name] = obj[name];
    }
    return ret;
};

var isEmpty = function (obj) {
    for(var prop in obj) {
        if(obj.hasOwnProperty(prop))
            return false;
    }
    return true;
};

var get_metadata = function(o_data, submission_timestamp) {
    var metadata = {};
    var fields = ['app', 'link', 'os', 'uptime'];
    for (var i = 0; i < fields.length; i++) {
        var name = fields[i];
        if(o_data[name] && o_data[name] != '???') {
            metadata[name] = o_data[name];
        }
    }

    if( !isEmpty(metadata)){
        metadata['ip'] = o_data['client_ip'];
        metadata['honeypot'] = 'p0f';
        metadata['timestamp'] = submission_timestamp;
    }
    return metadata;
};

var transform = function(rec){
    var payload = JSON.parse(rec['payload']);
    var submission_timestamp = rec['timestamp'];

    var metadata = get_metadata(payload, submission_timestamp);
    if(!isEmpty(metadata)) {
        var query = {'ip': metadata['ip'], 'honeypot':metadata['honeypot']};
        var update = {'$set': clone(metadata) };

        delete update['ip'];
        delete update['honeypot'];

        db.metadata.update(query, update, {upsert: true})
    }

};

db.hpfeed.find({channel:'p0f.events'}).forEach(transform);
