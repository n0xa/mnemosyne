/*
    This script pre-computes the counts from the hpfeeds data over time.
*/

var pad = function(number){
    if(number < 10) {
        return "0"+String(number);
    }
    else {
        return String(number);
    }
};

var transform = function(rec) {
    var identifier = rec['_id']['identifier'];

    var year    = pad(rec['_id']['year']);
    var month   = pad(rec['_id']['month']);
    var day     = pad(rec['_id']['day']);

    var date = year+month+day;

    db.counts.update({'date': date, 'identifier': identifier}, {'$set': {'event_count': rec['event_count']}}, {'upsert': true, 'multi': false});
};


var groupby_channel = {
    '$group': {
        '_id':{
            'identifier': "$channel",
            'year': {
                '$year': "$timestamp"
            },
            'month':{
                '$month':"$timestamp"
            },
            'day':{
                '$dayOfMonth':"$timestamp"
            }
        },
        event_count: {$sum: 1}
    }
};

var groupby_ident = {
    '$group': {
        '_id':{
            'identifier': "$ident",
            'year': {
                '$year': "$timestamp"
            },
            'month':{
                '$month':"$timestamp"
            },
            'day':{
                '$dayOfMonth':"$timestamp"
            }
        },
        event_count: {$sum: 1}
    }
};


db.hpfeed.aggregate(groupby_channel).forEach(transform);
db.hpfeed.aggregate(groupby_ident).forEach(transform);
